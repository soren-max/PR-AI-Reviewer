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

import logging
import time
from dataclasses import dataclass
from typing import Optional

from app.services.github import GitHubService
from app.services.llm.base import BaseLLMService
from app.services.llm.factory import get_llm_service
from app.services.review.diff_parser import parse_diff
from app.services.review.risk_analyzer import assess_risk, RiskResult, build_risk_prompt_context
from app.services.review.report_generator import ReportGenerator, ReviewReport

logger = logging.getLogger("services.review")


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


class ReviewService:
    """Orchestrates the complete PR review pipeline.

    Flow:
      1. Parse PR URL
      2. Fetch PR metadata + diff from GitHub
      3. Parse diff into structured data
      4. Analyze risk from changed files
      5. Build prompt with risk context
      6. Call LLM
      7. Generate final report
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
        """Execute the full review pipeline."""
        start = time.monotonic()
        from app.services.github import parse_pr_url

        # ---------- Step 1: Parse URL ----------
        parsed = parse_pr_url(inp.pr_url)

        # ---------- Step 2: Fetch from GitHub ----------
        pr_meta = await self.github.fetch_pr_metadata(
            owner=parsed.owner, repo=parsed.repo, number=parsed.pr_number,
        )
        diffs = await self.github.fetch_pr_diff(
            owner=parsed.owner, repo=parsed.repo, number=parsed.pr_number,
        )

        # Build raw diff text
        diff_lines: list[str] = []
        for f in diffs:
            if f.patch:
                diff_lines.append(f"diff --git a/{f.filename} b/{f.filename}")
                diff_lines.append(f"--- a/{f.filename}")
                diff_lines.append(f"+++ b/{f.filename}")
                diff_lines.append(f.patch)
                diff_lines.append("")
        diff_text = "\n".join(diff_lines)

        # ---------- Step 3: Parse diff ----------
        diff_result = parse_diff(diff_text)

        # ---------- Step 4: Analyze risk ----------
        changed_paths = [f.new_path for f in diff_result.files]
        risk = assess_risk(changed_paths)

        # ---------- Step 5: Build deterministic risk context ----------
        risk_context = build_risk_prompt_context(risk)

        # ---------- Step 6: Call LLM ----------
        llm = self.llm or get_llm_service()
        try:
            llm_result = await llm.review_pr(
                pr_title=pr_meta.title,
                pr_description=pr_meta.description,
                diff=diff_text,
                language=inp.language,
                risk_context=risk_context,
            )
        finally:
            if self.llm is None:
                await llm.close()

        # ---------- Step 7: Generate report ----------
        generator = ReportGenerator()
        report = generator.generate(
            raw_markdown=llm_result.raw_markdown,
            risk=risk,
            diff_summary=diff_result,
        )

        elapsed = int((time.monotonic() - start) * 1000)

        return ReviewOutput(
            pr_title=pr_meta.title,
            pr_description=pr_meta.description,
            owner=parsed.owner,
            repo=parsed.repo,
            pull_number=parsed.pr_number,
            report=report,
            risk=risk,
            diff_summary=summarize_diff_result(diff_result),
            input_tokens=llm_result.input_tokens,
            output_tokens=llm_result.output_tokens,
            model=llm_result.model,
            error=llm_result.error,
            duration_ms=elapsed,
        )


def summarize_diff_result(diff_result) -> str:
    """Build a short summary string from a DiffResult."""
    return (
        f"{diff_result.total_files_changed} files changed, "
        f"{diff_result.total_additions} insertions(+), "
        f"{diff_result.total_deletions} deletions(-)"
    )
