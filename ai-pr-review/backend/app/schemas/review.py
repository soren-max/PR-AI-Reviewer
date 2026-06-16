"""
Pydantic schemas for Review-related API requests and responses.
"""
import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.exceptions import InvalidPRUrlError

# ---------------------------------------------------------------------------
# PR URL regex
# ---------------------------------------------------------------------------
PR_URL_PATTERN = re.compile(
    r"^https://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)/pull/(?P<number>\d+)/?$"
)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class ReviewOptions(BaseModel):
    """Optional configuration for a review run."""

    focus_areas: list[str] | None = Field(
        default=None,
        description="Areas to focus on: security, performance, bug, design, style",
    )
    max_comments: int = Field(default=30, ge=1, le=100)
    language: str = Field(default="zh", pattern=r"^(zh|en)$")


class CreateReviewReq(BaseModel):
    """Request body to create a new review."""

    pr_url: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="Full GitHub Pull Request URL",
        examples=["https://github.com/owner/repo/pull/42"],
    )
    options: ReviewOptions | None = None

    @field_validator("pr_url")
    @classmethod
    def validate_pr_url(cls, v: str) -> str:
        v = v.strip()
        # Accept URL with query params / fragments by stripping them
        base_url = v.split("?")[0].split("#")[0]
        if not PR_URL_PATTERN.match(base_url):
            raise InvalidPRUrlError()
        return base_url


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class PRInfo(BaseModel):
    """PR metadata summary."""

    owner: str
    repo: str
    number: int
    title: str | None = None
    author: str | None = None
    base_branch: str | None = None
    head_branch: str | None = None
    changed_files_count: int = 0
    additions: int = 0
    deletions: int = 0


class ReviewSummary(BaseModel):
    """High-level review results summary."""

    overall_score: int | None = None
    total_issues: int = 0
    critical: int = 0
    major: int = 0
    minor: int = 0
    info: int = 0


class ReviewCommentResp(BaseModel):
    """A single review comment."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    severity: str
    category: str
    title: str
    body: str
    suggestion: str | None = None
    code_snippet: str | None = None


class ReviewFileResp(BaseModel):
    """A file changed in the PR."""

    model_config = ConfigDict(from_attributes=True)

    file_path: str
    status: str
    additions: int
    deletions: int
    comments_count: int


class ReviewResp(BaseModel):
    """Response returned after submitting a review (short)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "pr_url": "https://github.com/owner/repo/pull/42",
                "status": "pending",
                "created_at": "2025-01-01T00:00:00+00:00",
            }
        },
    )

    id: str
    pr_url: str
    status: str
    created_at: str | None = None


class ReviewDetailResp(ReviewResp):
    """Full review detail including results."""

    pr_info: PRInfo | None = None
    summary: ReviewSummary | None = None
    comments: list[ReviewCommentResp] = []
    files: list[ReviewFileResp] = []
    completed_at: str | None = None
    duration_ms: int | None = None
    error_code: str | None = None
    error_detail: str | None = None

    @classmethod
    def from_orm(cls, review) -> "ReviewDetailResp":
        """Build full response from an ORM Review instance."""
        comments = [
            ReviewCommentResp(
                id=str(c.id),
                file_path=c.file_path,
                line_start=c.line_start,
                line_end=c.line_end,
                severity=c.severity.value,
                category=c.category.value,
                title=c.title,
                body=c.body,
                suggestion=c.suggestion,
                code_snippet=c.code_snippet,
            )
            for c in review.comments
        ]
        files = [
            ReviewFileResp(
                file_path=f.file_path,
                status=f.status.value,
                additions=f.additions,
                deletions=f.deletions,
                comments_count=f.comments_count,
            )
            for f in review.files
        ]
        summary = None
        if review.total_issues is not None:
            summary = ReviewSummary(
                overall_score=review.overall_score,
                total_issues=review.total_issues,
                critical=review.critical_count or 0,
                major=review.major_count or 0,
                minor=review.minor_count or 0,
            )

        return cls(
            id=str(review.id),
            pr_url=review.pr_url,
            status=review.status.value,
            created_at=_fmt_dt(review.created_at),
            summary=summary,
            comments=comments,
            files=files,
            completed_at=_fmt_dt(review.completed_at),
            duration_ms=review.duration_ms,
            error_code=review.error_code,
            error_detail=review.error_detail,
        )


class ReviewListResp(BaseModel):
    """Compact review item for list view."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    pr_url: str
    status: str
    total_issues: int | None = None
    critical_count: int | None = None
    created_at: str | None = None

    @classmethod
    def from_orm(cls, review) -> "ReviewListResp":
        return cls(
            id=str(review.id),
            pr_url=review.pr_url,
            status=review.status.value,
            total_issues=review.total_issues,
            critical_count=review.critical_count,
            created_at=_fmt_dt(review.created_at),
        )


def _fmt_dt(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None
