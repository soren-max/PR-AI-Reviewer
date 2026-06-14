"""
Integration tests for the review task pipeline.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.review import Review, ReviewStatus


@pytest.mark.asyncio
async def test_run_review_success(test_engine, mock_github_service, mock_llm_client):
    """Should go through all states and persist a completed review."""
    from app.tasks.review import run_review

    # Create a review in pending state
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as db:
        review = Review(
            pr_url="https://github.com/owner/repo/pull/1",
            owner="owner",
            repo="repo",
            pr_number=1,
        )
        db.add(review)
        await db.commit()
        review_id = str(review.id)

    with patch("app.tasks.review.GitHubService", return_value=mock_github_service):
        with patch("app.tasks.review.LLMClient", return_value=mock_llm_client):
            await run_review(review_id, test_engine)

    # Verify the review is now completed
    async with session_factory() as db:
        completed = await db.get(Review, review_id)
        assert completed is not None
        assert completed.status == ReviewStatus.COMPLETED
        assert completed.overall_score == 85
        assert completed.duration_ms is not None
        assert completed.completed_at is not None


@pytest.mark.asyncio
async def test_run_review_idempotent(test_engine):
    """Calling run_review twice on the same review should be a no-op."""
    from app.tasks.review import run_review
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as db:
        review = Review(
            pr_url="https://github.com/owner/repo/pull/2",
            owner="owner", repo="repo", pr_number=2,
            status=ReviewStatus.COMPLETED,
        )
        db.add(review)
        await db.commit()
        review_id = str(review.id)

    await run_review(review_id, test_engine)

    # Should not change status (no crash)
    async with session_factory() as db:
        result = await db.get(Review, review_id)
        assert result.status == ReviewStatus.COMPLETED
