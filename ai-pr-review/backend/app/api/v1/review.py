"""
Synchronous PR review endpoint.

``POST /api/v1/review`` — accepts a GitHub PR URL, fetches the PR metadata
and diff, calls the configured LLM provider, and returns a structured
Markdown review report in a single request-response cycle.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.core.exceptions import GitHubAPIError, InvalidPRUrlError, PRNotFoundError
from app.schemas.review_request import ReviewRequest, ReviewResponse
from app.services.github import GitHubService, parse_pr_url
from app.services.llm import get_llm_service

logger = logging.getLogger("api.v1.review")

router = APIRouter(tags=["review"])


@router.post(
    "/review",
    summary="Review a Pull Request and return a Markdown report",
    response_model=ReviewResponse,
    responses={
        200: {"description": "Review completed successfully"},
        422: {"description": "Invalid PR URL"},
        404: {"description": "PR not found on GitHub"},
        502: {"description": "GitHub API or LLM API error"},
    },
)
async def review_pr(
    body: ReviewRequest,
    request: Request,
    github: GitHubService = Depends(GitHubService),
    llm: Any = Depends(get_llm_service),
) -> Any:
    """Synchronous PR review — one request, one response.

    Processing steps:
        ① Parse and validate the PR URL                   → 422
        ② Fetch PR metadata from GitHub API                → 404 / 502
        ③ Fetch unified diff from GitHub API               → 502
        ④ Call LLM with structured prompt                  → 502
        ⑤ Return structured JSON with Markdown report      → 200
    """
    request_id = getattr(request.state, "request_id", "unknown")
    start_time = time.monotonic()
    pr_url = body.pr_url

    logger.info("[%s] POST /review — pr_url=%s, language=%s", request_id, pr_url, body.language)

    # ------------------------------------------------------------------
    # Step ①: Parse PR URL
    # ------------------------------------------------------------------
    try:
        parsed = parse_pr_url(pr_url)
    except InvalidPRUrlError as exc:
        logger.warning("[%s] Invalid PR URL: %s", request_id, pr_url)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    logger.info(
        "[%s] Parsed: owner=%s, repo=%s, pr_number=%d",
        request_id, parsed.owner, parsed.repo, parsed.pr_number,
    )

    # ------------------------------------------------------------------
    # Step ②: Fetch PR metadata
    # ------------------------------------------------------------------
    try:
        pr_meta = await github.fetch_pr_metadata(
            owner=parsed.owner, repo=parsed.repo, number=parsed.pr_number,
        )
    except PRNotFoundError as exc:
        logger.warning("[%s] PR not found: %s/%s#%d", request_id, parsed.owner, parsed.repo, parsed.pr_number)
        raise HTTPException(
            status_code=404,
            detail=f"PR {parsed.owner}/{parsed.repo}#{parsed.pr_number} not found",
        ) from exc
    except GitHubAPIError as exc:
        logger.error("[%s] GitHub API error fetching PR metadata: %s", request_id, exc)
        raise HTTPException(status_code=502, detail=f"GitHub API error: {exc.message}") from exc

    logger.info(
        "[%s] PR metadata: title=%r, files=%d, +%d/-%d",
        request_id, pr_meta.title, pr_meta.changed_files,
        pr_meta.additions, pr_meta.deletions,
    )

    # ------------------------------------------------------------------
    # Step ③: Fetch PR diff
    # ------------------------------------------------------------------
    try:
        diffs = await github.fetch_pr_diff(
            owner=parsed.owner, repo=parsed.repo, number=parsed.pr_number,
        )
    except GitHubAPIError as exc:
        logger.error("[%s] GitHub API error fetching diff: %s", request_id, exc)
        raise HTTPException(status_code=502, detail=f"GitHub API error fetching diff: {exc.message}") from exc

    diff_lines: list[str] = []
    for f in diffs:
        if f.patch:
            diff_lines.append(f"diff --git a/{f.filename} b/{f.filename}")
            diff_lines.append(f"--- a/{f.filename}")
            diff_lines.append(f"+++ b/{f.filename}")
            diff_lines.append(f.patch)
            diff_lines.append("")

    diff_text = "\n".join(diff_lines)

    logger.info("[%s] Fetched %d files, diff size=%d chars", request_id, len(diffs), len(diff_text))

    # ------------------------------------------------------------------
    # Step ④: Call LLM
    # ------------------------------------------------------------------
    try:
        llm_result = await llm.review_pr(
            pr_title=pr_meta.title,
            pr_description=pr_meta.title,
            diff=diff_text,
            language=body.language,
        )
    except Exception as exc:
        logger.exception("[%s] LLM review failed", request_id)
        raise HTTPException(status_code=502, detail=f"LLM review failed: {exc}") from exc

    if llm_result.error:
        logger.error("[%s] LLM returned error: %s", request_id, llm_result.error)
        raise HTTPException(status_code=502, detail=f"LLM review error: {llm_result.error}")

    # ------------------------------------------------------------------
    # Step ⑤: Return structured response
    # ------------------------------------------------------------------
    elapsed = time.monotonic() - start_time
    logger.info(
        "[%s] Review complete in %.1fs — tokens: %d in / %d out",
        request_id, elapsed, llm_result.input_tokens, llm_result.output_tokens,
    )

    return ReviewResponse(
        pr_url=pr_url,
        owner=parsed.owner,
        repo=parsed.repo,
        pull_number=parsed.pr_number,
        pr_title=pr_meta.title,
        report=llm_result.raw_markdown,
        input_tokens=llm_result.input_tokens,
        output_tokens=llm_result.output_tokens,
        model=llm_result.model,
    )


@router.post(
    "/review/raw",
    summary="Review a PR and return raw Markdown",
    response_class=PlainTextResponse,
)
async def review_pr_raw(
    body: ReviewRequest,
    request: Request,
    github: GitHubService = Depends(GitHubService),
    llm: Any = Depends(get_llm_service),
) -> PlainTextResponse:
    """Same as ``POST /review`` but returns raw Markdown instead of JSON."""
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        parsed = parse_pr_url(body.pr_url)
    except InvalidPRUrlError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        pr_meta = await github.fetch_pr_metadata(
            owner=parsed.owner, repo=parsed.repo, number=parsed.pr_number,
        )
    except PRNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GitHubAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc.message)) from exc

    try:
        diffs = await github.fetch_pr_diff(
            owner=parsed.owner, repo=parsed.repo, number=parsed.pr_number,
        )
    except GitHubAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc.message)) from exc

    diff_text = "\n".join(
        line
        for f in diffs
        if f.patch
        for line in [
            f"diff --git a/{f.filename} b/{f.filename}",
            f"--- a/{f.filename}",
            f"+++ b/{f.filename}",
            f.patch,
            "",
        ]
    )

    try:
        llm_result = await llm.review_pr(
            pr_title=pr_meta.title,
            pr_description=pr_meta.title,
            diff=diff_text,
            language=body.language,
        )
    except Exception as exc:
        logger.exception("[%s] LLM review failed", request_id)
        raise HTTPException(status_code=502, detail=f"LLM review failed: {exc}") from exc

    if llm_result.error:
        raise HTTPException(status_code=502, detail=llm_result.error)

    return PlainTextResponse(
        content=llm_result.raw_markdown,
        media_type="text/markdown",
        headers={
            "X-Review-Model": llm_result.model,
            "X-Review-Tokens": str(llm_result.total_tokens),
        },
    )
