#!/usr/bin/env python3
"""
Eval Runner — 自动跑 Prompt 测试用例并评分。

使用方法:
    python eval/runner.py                        # 跑全部用例
    python eval/runner.py --case 001             # 跑单个用例
    python eval/runner.py --provider deepseek    # 指定 LLM 提供商
    python eval/runner.py --verbose              # 显示完整 LLM 输出

流程:
    1. 读取 eval/case_*.md 中的 diff 和预期发现
    2. 调用 LLM Service 生成审核报告
    3. 解析报告，检查是否命中预期问题
    4. 输出评分表

评分维度:
    - Recall:    预期问题被发现的比率
    - Severity:  严重级别匹配率
    - Suggestion: 是否给出修复建议
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# 将项目根目录加入 sys.path
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _PROJECT_ROOT)


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class ExpectedFinding:
    """测试用例中的预期发现项。"""
    description: str
    severity: str  # Critical / Major / Minor / Info
    file: str = ""
    line: str = "0"  # 行号，支持 "42" 或 "5-7" 范围

    def short_str(self) -> str:
        return f"[{self.severity}] {self.description[:60]}"


@dataclass
class EvalCase:
    """一个完整的测试用例。"""
    case_id: str
    title: str
    category: str
    severity: str
    diff: str
    expected_findings: list[ExpectedFinding]
    file_path: str

    @property
    def pr_title(self) -> str:
        return f"[Eval] {self.title}"

    @property
    def pr_description(self) -> str:
        cats = f"Category: {self.category} | Expected Severity: {self.severity}"
        return f"Automated eval case. {cats}"


@dataclass
class EvalResult:
    """单个测试用例的执行结果。"""
    case_id: str
    title: str
    passed: int = 0
    missed: int = 0
    severity_correct: int = 0
    has_suggestion: bool = False
    raw_output: str = ""
    error: Optional[str] = None
    duration_ms: int = 0

    @property
    def total(self) -> int:
        return self.passed + self.missed

    @property
    def recall(self) -> float:
        if self.total == 0:
            return 1.0
        return self.passed / self.total

    @property
    def passed_all(self) -> bool:
        return self.missed == 0 and self.error is None


# ---------------------------------------------------------------------------
# 解析测试用例
# ---------------------------------------------------------------------------

def parse_case(file_path: str) -> Optional[EvalCase]:
    """解析单个 eval/case_*.md 文件。"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取标题
    title_match = re.search(r"# Eval Case (\d+): (.+)", content)
    if not title_match:
        print(f"  ⚠️  {file_path}: 无法解析标题，跳过")
        return None

    case_id = title_match.group(1)
    title = title_match.group(2).strip()

    # 提取类别和严重级别
    cat_match = re.search(r"\*\*类别\*\*:\s*(.+)", content)
    sev_match = re.search(r"\*\*严重级别\*\*:\s*(.+)", content)
    category = cat_match.group(1).strip() if cat_match else "Unknown"
    severity = sev_match.group(1).strip() if sev_match else "Unknown"

    # 提取 diff（第一个 ```diff 块）
    diff_match = re.search(r"```diff\n(.+?)```", content, re.DOTALL)
    diff = diff_match.group(1).strip() if diff_match else ""

    # 提取预期发现表格
    findings = parse_findings_table(content)

    return EvalCase(
        case_id=case_id,
        title=title,
        category=category,
        severity=severity,
        diff=diff,
        expected_findings=findings,
        file_path=file_path,
    )


def parse_findings_table(content: str) -> list[ExpectedFinding]:
    """解析 Markdown 表格中的预期发现。"""
    findings = []
    # 匹配表格行: | 序号 | 描述 | 严重级别 | 文件 | 行号 |
    table_lines = re.findall(
        r"\| \d+ \| (.+?) \| ([🔴🟠🟡⚪]\*{0,2}\s*(Critical|Major|Minor|Info)) \| `(.+?)` \| ([\d,\-]+) \|",
        content,
    )
    for desc, sev_raw, sev, file_path, line_str in table_lines:
        findings.append(ExpectedFinding(
            description=desc.strip(),
            severity=sev.strip(),
            file=file_path.strip(),
            line=line_str.strip(),
        ))
    return findings


# ---------------------------------------------------------------------------
# 加载全部用例
# ---------------------------------------------------------------------------

