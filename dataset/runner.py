#!/usr/bin/env python3
"""
Golden Dataset Runner — 批量测试 LLM 代码审查能力。

用法:
    python dataset/runner.py                                 # 跑全部 + 全部模型
    python dataset/runner.py --category security              # 只跑安全类
    python dataset/runner.py --models deepseek,openai         # 指定模型
    python dataset/runner.py --dry-run                        # 测试 runner 本身
    python dataset/runner.py --report                         # 只生成报告

输出:
    dataset/reports/
    ├── deepseek_20250115_120000.json
    ├── openai_20250115_120000.json
    └── comparison_20250115_120000.md
"""
from __future__ import annotations

import argparse
import glob
import importlib
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _PROJECT_ROOT)

DATASET_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(DATASET_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class GoldenItem:
    """单个黄金数据集条目。"""
    id: str
    category: str
    severity: str
    description: str
    cwe: str
    code: str
    diff: str
    expected_findings: list[dict]
    reference_fix: str


@dataclass
class EvalMetric:
    found: int = 0
    missed: int = 0
    severity_correct: int = 0
    has_fix_suggestion: bool = False

    @property
    def total(self) -> int:
        return self.found + self.missed

    @property
    def recall(self) -> float:
        if self.total == 0:
            return 1.0
        return self.found / self.total

    @property
    def passed(self) -> bool:
        return self.missed == 0


@dataclass
class ModelResult:
    model_name: str
    item_id: str
    description: str
    metric: EvalMetric
    raw_output: str = ""
    error: Optional[str] = None
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# 加载数据集
# ---------------------------------------------------------------------------

def load_all_items() -> list[GoldenItem]:
    """递归加载 dataset/ 下所有 .py 数据点。"""
    items = []
    pattern = os.path.join(DATASET_DIR, "**", "*.py")
    for f in sorted(glob.glob(pattern, recursive=True)):
        if os.path.basename(f) in ("runner.py", "report.py", "__init__.py"):
            continue
        item = load_single_item(f)
        if item:
            items.append(item)
    return items


def load_single_item(file_path: str) -> Optional[GoldenItem]:
    """加载单个数据点文件（动态 import）。"""
    rel_path = os.path.relpath(file_path, _PROJECT_ROOT)
    module_name = rel_path.replace(os.sep, ".").replace(".py", "")

    try:
        mod = importlib.import_module(module_name)
    except Exception as exc:
        print(f"  ⚠️  加载失败 {file_path}: {exc}")
        return None

    return GoldenItem(
        id=getattr(mod, "ID", os.path.basename(file_path)),
        category=getattr(mod, "CATEGORY", "unknown"),
        severity=getattr(mod, "SEVERITY", "unknown"),
        description=getattr(mod, "DESCRIPTION", ""),
        cwe=getattr(mod, "CWE", ""),
        code=getattr(mod, "CODE", ""),
        diff=getattr(mod, "DIFF", ""),
        expected_findings=getattr(mod, "EXPECTED_FINDINGS", []),
        reference_fix=getattr(mod, "REFERENCE_FIX", ""),
    )


# ---------------------------------------------------------------------------
# 评分逻辑
# ---------------------------------------------------------------------------

def evaluate_output(item: GoldenItem, output: str) -> EvalMetric:
    """检查 LLM 输出是否命中预期发现。"""
    metric = EvalMetric()
    output_lower = output.lower()

    for finding in item.expected_findings:
        keywords = _extract_keywords(finding["description"])
        found = any(kw.lower() in output_lower for kw in keywords)

        if found:
            metric.found += 1
            sev = finding.get("severity", "").lower()
            if sev and sev in output_lower:
                metric.severity_correct += 1
        else:
            metric.missed += 1

    metric.has_fix_suggestion = "```" in output
    return metric


def _extract_keywords(text: str) -> list[str]:
    """从描述中提取关键词。"""
    stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
                 "都", "一", "也", "很", "到", "说", "要", "去", "你", "会",
                 "the", "a", "an", "in", "on", "at", "to", "for", "of", "by"}
    import re
    terms = re.findall(r"[\w\u4e00-\u9fff]+", text)
    return [t for t in terms if len(t) >= 2 and t.lower() not in stopwords]


# ---------------------------------------------------------------------------
# 运行
# ---------------------------------------------------------------------------

