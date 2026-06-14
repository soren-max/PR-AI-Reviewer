"""
Unit tests for ReportGenerator.
"""
import pytest

from app.services.report import ReportGenerator, ReviewReport


class TestReportGenerator:
    VALID_LLM_OUTPUT = """{
        "overall_score": 85,
        "summary": {
            "total_issues": 2,
            "critical_count": 1,
            "major_count": 0,
            "minor_count": 1,
            "info_count": 0
        },
        "issues": [
            {
                "file_path": "src/auth.py",
                "line_start": 42,
                "line_end": 45,
                "severity": "critical",
                "category": "security",
                "title": "Hardcoded secret",
                "body": "Secret key is hardcoded in source",
                "suggestion": "Use environment variables",
                "code_snippet": "SECRET_KEY = 'abc123'"
            },
            {
                "file_path": "src/utils.py",
                "line_start": 10,
                "severity": "minor",
                "category": "style",
                "title": "Unused import",
                "body": "`os` is imported but never used"
            }
        ]
    }"""

    def test_parse_valid_json(self):
        report = ReportGenerator.generate(self.VALID_LLM_OUTPUT)
        assert isinstance(report, ReviewReport)
        assert report.overall_score == 85
        assert report.total_issues == 2
        assert report.critical_count == 1
        assert report.minor_count == 1
        assert report.issues[0].file_path == "src/auth.py"
        assert report.issues[0].severity == "critical"

    def test_parse_json_in_markdown(self):
        """Should extract JSON from markdown code block."""
        markdown_output = f"Here is the review:\n\n```json\n{self.VALID_LLM_OUTPUT}\n```\n\nEnd."
        report = ReportGenerator.generate(markdown_output)
        assert report.overall_score == 85
        assert report.total_issues == 2

    def test_parse_json_from_braces(self):
        """Should extract JSON from bare braces as last resort."""
        text = f"Some text {{{self.VALID_LLM_OUTPUT}}} more text"
        report = ReportGenerator.generate(text)
        assert report.overall_score == 85

    def test_parse_empty_issues(self):
        output = '{"overall_score": 100, "summary": {"total_issues": 0}, "issues": []}'
        report = ReportGenerator.generate(output)
        assert report.total_issues == 0
        assert len(report.issues) == 0

    def test_parse_invalid_severity_uses_default(self):
        output = """{
            "overall_score": 70,
            "summary": {"total_issues": 1},
            "issues": [
                {"file_path": "a.py", "severity": "unknown_level", "category": "bug", "title": "test", "body": "body"}
            ]
        }"""
        report = ReportGenerator.generate(output)
        assert report.issues[0].severity == "minor"

    def test_parse_completely_invalid(self):
        with pytest.raises(Exception):
            ReportGenerator.generate("This is not JSON at all [[[")

    def test_parse_deduplication(self):
        """Duplicate issues (same file + line + title) should be removed."""
        output = """{
            "overall_score": 80,
            "summary": {"total_issues": 2},
            "issues": [
                {"file_path": "a.py", "line_start": 1, "severity": "major", "category": "bug", "title": "Same issue", "body": "First"},
                {"file_path": "a.py", "line_start": 1, "severity": "major", "category": "bug", "title": "Same issue", "body": "Duplicate"}
            ]
        }"""
        report = ReportGenerator.generate(output)
        assert len(report.issues) == 1
