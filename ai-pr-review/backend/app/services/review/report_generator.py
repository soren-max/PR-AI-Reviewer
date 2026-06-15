"""
Report Generator — 将 LLM 原始输出转换为最终审查报告。

Clean Architecture 层级: Domain
依赖:
  - RiskResult（风险信息）
  - DiffResult（Diff 摘要）

职责:
  1. 解析 LLM 的 JSON 输出
  2. 注入风险分析和 Diff 统计信息
  3. 格式化为最终的 Markdown / JSON 报告
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from app.services.review.risk_analyzer import RiskResult
from app.services.review.diff_parser import DiffResult

logger = logging.getLogger("services.review.report")


@dataclass
class ReviewIssue:
    """A single review issue found by the LLM."""
    severity: str = "minor"
    title: str = ""
    file: str = ""
    line: int = 0
    category: str = "maintainability"
    reason: str = ""
    suggestion: str = ""
    cwe: str = ""


@dataclass
class ReviewReport:
    """Final structured review report.

    Combines LLM output with risk analysis and diff statistics.
    """
    summary: str = ""
    changed_modules: list[str] = field(default_factory=list)
    issues: list[ReviewIssue] = field(default_factory=list)
    raw_llm_output: str = ""

    # Injected by pipeline
    risk_level: str = "low"
    risk_score: int = 0
    risk_reason: str = ""
    diff_summary: str = ""
    llm_error: Optional[str] = None

    def to_markdown(self) -> str:
        """Render the report as Markdown (for frontend display)."""
        lines: list[str] = []

        # Risk banner
        if self.risk_level in ("critical", "high"):
            emoji = "🔴" if self.risk_level == "critical" else "⚠️"
            lines.append(f"> {emoji} **Risk Level: {self.risk_level.upper()}**")
            lines.append(f"> {self.risk_reason}")
            lines.append("")

        # Summary
        lines.append("## 📋 Review Summary")
        lines.append("")
        lines.append(self.summary or self.raw_llm_output.split("## ")[0] if self.raw_llm_output else "_No summary available._")
        lines.append("")

        # Diff statistics
        lines.append(f"**Diff**: {self.diff_summary}")
        lines.append("")

        if self.llm_error:
            lines.append(f"⚠️ **LLM Error**: {self.llm_error}")
            return "\n".join(lines)

        # Issues
        if not self.issues:
            lines.append("✅ **No issues found.**")
            lines.append("")
            return "\n".join(lines)

        # Group by category
        categories = {"bug": [], "security": [], "performance": [], "maintainability": []}
        for issue in self.issues:
            cat = issue.category if issue.category in categories else "maintainability"
            categories[cat].append(issue)

        sev_labels = {"critical": "🔴 Critical", "major": "🟠 Major", "minor": "🟡 Minor", "nit": "⚪ Nit"}

        for cat_name, cat_issues in categories.items():
            if not cat_issues:
                continue

            cat_emoji = {"bug": "🐛", "security": "🔒", "performance": "⚡", "maintainability": "🏗️"}
            lines.append(f"## {cat_emoji.get(cat_name, '📋')} {cat_name.capitalize()} ({len(cat_issues)})")
            lines.append("")

            for i, issue in enumerate(cat_issues, 1):
                sev_label = sev_labels.get(issue.severity, issue.severity)
                lines.append(f"### {i}. {sev_label} — {issue.title}")
                lines.append("")
                if issue.file:
                    loc = f"`{issue.file}`"
                    if issue.line:
                        loc += f":{issue.line}"
                    lines.append(f"**Location**: {loc}")
                    lines.append("")
                if issue.cwe:
                    lines.append(f"**CWE**: {issue.cwe}")
                    lines.append("")
                lines.append(f"**Reason**: {issue.reason}")
                lines.append("")
                if issue.suggestion:
                    lines.append(f"**Suggestion**:")
                    lines.append("")
                    lines.append("```python")
                    lines.append(issue.suggestion)
                    lines.append("```")
                    lines.append("")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps({
            "summary": self.summary,
            "changed_modules": self.changed_modules,
            "issues": [
                {
                    "severity": i.severity,
                    "title": i.title,
                    "file": i.file,
                    "line": i.line,
                    "category": i.category,
                    "reason": i.reason,
                    "suggestion": i.suggestion,
                    "cwe": i.cwe,
                }
                for i in self.issues
            ],
            "risk": {
                "level": self.risk_level,
                "score": self.risk_score,
                "reason": self.risk_reason,
            },
            "diff_summary": self.diff_summary,
        }, ensure_ascii=False, indent=2)


class ReportGenerator:
    """Generate structured reports from LLM raw output."""

    def generate(
        self,
        raw_markdown: str,
        risk: Optional[RiskResult] = None,
        diff_summary: Optional[DiffResult] = None,
    ) -> ReviewReport:
        """Parse LLM raw markdown/JSON output into a ReviewReport."""
        report = ReviewReport(raw_llm_output=raw_markdown)

        # Attach risk info
        if risk:
            report.risk_level = risk.risk_level.value
            report.risk_score = risk.score
            report.risk_reason = risk.reason

        # Attach diff summary
        if diff_summary:
            report.diff_summary = (
                f"{diff_summary.total_files_changed} files, "
                f"{diff_summary.total_additions} additions, "
                f"{diff_summary.total_deletions} deletions"
            )

        # Try to parse as JSON
        issues = self._try_parse_json(raw_markdown)
        if issues is not None:
            report.summary = issues.get("summary", "")
            report.changed_modules = issues.get("changed_modules", [])
            for raw_issue in issues.get("issues", []):
                if isinstance(raw_issue, dict):
                    report.issues.append(ReviewIssue(
                        severity=raw_issue.get("severity", "minor"),
                        title=raw_issue.get("title", ""),
                        file=raw_issue.get("file", ""),
                        line=raw_issue.get("line", 0) or 0,
                        category=raw_issue.get("category", "maintainability"),
                        reason=raw_issue.get("reason", ""),
                        suggestion=raw_issue.get("suggestion", ""),
                        cwe=raw_issue.get("cwe", ""),
                    ))

        return report

    def _try_parse_json(self, text: str) -> Optional[dict]:
        """Try to extract JSON from LLM output (handles markdown-wrapped JSON)."""
        # Strategy 1: Direct JSON parse
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from markdown code block
        json_match = re.search(r"```(?:json)?\s*\n(.+?)\n```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Strategy 3: First { } block
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            try:
                return json.loads(text[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass

        return None