def run_item(
    item: GoldenItem,
    model_name: str = "deepseek",
    dry_run: bool = False,
) -> ModelResult:
    """对单个数据集条目运行指定模型的审查。"""
    start = time.monotonic()

    if dry_run:
        mock_output = _mock_review(item)
        metric = evaluate_output(item, mock_output)
        elapsed = 0
        return ModelResult(
            model_name=model_name,
            item_id=item.id,
            description=item.description,
            metric=metric,
            raw_output=mock_output,
            duration_ms=elapsed,
        )

    # 实际调用 LLM
    try:
        from app.services.llm import get_llm_service
        service = get_llm_service()

        import asyncio
        response = asyncio.run(service.review_pr(
            pr_title=f"[Dataset] {item.id}: {item.description}",
            pr_description=f"Category: {item.category} | Severity: {item.severity}",
            diff=item.diff,
            language="zh",
        ))

        elapsed = int((time.monotonic() - start) * 1000)

        if response.error:
            return ModelResult(
                model_name=model_name,
                item_id=item.id,
                description=item.description,
                metric=EvalMetric(),
                error=response.error,
                duration_ms=elapsed,
            )

        metric = evaluate_output(item, response.raw_markdown)
        return ModelResult(
            model_name=model_name,
            item_id=item.id,
            description=item.description,
            metric=metric,
            raw_output=response.raw_markdown,
            duration_ms=elapsed,
        )

    except Exception as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        return ModelResult(
            model_name=model_name,
            item_id=item.id,
            description=item.description,
            metric=EvalMetric(),
            error=f"{type(exc).__name__}: {exc}",
            duration_ms=elapsed,
        )


