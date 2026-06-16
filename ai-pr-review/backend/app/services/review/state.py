"""
LangGraph review workflow state.

The state intentionally carries both domain objects and operational metadata so
future agent nodes can be added without changing the public API contract.
"""
from __future__ import annotations

from typing import Any, TypedDict

from app.services.github import FileDiff, PRMetadata
from app.services.llm.base import LLMReviewResponse
from app.services.review.diff_parser import DiffResult
from app.services.review.report_generator import ReviewReport
from app.services.review.risk_analyzer import RiskResult


class ReviewState(TypedDict, total=False):
    """Shared state passed between LangGraph review nodes."""

    pr_url: str
    language: str

    owner: str
    repo: str
    pull_number: int

    pr_info: PRMetadata
    changed_files: list[FileDiff]
    diff_text: str
    diff_analysis: DiffResult
    risk_analysis: RiskResult
    review_result: LLMReviewResponse
    final_report: ReviewReport

    errors: list[str]
    last_exception: Exception
    latency: dict[str, int]
    token_usage: dict[str, int]
    metrics: dict[str, Any]
    checkpoint: Any
