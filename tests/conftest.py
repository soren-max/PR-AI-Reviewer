"""
pytest shared fixtures for AI PR Review tests.
"""
from __future__ import annotations

import json
import time
from typing import Any
from unittest.mock import MagicMock, AsyncMock

import requests
import pytest


# ===========================================================================
# GitHub URL parser fixtures
# ===========================================================================

@pytest.fixture
def valid_pr_urls() -> list[tuple[str, str, str, int]]:
    """(url, expected_owner, expected_repo, expected_pull_number)"""
    return [
        ("https://github.com/owner/repo/pull/42", "owner", "repo", 42),
        ("https://www.github.com/my-org/my-repo/pull/1", "my-org", "my-repo", 1),
        ("https://github.com/owner/repo/pull/42/", "owner", "repo", 42),
        ("https://github.com/owner/repo/pull/42?diff=unified", "owner", "repo", 42),
        ("https://github.com/owner/repo/pull/42#top", "owner", "repo", 42),
        ("https://github.com/owner/repo/pull/1", "owner", "repo", 1),
        ("https://github.com/owner/repo/pull/99999", "owner", "repo", 99999),
    ]


@pytest.fixture
def invalid_pr_urls() -> list[str]:
    return [
        "https://gitlab.com/owner/repo/merge_requests/1",
        "https://bitbucket.org/owner/repo/pull-requests/1",
        "not-a-url",
        "",
        "   ",
        "https://github.com/owner/repo/issues/1",
        "https://github.com/owner/repo/tree/main",
        "https://github.com/owner/repo/pull/abc",
    ]


# ===========================================================================
# GitHub API client fixtures
# ===========================================================================

SAMPLE_PR_METADATA: dict[str, Any] = {
    "number": 1,
    "state": "open",
    "title": "Fix login redirect",
    "body": "Updated the callback URL to use HTTPS.",
    "user": {"login": "octocat"},
    "base": {"ref": "main", "sha": "abc123", "repo": {"full_name": "octocat/Hello-World"}},
    "head": {"ref": "feat/fix", "sha": "def456", "repo": {"full_name": "octocat/Hello-World"}},
    "mergeable": True,
    "changed_files": 2,
    "additions": 50,
    "deletions": 10,
    "html_url": "https://github.com/octocat/Hello-World/pull/1",
    "created_at": "2025-01-15T10:00:00Z",
    "updated_at": "2025-01-15T12:00:00Z",
}

SAMPLE_FILES: list[dict[str, Any]] = [
    {
        "filename": "README.md",
        "status": "modified",
        "additions": 30,
        "deletions": 5,
        "changes": 35,
        "patch": "@@ -1,3 +1,5 @@\n+# Installation\n+Run `pip install`",
        "raw_url": "https://raw.githubusercontent.com/...",
        "blob_url": "https://github.com/...",
        "contents_url": "https://api.github.com/...",
    },
]

SAMPLE_DIFF = (
    "diff --git a/README.md b/README.md\n"
    "index abc..def 100644\n"
    "--- a/README.md\n"
    "+++ b/README.md\n"
    "@@ -1,3 +1,5 @@\n"
    " # Hello World\n"
    "+## Installation\n"
    "+Run `pip install`"
)


@pytest.fixture
def mock_github_responses() -> dict[str, MagicMock]:
    """Returns a dict of mock response factories for different GitHub API calls."""

    def _make_resp(status: int = 200, json_data: Any = None, text: str = "") -> MagicMock:
        resp = MagicMock(spec=requests.Response)
        resp.status_code = status
        resp.headers = {
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Reset": str(int(time.time()) + 3600),
            "X-RateLimit-Used": "1",
        }
        resp.request = MagicMock()
        resp.request.path_url = "/repos/octocat/Hello-World/pulls/1"
        resp.ok = status < 400

        if status >= 400:
            resp.raise_for_status = MagicMock(
                side_effect=requests.HTTPError(f"{status} Error", response=resp)
            )
        else:
            resp.raise_for_status = MagicMock()

        if json_data is not None:
            resp.json = MagicMock(return_value=json_data)
            resp.text = json.dumps(json_data)
            resp.content = resp.text.encode()
        else:
            resp.text = text
            resp.content = text.encode()

        return resp

    return {
        "pr_meta": _make_resp(200, SAMPLE_PR_METADATA),
        "pr_files": _make_resp(200, SAMPLE_FILES),
        "pr_diff": _make_resp(200, text_data=SAMPLE_DIFF),
        "not_found": _make_resp(404),
        "auth_error": _make_resp(401),
        "rate_limited": _make_resp(429, headers={"Retry-After": "1"}),
        "server_error": _make_resp(503),
    }


@pytest.fixture
def github_client() -> Any:
    """Import and return GitHubClient instance (requires requests)."""
    from github_client import GitHubClient
    return GitHubClient(token="test-token-12345", max_retries=0)


# ===========================================================================
# LLM / Review service fixtures
# ===========================================================================

@pytest.fixture
def sample_llm_report() -> str:
    return (
        "## 📋 PR Summary\n\n"
        "Clean fix for login redirect.\n\n"
        "## 🔧 Changed Modules\n\n"
        "- `src/auth.py` — Added redirect validation\n\n"
        "## ⚠️ Potential Risks\n\n"
        "None identified.\n\n"
        "## 🐛 Bug Suggestions\n\n"
        "1. **`src/auth.py:42`** 🟠 Major — Missing null check\n\n"
        "## ⚡ Performance Suggestions\n\n"
        "None identified.\n\n"
        "## 🔒 Security Suggestions\n\n"
        "None identified.\n"
    )
