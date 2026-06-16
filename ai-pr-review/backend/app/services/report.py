"""
Report generator — parses raw LLM output into structured ReviewReport.
"""
import json
import re
from dataclasses import dataclass, field

from app.core.config import settings
from app.core.exceptions import ReportParseError
from app.core.logging import setup_logging

logger = setup_logging(__name__)


@dataclass
class Issue:
    """A single code review finding."""

    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    severity: str = "minor"
    category: str = "best_practice"
    title: str = ""
    body: str = ""
    suggestion: str | None = None
    code_snippet: str | None = None


@dataclass
class ReviewReport:
    """Parsed and validated review report."""

    overall_score: int = 0
    total_issues: int = 0
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    info_count: int = 0
    issues: list[Issue] = field(default_factory=list)

    VALID_SEVERITIES = {"critical", "major", "minor", "info"}
    VALID_CATEGORIES = {
        "security", "performance", "bug", "design",
        "style", "best_practice", "readability",
    }


class ReportGenerator:
    """Parse and validate LLM response into a structured ReviewReport."""

    @staticmethod
    def generate(raw_llm_output: str) -> ReviewReport:
        """
        Parse raw LLM response into a validated ReviewReport.

        Strategy:
        1. Try direct JSON parse.
        2. Try to extract JSON from markdown code block.
        3. Try to extract JSON from any code block.
        4. If all fail, raise ReportParseError.
        """
        content = raw_llm_output.strip()

        # Strategy 1: Direct JSON
        report = ReportGenerator._try_parse_json(content)
        if report:
            return report

        # Strategy 2: JSON in markdown code block
        json_match = re.search(
            r"```(?:json)?\s*\n(.+?)\n```", content, re.DOTALL
        )
        if json_match:
            report = ReportGenerator._try_parse_json(json_match.group(1))
            if report:
                return report

        # Strategy 3: First balanced JSON object in surrounding prose
        json_object = ReportGenerator._extract_balanced_json_object(content)
        if json_object:
            report = ReportGenerator._try_parse_json(json_object)
            if report:
                return report

        raise ReportParseError(
            "Failed to parse LLM response as JSON after 3 strategies"
        )

    @staticmethod
    def _try_parse_json(text: str) -> ReviewReport | None:
        """Attempt to parse text as JSON and validate structure."""
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict):
            return None

        # Extract issues
        raw_issues = data.get("issues", [])
        if not isinstance(raw_issues, list):
            raw_issues = []

        seen_dedup = set()
        issues: list[Issue] = []
        score_map = {"critical": 0, "major": 0, "minor": 0, "info": 0}

        for raw in raw_issues:
            if not isinstance(raw, dict):
                continue

            severity = str(raw.get("severity", "minor")).lower()
            if severity not in ReviewReport.VALID_SEVERITIES:
                severity = "minor"

            category = str(raw.get("category", "best_practice")).lower()
            if category not in ReviewReport.VALID_CATEGORIES:
                category = "best_practice"

            file_path = str(raw.get("file_path", ""))
            title = str(raw.get("title", ""))[:256]
            line_start = raw.get("line_start")
            if line_start is not None:
                try:
                    line_start = int(line_start)
                except (ValueError, TypeError):
                    line_start = None

            # Dedup key: file_path + line_start + title
            dedup_key = f"{file_path}:{line_start}:{title}"
            if dedup_key in seen_dedup:
                continue
            seen_dedup.add(dedup_key)

            issue = Issue(
                file_path=file_path,
                line_start=line_start,
                line_end=raw.get("line_end"),
                severity=severity,
                category=category,
                title=title,
                body=str(raw.get("body", "")),
                suggestion=str(raw.get("suggestion")) if raw.get("suggestion") else None,
                code_snippet=str(raw.get("code_snippet")) if raw.get("code_snippet") else None,
            )
            issues.append(issue)
            score_map[severity] = score_map.get(severity, 0) + 1

            if len(issues) >= settings.MAX_COMMENTS_PER_REVIEW:
                logger.info("Issue limit reached (%d)", settings.MAX_COMMENTS_PER_REVIEW)
                break

        overall_score = data.get("overall_score", 0)
        if not isinstance(overall_score, (int, float)) or overall_score < 0 or overall_score > 100:
            overall_score = 0

        return ReviewReport(
            overall_score=int(overall_score),
            total_issues=len(issues),
            critical_count=score_map.get("critical", 0),
            major_count=score_map.get("major", 0),
            minor_count=score_map.get("minor", 0),
            info_count=score_map.get("info", 0),
            issues=issues,
        )

    @staticmethod
    def _extract_balanced_json_object(text: str) -> str | None:
        """Extract the first balanced JSON object from mixed LLM text."""
        start = text.find("{")
        while start != -1:
            depth = 0
            in_string = False
            escaped = False

            for index in range(start, len(text)):
                char = text[index]
                if escaped:
                    escaped = False
                    continue
                if char == "\\":
                    escaped = True
                    continue
                if char == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[start:index + 1]
                        if ReportGenerator._try_parse_json(candidate):
                            return candidate
                        break

            start = text.find("{", start + 1)
        return None
