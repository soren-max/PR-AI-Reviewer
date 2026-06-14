"""
Review CRUD endpoints.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import PRNotFoundError
from app.models.review import Review
from app.schemas.common import PaginatedResponse
from app.schemas.review import (
    CreateReviewReq,
    ReviewDetailResp,
    ReviewListResp,
    ReviewResp,
)
from app.services.github import GitHubService, parse_pr_url
from app.tasks.review import run_review

router = APIRouter()


@router.post(
    "/reviews",
    status_code=201,
    response_model=ReviewResp,
    summary="Submit a new PR review request",
)
async def create_review(
    body: CreateReviewReq,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    github: GitHubService = Depends(GitHubService),
):
    """
    Accept a GitHub Pull Request URL, parse it, create a review record,
    and kick off background analysis.
    """
    parsed = parse_pr_url(body.pr_url)

    # Verify the PR exists on GitHub
    await github.verify_pr_exists(
        owner=parsed.owner,
        repo=parsed.repo,
        number=parsed.pr_number,
    )

    review = Review(
        pr_url=body.pr_url,
        owner=parsed.owner,
        repo=parsed.repo,
        pr_number=parsed.pr_number,
        focus_areas=body.options.focus_areas if body.options else None,
        language=body.options.language if body.options else "zh",
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    background_tasks.add_task(run_review, str(review.id), db.bind)

    return ReviewResp(
        id=str(review.id),
        pr_url=review.pr_url,
        status=review.status.value,
        created_at=review.created_at.isoformat(),
    )


@router.get(
    "/reviews/{review_id}",
    response_model=ReviewDetailResp,
    summary="Get review details with comments",
)
async def get_review(
    review_id: str,
    db: AsyncSession = Depends(get_db),
):
    review = await Review.get_by_id(db, review_id)
    if not review:
        raise PRNotFoundError(f"Review {review_id} not found")
    return ReviewDetailResp.from_orm(review)


@router.get(
    "/reviews",
    response_model=PaginatedResponse[ReviewListResp],
    summary="List all reviews with pagination",
)
async def list_reviews(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
):
    items, total = await Review.list_paginated(
        db, page=page, per_page=per_page, status=status
    )
    return PaginatedResponse(
        items=[ReviewListResp.from_orm(r) for r in items],
        total=total,
        page=page,
        per_page=per_page,
    )
