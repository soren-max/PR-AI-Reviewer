"""
Tests for the synchronous ``POST /api/v1/review`` endpoint.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.core.exceptions import InvalidPRUrlError, PRNotFoundError
from app.main import app


@pytest.fixture
def sample_meta() -> MagicMock:
    meta = MagicMock()
    meta.title = "Fix login redirect"
    meta.description = "Fixes redirect validation after OAuth login."
    meta.author = "octocat"
    meta.base_branch = "main"
    meta.head_branch = "feat/fix"
    meta.changed_files = 2
    meta.additions = 50
    meta.deletions = 10
    return meta


@pytest.fixture
def sample_diff() -> list[MagicMock]:
    return [
        MagicMock(
            filename="src/auth.py",
            status="modified",
            additions=30,
            deletions=5,
            patch="@@ -1,3 +1,8 @@\n+import os\n+def login():",
        ),
    ]


@pytest.fixture
def sample_llm_result() -> MagicMock:
    result = MagicMock()
    result.raw_markdown = (
        '{"overall_score":92,'
        '"summary":{"overview":"Clean fix for login redirect.",'
        '"total_issues":0,"critical_count":0,"major_count":0,'
        '"minor_count":0,"info_count":0},'
        '"changed_modules":["src/auth.py — updated login redirect"],'
        '"issues":[]}'
    )
    result.summary = "Clean fix for login redirect."
    result.changed_modules = "- `src/auth.py`"
    result.potential_risks = ""
    result.bug_suggestions = "None identified."
    result.performance_suggestions = ""
    result.security_suggestions = ""
    result.input_tokens = 450
    result.output_tokens = 180
    result.total_tokens = 630
    result.model = "deepseek-chat"
    result.error = None
    return result


def override_review_service(github_mock=None, llm_mock=None) -> None:
    from app.api.v1.review import get_review_service
    from app.services.review import ReviewService

    service = ReviewService(github=github_mock, llm=llm_mock)
    app.dependency_overrides[get_review_service] = lambda: service


class TestReviewRequestSchema:
    def test_valid_url(self) -> None:
        from app.schemas.review_request import ReviewRequest

        req = ReviewRequest(pr_url="https://github.com/owner/repo/pull/42")
        assert req.pr_url == "https://github.com/owner/repo/pull/42"
        assert req.language == "zh"

    def test_valid_url_trailing_slash(self) -> None:
        from app.schemas.review_request import ReviewRequest

        req = ReviewRequest(pr_url="https://github.com/a/b/pull/1/")
        assert req.pr_url == "https://github.com/a/b/pull/1/"

    def test_valid_url_with_query(self) -> None:
        from app.schemas.review_request import ReviewRequest

        req = ReviewRequest(pr_url="https://github.com/a/b/pull/1?diff=unified")
        assert req.pr_url == "https://github.com/a/b/pull/1"

    def test_valid_language_en(self) -> None:
        from app.schemas.review_request import ReviewRequest

        req = ReviewRequest(pr_url="https://github.com/a/b/pull/1", language="en")
        assert req.language == "en"

    def test_invalid_url_raises(self) -> None:
        from app.schemas.review_request import ReviewRequest

        with pytest.raises(InvalidPRUrlError):
            ReviewRequest(pr_url="not-a-url")

    def test_invalid_language_raises(self) -> None:
        from pydantic import ValidationError
        from app.schemas.review_request import ReviewRequest

        with pytest.raises(ValidationError):
            ReviewRequest(pr_url="https://github.com/a/b/pull/1", language="fr")


class TestReviewResponseSchema:
    def test_basic_response(self) -> None:
        from app.schemas.review_request import ReviewResponse

        resp = ReviewResponse(
            pr_url="https://github.com/a/b/pull/1",
            owner="a",
            repo="b",
            pull_number=1,
            pr_title="Test PR",
            report="## 📋 Review Summary\n\nTest report.",
        )
        assert resp.owner == "a"
        assert resp.pull_number == 1
        assert "Review Summary" in resp.report
        assert resp.input_tokens == 0


class TestReviewEndpoint:
    async def test_review_success(
        self,
        async_client: AsyncClient,
        sample_meta: MagicMock,
        sample_diff: list[MagicMock],
        sample_llm_result: MagicMock,
    ) -> None:
        github = MagicMock()
        github.fetch_pr_metadata = AsyncMock(return_value=sample_meta)
        github.fetch_pr_diff = AsyncMock(return_value=sample_diff)

        llm = MagicMock()
        llm.review_pr = AsyncMock(return_value=sample_llm_result)
        llm.close = AsyncMock()

        override_review_service(github_mock=github, llm_mock=llm)

        resp = await async_client.post(
            "/api/v1/review",
            json={"pr_url": "https://github.com/octocat/Hello-World/pull/1"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["owner"] == "octocat"
        assert data["repo"] == "Hello-World"
        assert data["pull_number"] == 1
        assert data["pr_title"] == "Fix login redirect"
        assert "Review Summary" in data["report"]
        assert "Clean fix for login redirect" in data["report"]
        assert data["input_tokens"] == 450
        assert data["output_tokens"] == 180
        assert data["model"] == "deepseek-chat"

    async def test_review_success_with_language_en(
        self,
        async_client: AsyncClient,
        sample_meta: MagicMock,
        sample_diff: list[MagicMock],
        sample_llm_result: MagicMock,
    ) -> None:
        github = MagicMock()
        github.fetch_pr_metadata = AsyncMock(return_value=sample_meta)
        github.fetch_pr_diff = AsyncMock(return_value=sample_diff)

        llm = MagicMock()
        llm.review_pr = AsyncMock(return_value=sample_llm_result)
        llm.close = AsyncMock()

        override_review_service(github_mock=github, llm_mock=llm)

        resp = await async_client.post(
            "/api/v1/review",
            json={
                "pr_url": "https://github.com/octocat/Hello-World/pull/1",
                "language": "en",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["model"] == "deepseek-chat"

    async def test_invalid_url_returns_422(self, async_client: AsyncClient) -> None:
        resp = await async_client.post("/api/v1/review", json={"pr_url": "not-a-url"})
        assert resp.status_code == 422
        assert "Invalid" in resp.text

    async def test_pr_not_found_returns_404(self, async_client: AsyncClient) -> None:
        github = MagicMock()
        github.fetch_pr_metadata = AsyncMock(side_effect=PRNotFoundError("PR not found"))

        llm = MagicMock()
        llm.close = AsyncMock()

        override_review_service(github_mock=github, llm_mock=llm)

        resp = await async_client.post(
            "/api/v1/review",
            json={"pr_url": "https://github.com/owner/repo/pull/999"},
        )
        assert resp.status_code == 404

    async def test_github_api_error_returns_502(self, async_client: AsyncClient) -> None:
        from app.core.exceptions import GitHubAPIError

        github = MagicMock()
        github.fetch_pr_metadata = AsyncMock(side_effect=GitHubAPIError("API rate limited"))

        llm = MagicMock()
        llm.close = AsyncMock()

        override_review_service(github_mock=github, llm_mock=llm)

        resp = await async_client.post(
            "/api/v1/review",
            json={"pr_url": "https://github.com/owner/repo/pull/1"},
        )
        assert resp.status_code == 502

    async def test_llm_error_returns_502(
        self,
        async_client: AsyncClient,
        sample_meta: MagicMock,
        sample_diff: list[MagicMock],
    ) -> None:
        github = MagicMock()
        github.fetch_pr_metadata = AsyncMock(return_value=sample_meta)
        github.fetch_pr_diff = AsyncMock(return_value=sample_diff)

        llm = MagicMock()
        llm.review_pr = AsyncMock(side_effect=Exception("LLM API connection failed"))
        llm.close = AsyncMock()

        override_review_service(github_mock=github, llm_mock=llm)

        resp = await async_client.post(
            "/api/v1/review",
            json={"pr_url": "https://github.com/owner/repo/pull/1"},
        )
        assert resp.status_code == 502
        assert "LLM" in resp.text

    async def test_llm_returns_error_field(
        self,
        async_client: AsyncClient,
        sample_meta: MagicMock,
        sample_diff: list[MagicMock],
    ) -> None:
        github = MagicMock()
        github.fetch_pr_metadata = AsyncMock(return_value=sample_meta)
        github.fetch_pr_diff = AsyncMock(return_value=sample_diff)

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

        override_review_service(github_mock=github, llm_mock=llm)

        resp = await async_client.post(
            "/api/v1/review",
            json={"pr_url": "https://github.com/owner/repo/pull/1"},
        )
        assert resp.status_code == 502
        assert "API key" in resp.text

    async def test_review_raw_returns_markdown(
        self,
        async_client: AsyncClient,
        sample_meta: MagicMock,
        sample_diff: list[MagicMock],
        sample_llm_result: MagicMock,
    ) -> None:
        github = MagicMock()
        github.fetch_pr_metadata = AsyncMock(return_value=sample_meta)
        github.fetch_pr_diff = AsyncMock(return_value=sample_diff)

        llm = MagicMock()
        llm.review_pr = AsyncMock(return_value=sample_llm_result)
        llm.close = AsyncMock()

        override_review_service(github_mock=github, llm_mock=llm)

        resp = await async_client.post(
            "/api/v1/review/raw",
            json={"pr_url": "https://github.com/octocat/Hello-World/pull/1"},
        )

        assert resp.status_code == 200
        assert "Review Summary" in resp.text
        assert "Clean fix for login redirect" in resp.text
        assert "text/markdown" in resp.headers.get("content-type", "")
