"""
Tests for the synchronous ``POST /api/v1/review`` endpoint.
"""
from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.core.config import settings
from app.core.exceptions import InvalidPRUrlError, PRNotFoundError


# ===========================================================================
# Test the Pydantic schema
# ===========================================================================

class TestReviewRequestSchema(unittest.TestCase):
    """``ReviewRequest`` validation."""

    def setUp(self) -> None:
        from app.schemas.review_request import ReviewRequest
        self.schema = ReviewRequest

    def test_valid_url(self) -> None:
        req = self.schema(pr_url="https://github.com/owner/repo/pull/42")
        self.assertEqual(req.pr_url, "https://github.com/owner/repo/pull/42")
        self.assertEqual(req.language, "zh")

    def test_valid_url_trailing_slash(self) -> None:
        req = self.schema(pr_url="https://github.com/a/b/pull/1/")
        self.assertEqual(req.pr_url, "https://github.com/a/b/pull/1/")

    def test_valid_url_with_query(self) -> None:
        req = self.schema(pr_url="https://github.com/a/b/pull/1?diff=unified")
        self.assertEqual(req.pr_url, "https://github.com/a/b/pull/1")

    def test_valid_language_en(self) -> None:
        req = self.schema(pr_url="https://github.com/a/b/pull/1", language="en")
        self.assertEqual(req.language, "en")

    def test_invalid_url_raises(self) -> None:
        with self.assertRaises(InvalidPRUrlError):
            self.schema(pr_url="not-a-url")

    def test_invalid_language_raises(self) -> None:
        with self.assertRaises(Exception):
            self.schema(pr_url="https://github.com/a/b/pull/1", language="fr")


class TestReviewResponseSchema(unittest.TestCase):
    """``ReviewResponse`` construction."""

    def setUp(self) -> None:
        from app.schemas.review_request import ReviewResponse
        self.schema = ReviewResponse

    def test_basic_response(self) -> None:
        resp = self.schema(
            pr_url="https://github.com/a/b/pull/1",
            owner="a",
            repo="b",
            pull_number=1,
            pr_title="Test PR",
            report="## 📋 PR Summary\n\nTest report.",
        )
        self.assertEqual(resp.owner, "a")
        self.assertEqual(resp.pull_number, 1)
        self.assertIn("PR Summary", resp.report)
        self.assertEqual(resp.input_tokens, 0)


# ===========================================================================
# Integration test with mocked services
# ===========================================================================

