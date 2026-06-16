"""
Integration tests for Review API endpoints.
"""
import pytest
from httpx import AsyncClient

from app.main import app


@pytest.fixture
def override_background_review(monkeypatch):
    """Prevent API tests from executing the real background review pipeline."""
    async def noop_run_review(review_id: str, db_engine) -> None:
        return None

    monkeypatch.setattr("app.api.v1.reviews.run_review", noop_run_review)


class TestCreateReview:
    async def test_create_review_success(
        self,
        async_client: AsyncClient,
        mock_github_service,
        override_background_review,
    ):
        """Should return 201 with review metadata."""
        from app.api.v1.reviews import GitHubService

        app.dependency_overrides[GitHubService] = lambda: mock_github_service

        payload = {"pr_url": "https://github.com/owner/repo/pull/42"}
        resp = await async_client.post("/api/v1/reviews", json=payload)

        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["pr_url"] == "https://github.com/owner/repo/pull/42"
        assert "id" in data

    async def test_create_review_invalid_url(self, async_client: AsyncClient):
        """Should return 422 for non-GitHub URLs."""
        payload = {"pr_url": "https://gitlab.com/owner/repo/issues/1"}
        resp = await async_client.post("/api/v1/reviews", json=payload)
        assert resp.status_code == 422
        data = resp.json()
        assert data["error"]["code"] == "INVALID_PR_URL"

    async def test_create_review_bad_format(self, async_client: AsyncClient):
        """Should return 422 for completely invalid URLs."""
        payload = {"pr_url": "not-a-url"}
        resp = await async_client.post("/api/v1/reviews", json=payload)
        assert resp.status_code == 422


class TestGetReview:
    async def test_get_review_not_found(self, async_client: AsyncClient):
        """Should return 404 for non-existent review."""
        resp = await async_client.get("/api/v1/reviews/non-existent-id")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "PR_NOT_FOUND"

    async def test_get_review_pending(
        self,
        async_client: AsyncClient,
        mock_github_service,
        override_background_review,
    ):
        """Should return basic info for pending review."""
        from app.api.v1.reviews import GitHubService
        app.dependency_overrides[GitHubService] = lambda: mock_github_service

        create_resp = await async_client.post(
            "/api/v1/reviews",
            json={"pr_url": "https://github.com/owner/repo/pull/42"},
        )
        review_id = create_resp.json()["id"]

        resp = await async_client.get(f"/api/v1/reviews/{review_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("pending", "fetching", "analyzing")
        assert "comments" not in data or data["comments"] == []


class TestListReviews:
    async def test_list_empty(self, async_client: AsyncClient):
        """Should return empty list when no reviews exist."""
        resp = await async_client.get("/api/v1/reviews")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_pagination(
        self,
        async_client: AsyncClient,
        mock_github_service,
        override_background_review,
    ):
        """Should respect pagination parameters."""
        from app.api.v1.reviews import GitHubService
        app.dependency_overrides[GitHubService] = lambda: mock_github_service

        # Create 3 reviews
        for i in range(3):
            await async_client.post(
                "/api/v1/reviews",
                json={"pr_url": f"https://github.com/owner/repo/pull/{i+1}"},
            )

        resp = await async_client.get("/api/v1/reviews?page=1&per_page=2")
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3
        assert data["page"] == 1

        resp = await async_client.get("/api/v1/reviews?page=2&per_page=2")
        data = resp.json()
        assert len(data["items"]) == 1


class TestHealth:
    async def test_health(self, async_client: AsyncClient):
        """Health check should return ok."""
        resp = await async_client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
