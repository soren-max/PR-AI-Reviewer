"""
Synchronous PR review endpoint.

``POST /api/v1/review`` — Clean Architecture orchestration.
"""
from __future__ import annotations

import logging
import time
import inspect
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.core.exceptions import GitHubAPIError, InvalidPRUrlError, PRNotFoundError
from app.schemas.review_request import ReviewMetricsResponse, ReviewRequest, ReviewResponse
from app.services.github import GitHubService, parse_pr_url
from app.services.llm.base import BaseLLMService
from app.services.llm.factory import get_llm_service
from app.services.review import ReviewService, ReviewInput

logger = logging.getLogger("api.v1.review")

router = APIRouter(tags=["review"])


def get_llm_dependency() -> BaseLLMService:
    """Return the configured LLM service through a FastAPI-safe dependency."""
    return get_llm_service()


async def get_review_service(
    github: GitHubService = Depends(GitHubService),
    llm: BaseLLMService = Depends(get_llm_dependency),
):
    """Build the review orchestrator from injectable external services."""
    try:
        yield ReviewService(github=github, llm=llm)
    finally:
        await _close_if_async(llm)
        await _close_if_async(github)


async def _close_if_async(service: Any) -> None:
    close = getattr(service, "close", None)
    if close is None:
        return
    result = close()
    if inspect.isawaitable(result):
        await result


@router.post(
    "/review",
    summary="Review a Pull Request",
    response_model=ReviewResponse,
    responses={200: {}, 422: {}, 404: {}, 502: {}},
)
async def review_pr(
    body: ReviewRequest,
    request: Request,
    service: ReviewService = Depends(get_review_service),
) -> Any:
    """Synchronous PR review — one request, one response."""
    request_id = getattr(request.state, "request_id", "unknown")
    start_time = time.monotonic()
    pr_url = body.pr_url

    logger.info("[%s] POST /review — pr_url=%s", request_id, pr_url)

    # ---------- Step 1: Parse URL ----------
    try:
        parse_pr_url(pr_url)
    except InvalidPRUrlError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        result = await service.review(ReviewInput(
            pr_url=pr_url,
            language=body.language,
        ))
    except PRNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GitHubAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc.message)) from exc
    except Exception as exc:
        logger.exception("[%s] Review failed", request_id)
        raise HTTPException(status_code=502, detail=f"Review failed: {exc}") from exc

    if result.error:
        raise HTTPException(status_code=502, detail=result.error)

    elapsed = int((time.monotonic() - start_time) * 1000)
    logger.info(
        "[%s] Review complete in %dms — %s",
        request_id, elapsed, result.diff_summary,
    )

    return ReviewResponse(
        pr_url=pr_url,
        owner=result.owner,
        repo=result.repo,
        pull_number=result.pull_number,
        pr_title=result.pr_title,
        report=result.report.to_markdown(),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        model=result.model,
        metrics=ReviewMetricsResponse(**(result.metrics.to_dict() if result.metrics else {})),
    )


@router.post(
    "/review/raw",
    summary="Review a PR and return raw Markdown",
    response_class=PlainTextResponse,
)
async def review_pr_raw(
    body: ReviewRequest,
    request: Request,
    service: ReviewService = Depends(get_review_service),
) -> PlainTextResponse:
    """Same as POST /review but returns raw Markdown."""
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        parse_pr_url(body.pr_url)
    except InvalidPRUrlError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        result = await service.review(ReviewInput(
            pr_url=body.pr_url,
            language=body.language,
        ))
    except PRNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GitHubAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc.message)) from exc
    except Exception as exc:
        logger.exception("[%s] Review failed", request_id)
        raise HTTPException(status_code=502, detail=f"Review failed: {exc}") from exc

    if result.error:
        raise HTTPException(status_code=502, detail=result.error)

    return PlainTextResponse(
        content=result.report.to_markdown(),
        media_type="text/markdown",
        headers={
            "X-Review-Model": result.model,
            "X-Review-Tokens": str(result.input_tokens + result.output_tokens),
            "X-Review-Time-Ms": str(result.duration_ms),
        },
    )
