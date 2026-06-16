"""
Review Service — Clean Architecture module.

Exports are lazy so lightweight imports such as
``app.services.review.risk_analyzer`` do not instantiate API/config
dependencies during test collection.
"""
from __future__ import annotations

from typing import Any

__all__ = [
    "ReviewService",
    "ReviewInput",
    "ReviewOutput",
    "WorkflowService",
    "ReviewState",
    "parse_diff",
    "DiffResult",
    "assess_risk",
    "RiskResult",
    "build_risk_prompt_context",
    "build_review_prompt",
    "ReportGenerator",
    "ReviewReport",
    "ReviewIssue",
]


def __getattr__(name: str) -> Any:
    if name in {"ReviewService", "ReviewInput", "ReviewOutput"}:
        from app.services.review.review_service import ReviewInput, ReviewOutput, ReviewService

        return {
            "ReviewService": ReviewService,
            "ReviewInput": ReviewInput,
            "ReviewOutput": ReviewOutput,
        }[name]
    if name == "WorkflowService":
        from app.services.review.workflow_service import WorkflowService

        return WorkflowService
    if name == "ReviewState":
        from app.services.review.state import ReviewState

        return ReviewState
    if name in {"parse_diff", "DiffResult"}:
        from app.services.review.diff_parser import DiffResult, parse_diff

        return {"parse_diff": parse_diff, "DiffResult": DiffResult}[name]
    if name in {"assess_risk", "RiskResult", "build_risk_prompt_context"}:
        from app.services.review.risk_analyzer import (
            RiskResult,
            assess_risk,
            build_risk_prompt_context,
        )

        return {
            "assess_risk": assess_risk,
            "RiskResult": RiskResult,
            "build_risk_prompt_context": build_risk_prompt_context,
        }[name]
    if name == "build_review_prompt":
        from app.services.review.prompt_builder import build_review_prompt

        return build_review_prompt
    if name in {"ReportGenerator", "ReviewReport", "ReviewIssue"}:
        from app.services.review.report_generator import ReportGenerator, ReviewIssue, ReviewReport

        return {
            "ReportGenerator": ReportGenerator,
            "ReviewReport": ReviewReport,
            "ReviewIssue": ReviewIssue,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