def _mock_review(item: GoldenItem) -> str:
    """生成模拟审查报告（用于 dry-run）。"""
    lines = [f"## 📋 PR Summary\n\n审查 {item.description}\n"]
    lines.append("## 🔧 Changed Modules\n")
    lines.append("## ⚠️ Potential Risks\n")
    lines.append("## 🐛 Bug Suggestions\n")
    for i, f in enumerate(item.expected_findings[:3], 1):
        cwe = f.get("cwe", "")
        lines.append(
            f"{i}. **`code.py`** {f['severity'].upper()} — "
            f"{f['description']} {f'+ CWE: {cwe}' if cwe else ''}\n"
        )
    lines.append("\n```python\ndef fix():\n    pass\n```\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 批量运行
# ---------------------------------------------------------------------------

def run_batch(
    items: list[GoldenItem],
    models: list[str],
    dry_run: bool = False,
    category: Optional[str] = None,
) -> dict[str, list[ModelResult]]:
    """对多个模型批量运行数据集。"""
    if category:
        items = [i for i in items if i.category == category]

    all_results: dict[str, list[ModelResult]] = {m: [] for m in models}

    for item in items:
        print(f"\n  📦 {item.id} [{item.category}] {item.description[:50]}")
        for model in models:
            result = run_item(item, model_name=model, dry_run=dry_run)
            all_results[model].append(result)

            status = "✅" if result.metric.passed and not result.error else "⚠️"
            recall = f"{result.metric.recall:.0%}" if result.metric.total > 0 else "-"
            print(f"    {status} {model:10s} 召回={recall}  "
                  f"{result.metric.found}/{result.metric.total}  "
                  f"{f'❌ {result.error[:30]}' if result.error else ''}")

    return all_results


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------

def generate_report(
    all_results: dict[str, list[ModelResult]],
    items: list[GoldenItem],
) -> str:
    """生成模型对比报告（Markdown）。"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    models = list(all_results.keys())

    lines = [
        f"# Golden Dataset 评测报告",
        f"",
        f"**时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**模型**: {', '.join(models)}",
        f"**数据集**: {sum(len(v) for v in all_results.values())} 条",
        f"",
        f"## 汇总",
        f"",
        f"| 模型 | 通过率 | 召回率 | 严重匹配 | 建议率 | 平均耗时 |",
        f"|------|--------|--------|----------|--------|----------|",
    ]

    for model in models:
        results = all_results[model]
        total = len(results)
        passed = sum(1 for r in results if r.metric.passed and not r.error)
        errors = sum(1 for r in results if r.error)
        total_findings = sum(r.metric.total for r in results)
        total_found = sum(r.metric.found for r in results)
        total_sev = sum(r.metric.severity_correct for r in results)
        total_suggest = sum(1 for r in results if r.metric.has_fix_suggestion)
        avg_time = sum(r.duration_ms for r in results) / max(total, 1)

        pass_rate = passed / total * 100
        recall = total_found / total_findings * 100 if total_findings else 0
        sev_rate = total_sev / total_findings * 100 if total_findings else 0
        suggest_rate = total_suggest / total * 100
        error_str = f" ({errors} err)" if errors else ""

        lines.append(
            f"| {model:10s} | {pass_rate:5.1f}%{error_str:8s} | "
            f"{recall:5.1f}% | {sev_rate:5.1f}% | "
            f"{suggest_rate:5.1f}% | {avg_time:6.0f}ms |"
        )

    lines.extend(["", "## 按类别", "", f"| 类别 | 模型 | 通过数 | 召回率 | 严重匹配 |", f"|------|------|--------|--------|----------|"])

    for cat_name in sorted(set(i.category for i in items)):
        for model in models:
            cat_results = [
                r for r in all_results[model]
                if any(i.id == r.item_id and i.category == cat_name for i in items)
            ]
            if not cat_results:
                continue
            total_f = sum(r.metric.total for r in cat_results)
            found = sum(r.metric.found for r in cat_results)
            sev = sum(r.metric.severity_correct for r in cat_results)
            recall = found / total_f * 100 if total_f else 0
            sev_rate = sev / total_f * 100 if total_f else 0
            lines.append(
                f"| {cat_name:10s} | {model:10s} | "
                f"{sum(1 for r in cat_results if r.metric.passed):>2}/{len(cat_results):<2} | "
                f"{recall:5.1f}% | {sev_rate:5.1f}% |"
            )

    # 详细结果
    lines.extend(["", "## 详细结果", ""])
    for model in models:
        lines.append(f"### {model}")
        lines.append("")
        lines.append("| ID | 描述 | 状态 | 召回 | 耗时 |")
        lines.append("|----|------|------|------|------|")
        for r in all_results[model]:
            status = "✅" if r.metric.passed and not r.error else "❌"
            recall = f"{r.metric.recall:.0%}" if r.metric.total > 0 else "-"
            err = f" {r.error[:30]}" if r.error else ""
            lines.append(
                f"| {r.item_id} | {r.description[:40]} | {status} | "
                f"{recall} ({r.metric.found}/{r.metric.total}) | "
                f"{r.duration_ms}ms{err} |"
        )
        lines.append("")

    report = "\n".join(lines)
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Golden Dataset Runner — 批量测试 LLM 代码审查能力",
    )
    parser.add_argument("--models", default="deepseek", help="逗号分隔的模型列表")
    parser.add_argument("--category", help="只跑指定类别 (security/performance/bug)")
    parser.add_argument("--dry-run", action="store_true", help="不调 LLM")
    parser.add_argument("--report", action="store_true", help="只生成报告")
    parser.add_argument("--save", action="store_true", help="保存报告到 dataset/reports/")
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",")]

    print(f"\n📊 Golden Dataset")
    print(f"   Models:    {', '.join(models)}")
    print(f"   Category:  {args.category or 'all'}")
    print(f"   Dry run:   {'✅' if args.dry_run else '❌'}")

    # 加载数据集
    items = load_all_items()
    print(f"   Dataset:   {len(items)} items")

    if not items:
        print("⚠️  没有加载到数据点")
        sys.exit(1)

    # 运行
    all_results = run_batch(items, models, dry_run=args.dry_run, category=args.category)

    # 生成报告
    report = generate_report(all_results, items)
    print(f"\n{'='*60}")
    print(report)

    # 保存报告
    if args.save:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(REPORT_DIR, f"comparison_{timestamp}.md")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n📄 报告已保存: {report_file}")

        # 保存原始结果
        for model, results in all_results.items():
            raw_file = os.path.join(REPORT_DIR, f"{model}_{timestamp}.json")
            with open(raw_file, "w", encoding="utf-8") as f:
                json.dump(
                    [
                        {
                            "item_id": r.item_id,
                            "description": r.description,
                            "metric": {
                                "found": r.metric.found,
                                "missed": r.metric.missed,
                                "recall": r.metric.recall,
                                "passed": r.metric.passed,
                                "has_fix": r.metric.has_fix_suggestion,
                            },
                            "error": r.error,
                            "duration_ms": r.duration_ms,
                        }
                        for r in results
                    ],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            print(f"📄 原始数据: {raw_file}")


if __name__ == "__main__":
    main()
