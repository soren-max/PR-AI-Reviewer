"""
Tests for the review service — ``POST /api/v1/review`` endpoint and
LLM service integration.

All external services (GitHub API, DeepSeek API) are mocked via ``@patch``.
No real network requests are made.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github_url import parse_pr_url, InvalidGitHubURLError


# ===========================================================================
# Schema tests (no mocking)
# ===========================================================================


class TestReviewRequestSchema:
    def test_valid_request(self) -> None:
        from app.schemas.review_request import ReviewRequest
        req = ReviewRequest(pr_url="https://github.com/owner/repo/pull/42")
        assert req.pr_url is not None
        assert req.language == "zh"

    def test_valid_url_with_query(self) -> None:
        from app.schemas.review_request import ReviewRequest
        req = ReviewRequest(pr_url="https://github.com/a/b/pull/1?diff=unified")
        assert req.pr_url is not None

    def test_valid_language_en(self) -> None:
        from app.schemas.review_request import ReviewRequest
        req = ReviewRequest(pr_url="https://github.com/a/b/pull/1", language="en")
        assert req.language == "en"

    def test_invalid_url_raises(self) -> None:
        from app.schemas.review_request import ReviewRequest
        from app.core.exceptions import InvalidPRUrlError
        with pytest.raises(InvalidPRUrlError):
            ReviewRequest(pr_url="not-a-url")

    def test_invalid_language_raises(self) -> None:
        from pydantic import ValidationError
        from app.schemas.review_request import ReviewRequest
        with pytest.raises(ValidationError):
            ReviewRequest(pr_url="https://github.com/a/b/pull/1", language="fr")


class TestReviewResponseSchema:
    def test_build_response(self) -> None:
        from app.schemas.review_request import ReviewResponse
        resp = ReviewResponse(
            pr_url="https://github.com/a/b/pull/1",
            owner="a", repo="b", pull_number=1,
            pr_title="Test", report="## 📋 PR Summary\n\nReview.",
        )
        assert resp.owner == "a"
        assert resp.pull_number == 1
        assert "PR Summary" in resp.report
        assert resp.model == ""


# ===========================================================================
# FastAPI endpoint tests — all dependencies mocked with @patch
# ===========================================================================


class TestReviewEndpoint:
    """Tests ``POST /api/v1/review`` with @patch on GitHub + LLM services."""

    @pytest.fixture
    def client(self):
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    @pytest.fixture
    def mock_fetch_pr(self):
        """Mock GitHubService.fetch_pr_metadata returns a sample PR."""
        async def _fake(owner, repo, number):
            from app.services.github import PRMetadata
            return PRMetadata(
                title="Fix login redirect",
                author="octocat",
                base_branch="main",
                head_branch="feat/fix",
                changed_files=2,
                additions=50,
                deletions=10,
            )
        return _fake

    @pytest.fixture
    def mock_fetch_diff(self):
        """Mock GitHubService.fetch_pr_diff returns a sample diff list."""
        async def _fake(owner, repo, number):
            from app.services.github import FileDiff
            return [
                FileDiff(
                    filename="src/auth.py",
                    status="modified",
                    additions=30,
                    deletions=5,
                    patch="@@ -1,3 +1,8 @@\n+import os",
                ),
            ]
        return _fake

    # ------------------------------------------------------------------
    # Happy path — mock both GitHub and LLM via @patch
    # ------------------------------------------------------------------

    @patch("app.services.github.GitHubService.fetch_pr_metadata")
    @patch("app.services.github.GitHubService.fetch_pr_diff")
    @patch("app.services.llm.deepseek.DeepSeekService.review_pr")
    def test_review_success(
        self,
        mock_llm: AsyncMock,
        mock_diff: AsyncMock,
        mock_pr: AsyncMock,
        client,
        mock_fetch_pr,
        mock_fetch_diff,
    ) -> None:
        """@patch on 3 external calls → 200 + structured JSON response."""
        mock_pr.side_effect = mock_fetch_pr
        mock_diff.side_effect = mock_fetch_diff
        mock_llm.return_value = MagicMock(
            raw_markdown="## 📋 PR Summary\n\nClean fix.\n\n"
                         "## 🔧 Changed Modules\n\n- `src/auth.py`",
            summary="Clean fix.",
            changed_modules="- `src/auth.py`",
            potential_risks="",
            bug_suggestions="None identified.",
            performance_suggestions="",
            security_suggestions="",
            input_tokens=450,
            output_tokens=180,
            total_tokens=630,
            model="deepseek-chat",
            error=None,
        )

        resp = client.post(
            "/api/v1/review",
            json={"pr_url": "https://github.com/octocat/Hello-World/pull/1"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["owner"] == "octocat"
        assert data["repo"] == "Hello-World"
        assert data["pull_number"] == 1
        assert data["pr_title"] == "Fix login redirect"
        assert "PR Summary" in data["report"]
        assert data["input_tokens"] == 450
        assert data["output_tokens"] == 180
        assert data["model"] == "deepseek-chat"

    @patch("app.services.github.GitHubService.fetch_pr_metadata")
    @patch("app.services.github.GitHubService.fetch_pr_diff")
    @patch("app.services.llm.deepseek.DeepSeekService.review_pr")
    def test_review_with_language_en(
        self,
        mock_llm: AsyncMock,
        mock_diff: AsyncMock,
        mock_pr: AsyncMock,
        client,
        mock_fetch_pr,
        mock_fetch_diff,
    ) -> None:
        mock_pr.side_effect = mock_fetch_pr
        mock_diff.side_effect = mock_fetch_diff
        mock_llm.return_value = MagicMock(
            raw_markdown="## 📋 PR Summary\n\nClean fix.",
            summary="Clean fix.",
            changed_modules="",
            potential_risks="",
            bug_suggestions="",
            performance_suggestions="",
            security_suggestions="",
            input_tokens=400,
            output_tokens=150,
            total_tokens=550,
            model="deepseek-chat",
            error=None,
        )

        resp = client.post(
            "/api/v1/review",
            json={
                "pr_url": "https://github.com/octocat/Hello-World/pull/1",
                "language": "en",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["model"] == "deepseek-chat"

    # ------------------------------------------------------------------
    # Error path: invalid URL — no mocking needed
    # ------------------------------------------------------------------

    def test_invalid_url_returns_422(self, client) -> None:
        resp = client.post("/api/v1/review", json={"pr_url": "not-a-url"})
        assert resp.status_code == 422

    # ------------------------------------------------------------------
    # Error path: PR not found — @patch GitHubService
    # ------------------------------------------------------------------

    @patch("app.services.github.GitHubService.fetch_pr_metadata")
    def test_pr_not_found_returns_404(
        self,
        mock_pr: AsyncMock,
        client,
    ) -> None:
        from app.core.exceptions import PRNotFoundError
        mock_pr.side_effect = PRNotFoundError("PR not found")

        resp = client.post(
            "/api/v1/review",
            json={"pr_url": "https://github.com/owner/repo/pull/999"},
        )
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # Error path: GitHub API error — @patch GitHubService
    # ------------------------------------------------------------------

    @patch("app.services.github.GitHubService.fetch_pr_metadata")
    def test_github_error_returns_502(
        self,
        mock_pr: AsyncMock,
        client,
    ) -> None:
        from app.core.exceptions import GitHubAPIError
        mock_pr.side_effect = GitHubAPIError("API rate limited")

        resp = client.post(
            "/api/v1/review",
            json={"pr_url": "https://github.com/owner/repo/pull/1"},
        )
        assert resp.status_code == 502

    # ------------------------------------------------------------------
    # Error path: LLM exception — @patch LLM
    # ------------------------------------------------------------------

    @patch("app.services.github.GitHubService.fetch_pr_metadata")
    @patch("app.services.github.GitHubService.fetch_pr_diff")
    @patch("app.services.llm.deepseek.DeepSeekService.review_pr")
    def test_llm_exception_returns_502(
        self,
        mock_llm: AsyncMock,
        mock_diff: AsyncMock,
        mock_pr: AsyncMock,
        client,
        mock_fetch_pr,
        mock_fetch_diff,
    ) -> None:
        mock_pr.side_effect = mock_fetch_pr
        mock_diff.side_effect = mock_fetch_diff
        mock_llm.side_effect = Exception("LLM connection failed")

        resp = client.post(
            "/api/v1/review",
            json={"pr_url": "https://github.com/owner/repo/pull/1"},
        )
        assert resp.status_code == 502
        assert "LLM" in resp.text

    # ------------------------------------------------------------------
    # Error path: LLM returns error field — @patch LLM
    # ------------------------------------------------------------------

    @patch("app.services.github.GitHubService.fetch_pr_metadata")
    @patch("app.services.github.GitHubService.fetch_pr_diff")
    @patch("app.services.llm.deepseek.DeepSeekService.review_pr")
    def test_llm_error_field_returns_502(
        self,
        mock_llm: AsyncMock,
        mock_diff: AsyncMock,
        mock_pr: AsyncMock,
        client,
        mock_fetch_pr,
        mock_fetch_diff,
    ) -> None:
        mock_pr.side_effect = mock_fetch_pr
        mock_diff.side_effect = mock_fetch_diff
        mock_llm.return_value = MagicMock(
            raw_markdown="", error="ProviderAuthError: invalid API key",
            input_tokens=0, output_tokens=0, total_tokens=0,
            model="", is_complete=False,
        )

        resp = client.post(
            "/api/v1/review",
            json={"pr_url": "https://github.com/owner/repo/pull/1"},
        )
        assert resp.status_code == 502
        assert "API key" in resp.text

    # ------------------------------------------------------------------
    # Raw Markdown endpoint
    # ------------------------------------------------------------------

    @patch("app.services.github.GitHubService.fetch_pr_metadata")
    @patch("app.services.github.GitHubService.fetch_pr_diff")
    @patch("app.services.llm.deepseek.DeepSeekService.review_pr")
    def test_review_raw_endpoint(
        self,
        mock_llm: AsyncMock,
        mock_diff: AsyncMock,
        mock_pr: AsyncMock,
        client,
        mock_fetch_pr,
        mock_fetch_diff,
    ) -> None:
        mock_pr.side_effect = mock_fetch_pr
        mock_diff.side_effect = mock_fetch_diff
        mock_llm.return_value = MagicMock(
            raw_markdown="## 📋 PR Summary\n\nClean fix.",
            summary="Clean fix.",
            changed_modules="",
            potential_risks="",
            bug_suggestions="",
            performance_suggestions="",
            security_suggestions="",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            model="deepseek-chat",
            error=None,
        )

        resp = client.post(
            "/api/v1/review/raw",
            json={"pr_url": "https://github.com/octocat/Hello-World/pull/1"},
        )

        assert resp.status_code == 200
        assert "PR Summary" in resp.text
        assert "text/markdown" in resp.headers.get("content-type", "")


# ===========================================================================
# LLM Service layer tests (@patch on httpx.AsyncClient.post)
# ===========================================================================


class TestLLMDeepSeek:
    """DeepSeekService tests — all HTTP mocked via @patch."""

    @patch("httpx.AsyncClient.post")
    def test_review_pr_success(self, mock_post: AsyncMock) -> None:
        from app.services.llm.deepseek import DeepSeekService

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "choices": [{"message": {"content": "## 📋 PR Summary\n\nTest review."}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        })

        async def async_mock(*args, **kwargs):
            return mock_response
        mock_post.side_effect = async_mock

        import asyncio
        service = DeepSeekService(api_key="sk-test", max_retries=0)
        result = asyncio.run(
            service.review_pr("Test", "Description", "diff --git a/a.py")
        )

        assert "PR Summary" in result.raw_markdown
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.error is None

    @patch("httpx.AsyncClient.post")
    def test_chat_completion_retry_then_success(
        self, mock_post: AsyncMock
    ) -> None:
        """@patch: 503 → retry → 200 succeeds."""
        from app.services.llm.deepseek import DeepSeekService

        call_count = 0

        async def async_mock(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                resp = MagicMock()
                resp.status_code = 503
                return resp
            resp = MagicMock()
            resp.status_code = 200
            resp.json = MagicMock(return_value={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            })
            return resp

        mock_post.side_effect = async_mock

        import asyncio
        with patch("time.sleep"):
            service = DeepSeekService(api_key="sk-test", max_retries=2)
            content, inp, out = asyncio.run(
                service.chat_completion("system", "user")
            )

        assert content == "ok"
        assert call_count == 2


class TestLLMFactory:
    def test_get_deepseek(self) -> None:
        from app.services.llm import get_llm_service
        from app.core.config import LLMProvider
        svc = get_llm_service(LLMProvider.DEEPSEEK)
        assert svc.provider_name == "deepseek"

    def test_get_openai(self) -> None:
        from app.services.llm import get_llm_service
        from app.core.config import LLMProvider
        svc = get_llm_service(LLMProvider.OPENAI, api_key="sk-test")
        assert svc.provider_name == "openai"

    def test_get_qwen(self) -> None:
        from app.services.llm import get_llm_service
        from app.core.config import LLMProvider
        svc = get_llm_service(LLMProvider.QWEN, api_key="sk-test")
        assert svc.provider_name == "qwen"

    def test_provider_names(self) -> None:
        from app.services.llm import get_provider_names
        names = get_provider_names()
        assert "deepseek" in names
        assert "openai" in names
        assert "qwen" in names


class TestPromptBuilder:
    def test_basic_prompt(self) -> None:
        from app.services.llm.prompts import build_review_prompt
        system, user = build_review_prompt(
            "Fix login bug", "Fixed OAuth", "diff --git a/a.py", language="en",
        )
        assert isinstance(system, str)
        assert len(system) > 50
        assert "Fix login bug" in user
        assert "diff --git" in user

    def test_diff_truncation(self) -> None:
        from app.services.llm.prompts import build_review_prompt
        large = "x" * 600_000
        system, user = build_review_prompt("Large", "", large)
        assert len(user) < 600_000 + 500
        assert "truncated" in user


# ===========================================================================
# GitHub URL parser quick sanity
# ===========================================================================


class TestGithubURLSmoke:
    def test_parse_success(self) -> None:
        result = parse_pr_url("https://github.com/langchain-ai/langgraph/pull/123")
        assert result.owner == "langchain-ai"
        assert result.repo == "langgraph"
        assert result.pull_number == 123

    def test_parse_invalid(self) -> None:
        with pytest.raises(InvalidGitHubURLError):
            parse_pr_url("not-a-url")
