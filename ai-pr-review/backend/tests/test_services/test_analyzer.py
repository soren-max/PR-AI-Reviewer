"""
Unit tests for Analyzer service (prompt builder).
"""
from app.services.analyzer import build_system_prompt, build_user_prompt
from app.core.config import settings
from app.services.github import PRMetadata, FileDiff


def test_build_system_prompt_zh():
    prompt = build_system_prompt(language="zh")
    assert "Staff Software Engineer" in prompt
    assert "严重级别" in prompt
    assert "critical" in prompt
    assert "output format" not in prompt


def test_build_system_prompt_en():
    prompt = build_system_prompt(language="en")
    assert "Staff Software Engineer" in prompt
    assert "severity" in prompt
    assert "critical" in prompt


def test_build_user_prompt_includes_pr_info():
    pr_info = PRMetadata(
        title="Add auth",
        author="alice",
        base_branch="main",
        head_branch="feat/auth",
        changed_files_count=1,
        additions=10,
        deletions=2,
    )
    diffs = [
        FileDiff(
            filename="src/auth.py",
            status="modified",
            additions=10,
            deletions=2,
            patch="diff --git a/src/auth.py b/src/auth.py\n@@ -1,5 +1,8 @@\n+import jwt",
        )
    ]
    prompt = build_user_prompt(pr_info, diffs)
    assert "Add auth" in prompt
    assert "alice" in prompt
    assert "main" in prompt
    assert "src/auth.py" in prompt
    assert "+import jwt" in prompt
    assert "```diff" in prompt


def test_build_user_prompt_respects_focus_areas():
    pr_info = PRMetadata(
        title="Test", author="bot", base_branch="main", head_branch="test",
        changed_files_count=1, additions=0, deletions=0,
    )
    prompt = build_user_prompt(pr_info, [], options={"focus_areas": ["security"]})
    assert "security" in prompt


def test_build_user_prompt_truncates_total_diff_size(monkeypatch):
    monkeypatch.setattr(settings, "MAX_DIFF_SIZE_BYTES", 20)
    pr_info = PRMetadata(
        title="Large diff", author="bot", base_branch="main", head_branch="large",
        changed_files_count=1, additions=100, deletions=0,
    )
    diffs = [
        FileDiff(
            filename="src/large.py",
            status="modified",
            additions=100,
            deletions=0,
            patch="x" * 100,
        )
    ]

    prompt = build_user_prompt(pr_info, diffs)

    assert len(prompt) < 500
    assert "diff truncated" in prompt
    assert "Some files were omitted" in prompt
