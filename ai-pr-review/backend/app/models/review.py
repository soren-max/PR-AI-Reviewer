"""
Review ORM models.
"""
import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.dialects.sqlite import CHAR
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    FETCHING = "fetching"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class Category(str, enum.Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    BUG = "bug"
    DESIGN = "design"
    STYLE = "style"
    BEST_PRACTICE = "best_practice"
    READABILITY = "readability"


class FileStatus(str, enum.Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


# ---------------------------------------------------------------------------
# Review — main aggregate root
# ---------------------------------------------------------------------------
class Review(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reviews"

    pr_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    repo: Mapped[str] = mapped_column(String(128), nullable=False)
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pr_title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status"),
        default=ReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    status_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Score & summary
    overall_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_issues: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    critical_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    major_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    minor_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Review options
    focus_areas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="zh")

    # Error tracking
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Raw LLM output for debugging
    raw_llm_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    comments: Mapped[list["ReviewComment"]] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="ReviewComment.sort_order",
    )
    files: Mapped[list["ReviewFile"]] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
    )

    # -----------------------------------------------------------------------
    # Domain helpers
    # -----------------------------------------------------------------------
    async def transition_to(self, target: ReviewStatus) -> None:
        """Validate and apply state transition."""
        ALLOWED_TRANSITIONS = {
            ReviewStatus.PENDING: [ReviewStatus.FETCHING, ReviewStatus.FAILED],
            ReviewStatus.FETCHING: [ReviewStatus.ANALYZING, ReviewStatus.FAILED],
            ReviewStatus.ANALYZING: [ReviewStatus.COMPLETED, ReviewStatus.FAILED],
            ReviewStatus.COMPLETED: [],
            ReviewStatus.FAILED: [],
        }
        allowed = ALLOWED_TRANSITIONS.get(self.status, [])
        if target not in allowed:
            from app.core.exceptions import StateTransitionError
            raise StateTransitionError(current=self.status.value, target=target.value)
        self.status = target

    # -----------------------------------------------------------------------
    # Query helpers
    # -----------------------------------------------------------------------
    @staticmethod
    async def get_by_id(db: AsyncSession, review_id: str) -> Optional["Review"]:
        from sqlalchemy.orm import selectinload
        stmt = (
            select(Review)
            .where(Review.id == review_id)
            .options(selectinload(Review.comments), selectinload(Review.files))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_paginated(
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
        status: str | None = None,
    ) -> tuple[list["Review"], int]:
        query = select(Review)
        count_query = select(func.count(Review.id))
        if status:
            query = query.where(Review.status == status)
            count_query = count_query.where(Review.status == status)

        query = query.order_by(Review.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        result = await db.execute(query)
        items = list(result.scalars().all())
        return items, total


# ---------------------------------------------------------------------------
# ReviewComment — individual review findings
# ---------------------------------------------------------------------------
class ReviewComment(Base, UUIDMixin):
    __tablename__ = "review_comments"

    review_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    line_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    line_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity"), nullable=False
    )
    category: Mapped[Category] = mapped_column(
        Enum(Category, name="category"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    code_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Back-reference
    review: Mapped[Review] = relationship(back_populates="comments")


# ---------------------------------------------------------------------------
# ReviewFile — files touched in the PR
# ---------------------------------------------------------------------------
class ReviewFile(Base, UUIDMixin):
    __tablename__ = "review_files"

    review_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[FileStatus] = mapped_column(
        Enum(FileStatus, name="file_status"), nullable=False
    )
    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)

    review: Mapped[Review] = relationship(back_populates="files")
