"""
Prompt builder — constructs system + user prompts from PR data.
"""
from app.services.github import FileDiff, PRMetadata
from app.core.config import settings
from app.core.logging import setup_logging

logger = setup_logging(__name__)

SYSTEM_PROMPT_ZH = """你是一位资深的 Staff Software Engineer，正在进行 Code Review。

## 审查职责
- 代码质量：逻辑正确性、边界条件、错误处理
- 安全性：注入、认证、授权、敏感数据泄露
- 性能：不必要的循环、内存泄漏、慢查询
- 可维护性：命名、职责划分、测试覆盖度、文档
- 最佳实践：遵循语言/框架惯例、DRY、SOLID

## 审查规则
1. 只审查 **变更部分**（diff），不要评论未修改的代码
2. 每个问题必须给出：严重级别、类别、文件名、行号、问题描述、改进建议
3. 如果发现有改进建议，必须提供 **示例代码**
4. 对于明显良好/安全的代码，不要无中生有提问题
5. 输出 **严格 JSON 格式**，不要加 Markdown 包裹或额外文字

## 严重级别定义
- **critical**: 会导致生产事故、安全漏洞或数据丢失
- **major**: 明显错误，可能导致运行时 bug
- **minor**: 代码风格或轻微可读性改进
- **info**: 建议或后续可以考虑的优化

## 输出格式
```json
{
  "overall_score": <0-100 整数>,
  "summary": {
    "total_issues": <整数>,
    "critical_count": <整数>,
    "major_count": <整数>,
    "minor_count": <整数>,
    "info_count": <整数>
  },
  "issues": [
    {
      "file_path": "src/file.ts",
      "line_start": <整数|null>,
      "line_end": <整数|null>,
      "severity": "critical" | "major" | "minor" | "info",
      "category": "security" | "performance" | "bug" | "design" | "style" | "best_practice" | "readability",
      "title": "简短标题",
      "body": "详细说明问题所在及原因",
      "suggestion": "改进建议（可选）",
      "code_snippet": "问题代码片段（可选）"
    }
  ]
}
```"""

SYSTEM_PROMPT_EN = """You are a Staff Software Engineer conducting a Code Review.

## Review Responsibilities
- Quality: correctness, edge cases, error handling
- Security: injection, auth, authorization, data leaks
- Performance: unnecessary loops, memory leaks, slow queries
- Maintainability: naming, single responsibility, test coverage, documentation
- Best practices: language/framework conventions, DRY, SOLID

## Rules
1. Only review the **changed lines** in the diff
2. Every issue must include: severity, category, file, line, description, suggestion
3. Provide **code examples** for improvement suggestions
4. Do NOT invent issues for clean/safe code
5. Output **pure JSON** only, no markdown wrapping

## Output Format
(Same as Chinese version — JSON structure identical)
```json
{
  "overall_score": <0-100>,
  "summary": { ... },
  "issues": [ ... ]
}
```"""


def build_system_prompt(language: str = "zh") -> str:
    """Build the system prompt based on language preference."""
    if language == "en":
        return SYSTEM_PROMPT_EN
    return SYSTEM_PROMPT_ZH


def build_user_prompt(
    pr_info: PRMetadata,
    diffs: list[FileDiff],
    options: dict | None = None,
) -> str:
    """
    Build the user prompt containing PR context and diffs.

    Args:
        pr_info: PR metadata (title, branches, stats).
        diffs: List of file diffs to review.
        options: User options like focus_areas.

    Returns:
        Formatted user prompt string.
    """
    lines: list[str] = []
    lines.append("# Pull Request Review Request")
    lines.append("")
    lines.append("## PR Overview")
    lines.append(f"- Title: {pr_info.title}")
    lines.append(f"- Author: {pr_info.author}")
    lines.append(f"- Branch: {pr_info.head_branch} → {pr_info.base_branch}")
    lines.append(f"- Changed files: {pr_info.changed_files_count}")
    lines.append(f"- Additions: {pr_info.additions} / Deletions: {pr_info.deletions}")
    lines.append("")

    # Focus areas
    opts = options or {}
    focus_areas = opts.get("focus_areas")
    if focus_areas:
        lines.append(f"- Focus areas: {', '.join(focus_areas)}")
        lines.append("")

    lines.append("## Changed Files")
    lines.append("")

    total_diff_size = 0
    file_count = 0
    truncated = False

    for diff in diffs:
        if diff.is_binary or diff.patch is None:
            lines.append(f"### {diff.filename} (binary / deleted — skipped)")
            lines.append("")
            continue

        file_count += 1
        if file_count > settings.MAX_FILES_PER_REVIEW:
            lines.append(f"### … and {len(diffs) - file_count + 1} more files (truncated)")
            truncated = True
            break

        lines.append(f"### {diff.filename} (+{diff.additions} -{diff.deletions})")
        lines.append("")
        lines.append("```diff")
        lines.append(diff.patch)
        lines.append("```")
        lines.append("")

        total_diff_size += len(diff.patch)

    if truncated:
        lines.append("> ⚠️ Some files were omitted due to the large diff size.\n")

    lines.append("## Instructions")
    lines.append("Please review the above changes and output the result in the specified JSON format.")
    lines.append("")

    prompt = "\n".join(lines)
    logger.info(
        "Built user prompt: %d chars, %d files, truncated=%s",
        len(prompt), file_count, truncated,
    )
    return prompt
