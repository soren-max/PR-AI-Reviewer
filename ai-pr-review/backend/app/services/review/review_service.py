"""
Review Service — Clean Architecture入口

职责：
  编排完整的Review流程

依赖关系：
  ReviewService → PromptBuilder → LLMService
                → RiskAnalyzer
                → DiffParser
                → ReportGenerator
                → GitHubService

分层规则：
  Controller (api/) → Service (编排) → Domain (纯逻辑) → Infrastructure (外部)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.services.github import GitHubService
from app.services.llm.base import BaseLLMService
from app.services.review.metrics import ReviewMetrics, build_review_metrics
from app.services.review.risk_analyzer import RiskResult
from app.services.review.report_generator import ReviewReport
from app.services.review.workflow_service import WorkflowService


@dataclass
class ReviewInput:
    """Input to the review service."""
    pr_url: str
    language: str = "zh"


@dataclass
class ReviewOutput:
    """Output from the review service."""
    pr_title: str
    pr_description: str
    owner: str
    repo: str
    pull_number: int
    report: ReviewReport
    risk: RiskResult
    diff_summary: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    error: Optional[str] = None
    duration_ms: int = 0
    metrics: ReviewMetrics | None = None


class ReviewService:
    """Backwards-compatible facade for the LangGraph review workflow.

    Existing API routes keep depending on ``ReviewService`` while the actual
    orchestration is delegated to ``WorkflowService``.
    """

    def __init__(
        self,
        github: Optional[GitHubService] = None,
        llm: Optional[BaseLLMService] = None,
        llm_provider: Optional[str] = None,
    ):
        self.github = github or GitHubService()
        self.llm = llm
        self.llm_provider = llm_provider

    async def review(self, inp: ReviewInput) -> ReviewOutput:
        """Execute the full review workflow and map state to legacy output."""
        state = await WorkflowService(github=self.github, llm=self.llm).run(
            pr_url=inp.pr_url,
            language=inp.language,
        )
        if state.get("last_exception") is not None:
            raise state["last_exception"]

        pr_meta = state["pr_info"]
        llm_result = state["review_result"]
        risk = state["risk_analysis"]
        diff_result = state["diff_analysis"]
        report = state["final_report"]
        metrics = build_review_metrics(state)

        return ReviewOutput(
            pr_title=pr_meta.title,
            pr_description=pr_meta.description,
            owner=state["owner"],
            repo=state["repo"],
            pull_number=state["pull_number"],
            report=report,
            risk=risk,
            diff_summary=summarize_diff_result(diff_result),
            input_tokens=llm_result.input_tokens,
            output_tokens=llm_result.output_tokens,
            model=llm_result.model,
            error=llm_result.error,
            duration_ms=metrics.review_time_ms,
            metrics=metrics,
        )


def summarize_diff_result(diff_result) -> str:
    """Build a short summary string from a DiffResult."""
    return (
        f"{diff_result.total_files_changed} files changed, "
        f"{diff_result.total_additions} insertions(+), "
        f"{diff_result.total_deletions} deletions(-)"
    )