class TestReviewEndpoint(unittest.TestCase):
    """``POST /api/v1/review`` with mocked GitHub and LLM."""

    def setUp(self) -> None:
        # FastAPI TestClient
        from app.main import app
        from fastapi.testclient import TestClient
        self.client = TestClient(app)

        # Sample PR metadata
        self.sample_meta = MagicMock()
        self.sample_meta.title = "Fix login redirect"
        self.sample_meta.author = "octocat"
        self.sample_meta.base_branch = "main"
        self.sample_meta.head_branch = "feat/fix"
        self.sample_meta.changed_files = 2
        self.sample_meta.additions = 50
        self.sample_meta.deletions = 10

        # Sample file diffs
        self.sample_diff = [
            MagicMock(
                filename="src/auth.py",
                status="modified",
                additions=30,
                deletions=5,
                patch="@@ -1,3 +1,8 @@\n+import os\n+def login():",
            ),
        ]

        # Sample LLM result
        self.sample_report = (
            "## 📋 PR Summary\n\n"
            "Clean fix for login redirect.\n\n"
            "## 🔧 Changed Modules\n\n"
            "- `src/auth.py`\n\n"
            "## 🐛 Bug Suggestions\n\n"
            "None identified.\n"
        )

        self.sample_llm_result = MagicMock()
        self.sample_llm_result.raw_markdown = self.sample_report
        self.sample_llm_result.summary = "Clean fix for login redirect."
        self.sample_llm_result.changed_modules = "- `src/auth.py`"
        self.sample_llm_result.potential_risks = ""
        self.sample_llm_result.bug_suggestions = "None identified."
        self.sample_llm_result.performance_suggestions = ""
        self.sample_llm_result.security_suggestions = ""
        self.sample_llm_result.input_tokens = 450
        self.sample_llm_result.output_tokens = 180
        self.sample_llm_result.total_tokens = 630
        self.sample_llm_result.model = "deepseek-chat"
        self.sample_llm_result.error = None

    def _override_deps(
        self,
        github_mock=None,
        llm_mock=None,
    ) -> None:
        """Override FastAPI dependencies with mocks.

        The override key must match the exact callable passed to ``Depends()``
        in the route definition — class for ``Depends(GitHubService)``,
        function for ``Depends(get_llm_service)``.
        """
        from app.main import app
        from app.services.github import GitHubService
        from app.services.llm.factory import get_llm_service

        if github_mock:
            app.dependency_overrides[GitHubService] = lambda: github_mock
        if llm_mock:
            app.dependency_overrides[get_llm_service] = lambda: llm_mock

    def tearDown(self) -> None:
        from app.main import app
        app.dependency_overrides.clear()

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_review_success(self) -> None:
        """A valid PR URL should return a complete review report."""
        github = MagicMock()
        github.fetch_pr_metadata = AsyncMock(return_value=self.sample_meta)
        github.fetch_pr_diff = AsyncMock(return_value=self.sample_diff)

        llm = MagicMock()
        llm.review_pr = AsyncMock(return_value=self.sample_llm_result)
        llm.close = AsyncMock()

        self._override_deps(github_mock=github, llm_mock=llm)

        resp = self.client.post(
            "/api/v1/review",
            json={"pr_url": "https://github.com/octocat/Hello-World/pull/1"},
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["owner"], "octocat")
        self.assertEqual(data["repo"], "Hello-World")
        self.assertEqual(data["pull_number"], 1)
        self.assertEqual(data["pr_title"], "Fix login redirect")
        self.assertIn("PR Summary", data["report"])
        self.assertEqual(data["input_tokens"], 450)
        self.assertEqual(data["output_tokens"], 180)
        self.assertEqual(data["model"], "deepseek-chat")

    def test_review_success_with_language_en(self) -> None:
        """Language parameter should be passed through."""
        github = MagicMock()
        github.fetch_pr_metadata = AsyncMock(return_value=self.sample_meta)
        github.fetch_pr_diff = AsyncMock(return_value=self.sample_diff)

        llm = MagicMock()
        llm.review_pr = AsyncMock(return_value=self.sample_llm_result)
        llm.close = AsyncMock()

        self._override_deps(github_mock=github, llm_mock=llm)

        resp = self.client.post(
            "/api/v1/review",
            json={
                "pr_url": "https://github.com/octocat/Hello-World/pull/1",
                "language": "en",
            },
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["model"], "deepseek-chat")

    # ------------------------------------------------------------------
    # Error paths
    # ------------------------------------------------------------------

    def test_invalid_url_returns_422(self) -> None:
        """An invalid PR URL should return 422."""
        resp = self.client.post(
            "/api/v1/review",
            json={"pr_url": "not-a-url"},
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("Invalid", resp.text)

    def test_pr_not_found_returns_404(self) -> None:
        """A non-existent PR should return 404."""
        github = MagicMock()
        github.fetch_pr_metadata = AsyncMock(
            side_effect=PRNotFoundError("PR not found")
        )

        llm = MagicMock()
        llm.close = AsyncMock()

        self._override_deps(github_mock=github, llm_mock=llm)

        resp = self.client.post(
            "/api/v1/review",
            json={"pr_url": "https://github.com/owner/repo/pull/999"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_github_api_error_returns_502(self) -> None:
        """A GitHub API failure should return 502."""
        from app.core.exceptions import GitHubAPIError

        github = MagicMock()
        github.fetch_pr_metadata = AsyncMock(
            side_effect=GitHubAPIError("API rate limited")
        )

        llm = MagicMock()
        llm.close = AsyncMock()

        self._override_deps(github_mock=github, llm_mock=llm)

        resp = self.client.post(
            "/api/v1/review",
            json={"pr_url": "https://github.com/owner/repo/pull/1"},
        )
        self.assertEqual(resp.status_code, 502)

    def test_llm_error_returns_502(self) -> None:
        """An LLM failure should return 502."""
        github = MagicMock()
        github.fetch_pr_metadata = AsyncMock(return_value=self.sample_meta)
        github.fetch_pr_diff = AsyncMock(return_value=self.sample_diff)

        llm = MagicMock()
        llm.review_pr = AsyncMock(
            side_effect=Exception("LLM API connection failed")
        )
        llm.close = AsyncMock()

        self._override_deps(github_mock=github, llm_mock=llm)

        resp = self.client.post(
            "/api/v1/review",
            json={"pr_url": "https://github.com/owner/repo/pull/1"},
        )
        self.assertEqual(resp.status_code, 502)
        self.assertIn("LLM", resp.text)

    def test_llm_returns_error_field(self) -> None:
        """If the LLM returns an error in the response, should return 502."""
        github = MagicMock()
        github.fetch_pr_metadata = AsyncMock(return_value=self.sample_meta)
        github.fetch_pr_diff = AsyncMock(return_value=self.sample_diff)

        error_result = MagicMock()
        error_result.raw_markdown = ""
        error_result.error = "ProviderAuthError: invalid API key"
        error_result.input_tokens = 0
        error_result.output_tokens = 0
        error_result.total_tokens = 0
        error_result.model = ""
        error_result.is_complete = False

        llm = MagicMock()
        llm.review_pr = AsyncMock(return_value=error_result)
        llm.close = AsyncMock()

        self._override_deps(github_mock=github, llm_mock=llm)

        resp = self.client.post(
            "/api/v1/review",
            json={"pr_url": "https://github.com/owner/repo/pull/1"},
        )
        self.assertEqual(resp.status_code, 502)
        self.assertIn("API key", resp.text)

    # ------------------------------------------------------------------
    # Raw Markdown endpoint
    # ------------------------------------------------------------------

    def test_review_raw_returns_markdown(self) -> None:
        """``POST /review/raw`` should return raw Markdown."""
        github = MagicMock()
        github.fetch_pr_metadata = AsyncMock(return_value=self.sample_meta)
        github.fetch_pr_diff = AsyncMock(return_value=self.sample_diff)

        llm = MagicMock()
        llm.review_pr = AsyncMock(return_value=self.sample_llm_result)
        llm.close = AsyncMock()

        self._override_deps(github_mock=github, llm_mock=llm)

        resp = self.client.post(
            "/api/v1/review/raw",
            json={"pr_url": "https://github.com/octocat/Hello-World/pull/1"},
        )

        self.assertEqual(resp.status_code, 200)
        self.assertIn("PR Summary", resp.text)
        self.assertIn("text/markdown", resp.headers.get("content-type", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