def load_all_cases(eval_dir: str = "eval") -> list[EvalCase]:
    """加载 eval/ 目录下所有 case_*.md 文件。"""
    pattern = os.path.join(eval_dir, "case_*.md")
    files = sorted(glob.glob(pattern))
    cases = []
    for f in files:
        case = parse_case(f)
        if case:
            cases.append(case)
    return cases


# ---------------------------------------------------------------------------
# 评分逻辑
# ---------------------------------------------------------------------------

def evaluate_output(case: EvalCase, output: str) -> EvalResult:
    """检查 LLM 输出是否命中预期发现。"""
    result = EvalResult(
        case_id=case.case_id,
        title=case.title,
        raw_output=output,
    )

    output_lower = output.lower()

    for finding in case.expected_findings:
        # 检查描述关键词是否出现在输出中
        keywords = extract_keywords(finding.description)
        found = any(kw.lower() in output_lower for kw in keywords)

        if found:
            result.passed += 1
            # 检查严重级别是否匹配
            if finding.severity.lower() in output_lower:
                result.severity_correct += 1
        else:
            result.missed += 1

    # 检查是否包含代码建议（``` 代码块表示有建议）
    result.has_suggestion = "```" in output

    return result


def extract_keywords(description: str) -> list[str]:
    """从问题描述中提取关键词用于匹配。"""
    # 移除常见停用词，保留关键术语
    stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
                 "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
                 "会", "着", "没有", "看", "好", "自己", "这", "out", "the",
                 "a", "an", "in", "on", "at", "to", "for", "of", "by", "with"}

    # 分词（简单：按空格和标点分割）
    terms = re.findall(r"[\w]+", description)

    # 保留有信息量的关键词（长度 >= 2 且非停用词）
    keywords = [t for t in terms if len(t) >= 2 and t.lower() not in stopwords]

    return keywords


# ---------------------------------------------------------------------------
# 运行测试
# ---------------------------------------------------------------------------

def run_single_case(
    case: EvalCase,
    provider: str = "deepseek",
    verbose: bool = False,
    dry_run: bool = False,
) -> EvalResult:
    """调用 LLM 审核单个用例并评分。

    Args:
        case: 测试用例
        provider: LLM 提供商名称
        verbose: 是否输出完整 LLM 响应
        dry_run: 不实际调用 LLM，用预设响应替代（测试 runner 本身）
    """
    if dry_run:
        # 用预设响应做评分逻辑测试
        mock_output = generate_mock_review(case)
        result = evaluate_output(case, mock_output)
        result.duration_ms = 0
        return result

    # 实际调用 LLM
    from app.services.llm import get_llm_service

    service = get_llm_service()
    start = time.monotonic()

    try:
        import asyncio
        response = asyncio.run(service.review_pr(
            pr_title=case.pr_title,
            pr_description=case.pr_description,
            diff=case.diff,
            language="zh",
        ))
    except Exception as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        return EvalResult(
            case_id=case.case_id,
            title=case.title,
            error=f"{type(exc).__name__}: {exc}",
            duration_ms=elapsed,
        )

    elapsed = int((time.monotonic() - start) * 1000)

    if response.error:
        return EvalResult(
            case_id=case.case_id,
            title=case.title,
            error=response.error,
            duration_ms=elapsed,
        )

    result = evaluate_output(case, response.raw_markdown)
    result.duration_ms = elapsed

    if verbose:
        print(f"\n{'='*60}")
        print(f"LLM 原始输出 ({case.case_id}):")
        print(f"{'='*60}")
        print(response.raw_markdown[:2000])
        if len(response.raw_markdown) > 2000:
            print(f"\n... (截断, 共 {len(response.raw_markdown)} 字符)")
        print(f"{'='*60}\n")

    return result


