"""
Asynchronous PR review orchestration task.
"""
import time
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.exceptions import (
    GitHubAPIError,
    LLMAPIError,
    ReportParseError,
)
from app.core.logging import setup_logging
from app.models.review import FileStatus, Review, ReviewComment, ReviewFile, ReviewStatus
from app.services.analyzer import build_system_prompt, build_user_prompt
from app.services.github import GitHubService
from app.services.llm import LLMClient
from app.services.report import ReportGenerator

logger = setup_logging(__name__)


async def run_review(review_id: str, db_engine: AsyncEngine) -> None:
    """
    Execute the full PR review pipeline.

    This function is dispatched as a FastAPI BackgroundTask:
    1. Fetch PR metadata + diff from GitHub
    2. Build LLM prompt
    3. Call DeepSeek V4 Pro
    4. Parse response into structured report
    5. Persist results

    Args:
        review_id: UUID of the Review record.
        db_engine: SQLAlchemy async engine (passed because BackgroundTasks
                   don't have access to the request session).
    """
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    start_ts = time.monotonic()

    async with session_factory() as db:
        review = await db.get(Review, review_id)
        if not review:
            logger.error("Review %s not found in database", review_id)
            return

        # Idempotency: skip if already done
        if review.status in (ReviewStatus.COMPLETED, ReviewStatus.FAILED):
            logger.warning("Review %s already in terminal state (%s)", review_id, review.status.value)
            return

        try:
            # ------------------------------------------------------------------
            # Step 1: Fetch PR metadata + diff from GitHub
            # ------------------------------------------------------------------
            await review.transition_to(ReviewStatus.FETCHING)
            await db.commit()
            logger.info("[%s] Fetching PR data from GitHub...", review_id)

            async with GitHubService() as github:
                pr_meta = await github.fetch_pr_metadata(
                    owner=review.owner, repo=review.repo, number=review.pr_number,
                )
                diffs = await github.fetch_pr_diff(
                    owner=review.owner, repo=review.repo, number=review.pr_number,
                )

            review.pr_title = pr_meta.title

            # Persist file metadata
            status_map = {status.value: status for status in FileStatus}
            for diff in diffs:
                file_status = status_map.get(diff.status, FileStatus.MODIFIED)
                db.add(ReviewFile(
                    review_id=review_id,
                    file_path=diff.filename,
                    status=file_status,
                    additions=diff.additions,
                    deletions=diff.deletions,
                ))

            await db.commit()
            logger.info("[%s] Fetched %d files from PR", review_id, len(diffs))

            # ------------------------------------------------------------------
            # Step 2: Build prompt & call LLM
            # ------------------------------------------------------------------
            await review.transition_to(ReviewStatus.ANALYZING)
            await db.commit()
            logger.info("[%s] Analyzing with DeepSeek...", review_id)

            system_prompt = build_system_prompt(language=review.language)
            user_prompt = build_user_prompt(
                pr_info=pr_meta,
                diffs=diffs,
                options={"focus_areas": review.focus_areas.split(",") if review.focus_areas else None},
            )

            async with LLMClient() as llm:
                llm_response = await llm.chat_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )

            review.raw_llm_output = llm_response.content

            logger.info(
                "[%s] LLM analysis complete — %d input / %d output tokens",
                review_id, llm_response.input_tokens, llm_response.output_tokens,
            )

            # ------------------------------------------------------------------
            # Step 3: Parse & persist report
            # ------------------------------------------------------------------
            report = ReportGenerator.generate(llm_response.content)

            review.overall_score = report.overall_score
            review.total_issues = report.total_issues
            review.critical_count = report.critical_count
            review.major_count = report.major_count
            review.minor_count = report.minor_count

            # Persist comments
            for idx, issue in enumerate(report.issues):
                db.add(ReviewComment(
                    review_id=review_id,
                    file_path=issue.file_path,
                    line_start=issue.line_start,
                    line_end=issue.line_end,
                    severity=issue.severity,  # type: ignore[arg-type]
                    category=issue.category,  # type: ignore[arg-type]
                    title=issue.title,
                    body=issue.body,
                    suggestion=issue.suggestion,
                    code_snippet=issue.code_snippet,
                    sort_order=idx,
                ))

                # Update file comment count
                for f in review.files:
                    if f.file_path == issue.file_path:
                        f.comments_count += 1

            # ------------------------------------------------------------------
            # Step 4: Complete
            # ------------------------------------------------------------------
            await review.transition_to(ReviewStatus.COMPLETED)
            review.completed_at = datetime.now(timezone.utc)
            review.duration_ms = int((time.monotonic() - start_ts) * 1000)

            await db.commit()
            logger.info(
                "[%s] Review completed — %d issues found in %dms",
                review_id, report.total_issues, review.duration_ms,
            )

        except (GitHubAPIError, LLMAPIError, ReportParseError) as exc:
            try:
                review.status = ReviewStatus.FAILED
                review.error_code = exc.code
                review.error_detail = str(exc)
                review.completed_at = datetime.now(timezone.utc)
                review.duration_ms = int((time.monotonic() - start_ts) * 1000)
                await db.commit()
            except Exception:
                logger.exception("[%s] Failed to persist error state", review_id)

            logger.error(
                "[%s] Review failed: [%s] %s",
                review_id, exc.code, exc.message,
            )

        except Exception as exc:
            try:
                review.status = ReviewStatus.FAILED
                review.error_code = "INTERNAL_ERROR"
                review.error_detail = f"{type(exc).__name__}: {str(exc)}"
                review.completed_at = datetime.now(timezone.utc)
                review.duration_ms = int((time.monotonic() - start_ts) * 1000)
                await db.commit()
            except Exception:
                logger.exception("[%s] Failed to persist error state", review_id)

            logger.exception("[%s] Unexpected error in review pipeline", review_id)