def generate_mock_review(case: EvalCase) -> str:
    """生成模拟审核报告（用于 dry-run 测试 runner 本身）。"""
    lines = [f"## 📋 PR Summary\n\nEval for {case.title}\n"]
    lines.append(f"## 🔧 Changed Modules\n")
    lines.append(f"## ⚠️ Potential Risks\n")

    bug_lines = ["## 🐛 Bug Suggestions\n"]
    for i, f in enumerate(case.expected_findings[:3], 1):
        bug_lines.append(
            f"{i}. **`{f.file}:{f.line}`** {f.severity} — {f.description}\n"
        )
    lines.append("\n".join(bug_lines))
    lines.append("## ⚡ Performance Suggestions\n\nNone identified.\n")
    lines.append("## 🔒 Security Suggestions\n\n")
    lines.append("```python\ndef fix():\n    pass\n```\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 结果展示
# ---------------------------------------------------------------------------

def print_summary(all_results: list[EvalResult]) -> None:
    """打印评分汇总表。"""
    total = len(all_results)
    passed_cases = sum(1 for r in all_results if r.passed_all)
    total_findings = sum(r.total for r in all_results)
    total_passed = sum(r.passed for r in all_results)
    total_missed = sum(r.missed for r in all_results)
    total_sev_correct = sum(r.severity_correct for r in all_results)
    total_time = sum(r.duration_ms for r in all_results)

    print()
    print("=" * 72)
    print("  AI PR Review — Eval 评分报告")
    print("=" * 72)
    print()

    # 表头
    print(f"{'Case':<8} {'Title':<28} {'通过/总计':<12} {'召回率':<8} {'严重匹配':<10} {'耗时':<8}")
    print("-" * 72)

    for r in all_results:
        if r.error:
            print(f"  {r.case_id:<6} {r.title:<28} {'❌ ERROR':<12} {'':8} {'':10} {r.duration_ms:>4}ms")
            continue

        recall_pct = r.recall * 100
        sev_pct = (r.severity_correct / r.total * 100) if r.total > 0 else 0
        status = "✅" if r.passed_all else "⚠️"
        print(
            f"  {r.case_id:<6} {r.title:<28} "
            f"{status} {r.passed}/{r.total:<6} "
            f"{recall_pct:>5.0f}%   "
            f"{sev_pct:>4.0f}%   "
            f"{r.duration_ms:>4}ms"
        )

    print("-" * 72)

    # 汇总行
    recall_total = (total_passed / total_findings * 100) if total_findings > 0 else 0
    sev_total = (total_sev_correct / total_findings * 100) if total_findings > 0 else 0

    print(
        f"  {'总计':<6} {f'{passed_cases}/{total} cases':<28} "
        f"{'✓':<2} {total_passed}/{total_findings:<5} "
        f"{recall_total:>5.0f}%   "
        f"{sev_total:>4.0f}%   "
        f"{total_time:>4}ms"
    )
    print()

    # 详细错误
    errors = [r for r in all_results if r.error]
    if errors:
        print("❌ 错误详情:")
        for r in errors:
            print(f"   Case {r.case_id} ({r.title}): {r.error}")
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AI PR Review — Prompt Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用例:
  python eval/runner.py                        跑全部用例
  python eval/runner.py --case 001             跑单个用例
  python eval/runner.py --dry-run              测试 runner 本身（不调 LLM）
  python eval/runner.py --verbose              显示完整 LLM 输出
        """,
    )
    parser.add_argument("--case", type=str, help="运行指定用例编号（如 001）")
    parser.add_argument("--provider", type=str, default="deepseek", help="LLM 提供商")
    parser.add_argument("--verbose", action="store_true", help="显示完整 LLM 输出")
    parser.add_argument("--dry-run", action="store_true", help="不调 LLM，用模拟响应测试 runner")
    args = parser.parse_args()

    # 加载用例
    all_cases = load_all_cases()

    if not all_cases:
        print("⚠️  没有找到测试用例 (eval/case_*.md)")
        sys.exit(1)

    # 筛选用例
    if args.case:
        cases = [c for c in all_cases if c.case_id == args.case]
        if not cases:
            print(f"⚠️  未找到 Case {args.case}")
            print(f"   可用用例: {', '.join(c.case_id for c in all_cases)}")
            sys.exit(1)
    else:
        cases = all_cases

    print(f"\n📋 加载 {len(cases)}/{len(all_cases)} 个测试用例")
    print(f"   Provider: {args.provider}")
    print(f"   Dry run:  {'✅' if args.dry_run else '❌'}")

    # 运行
    results = []
    for case in cases:
        print(f"\n▶️  Case {case.case_id}: {case.title} ", end="", flush=True)

        result = run_single_case(
            case=case,
            provider=args.provider,
            verbose=args.verbose,
            dry_run=args.dry_run,
        )

        if result.error:
            print(f"❌ {result.error[:60]}")
        elif result.passed_all:
            print(f"✅ {result.passed}/{result.total} 通过 ({result.recall:.0%})")
        else:
            print(f"⚠️  {result.passed}/{result.total} 通过 ({result.recall:.0%}), "
                  f"漏检 {result.missed} 项")

        results.append(result)

    # 汇总
    print_summary(results)

    # 退出码
    failed = sum(1 for r in results if not r.passed_all or r.error)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
