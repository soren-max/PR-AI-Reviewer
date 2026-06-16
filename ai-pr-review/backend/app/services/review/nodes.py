"""
Single-responsibility nodes for the LangGraph PR review workflow.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.core.exceptions import InvalidPRUrlError, PRNotFoundError
from app.services.github import GitHubService, parse_pr_url
from app.services.llm.base import BaseLLMService
from app.services.llm.factory import get_llm_service
from app.services.review.diff_parser import parse_diff
from app.services.review.report_generator import ReportGenerator
from app.services.review.risk_analyzer import assess_risk, build_risk_prompt_context
from app.services.review.state import ReviewState

logger = logging.getLogger("services.review.workflow.nodes")

T = TypeVar("T")


class WorkflowNode:
    """Base helper for consistent node latency and error recording."""

    name = "workflow"

    async def __call__(self, state: ReviewState) -> ReviewState:
        start = time.monotonic()
        try:
            updates = await self.run(state)
            return _with_latency(state, updates, self.name, start)
        except Exception as exc:
            logger.exception("Review workflow node failed: %s", self.name)
            return _with_latency(
                state,
                {
                    "errors": [*state.get("errors", []), f"{self.name}: {exc}"],
                    "last_exception": exc,
                },
                self.name,
                start,
            )

    async def run(self, state: ReviewState) -> ReviewState:
        raise NotImplementedError


class ParsePRNode(WorkflowNode):
    """Parse the submitted GitHub PR URL."""

    name = "parse_pr"

    async def run(self, state: ReviewState) -> ReviewState:
        parsed = parse_pr_url(state["pr_url"])
        return {
            "owner": parsed.owner,
            "repo": parsed.repo,
            "pull_number": parsed.pr_number,
        }


class FetchPRNode(WorkflowNode):
    """Fetch PR metadata and changed files from GitHub."""

    name = "fetch_pr"

    def __init__(self, github: GitHubService, max_attempts: int = 2) -> None:
        self.github = github
        self.max_attempts = max_attempts

    async def run(self, state: ReviewState) -> ReviewState:
        owner = state["owner"]
        repo = state["repo"]
        pull_number = state["pull_number"]

        pr_info = await _retry(
            lambda: self.github.fetch_pr_metadata(owner, repo, pull_number),
            max_attempts=self.max_attempts,
        )
        changed_files = await _retry(
            lambda: self.github.fetch_pr_diff(owner, repo, pull_number),
            max_attempts=self.max_attempts,
        )
        return {
            "pr_info": pr_info,
            "changed_files": changed_files,
            "diff_text": build_diff_text(changed_files),
        }


class DiffAnalysisNode(WorkflowNode):
    """Parse unified diff text into the domain diff model."""

    name = "diff_analysis"

    async def run(self, state: ReviewState) -> ReviewState:
        return {"diff_analysis": parse_diff(state.get("diff_text", ""))}


class RiskDetectionNode(WorkflowNode):
    """Assess deterministic risk from changed file paths."""

    name = "risk_detection"

    async def run(self, state: ReviewState) -> ReviewState:
        diff_analysis = state["diff_analysis"]
        return {"risk_analysis": assess_risk(diff_analysis.changed_paths)}


class ReviewGenerationNode(WorkflowNode):
    """Call the configured LLM review agent using the existing Week2 prompt."""

    name = "review_generation"

    def __init__(
        self,
        llm: BaseLLMService | None = None,
        max_attempts: int = 2,
    ) -> None:
        self.llm = llm
        self.max_attempts = max_attempts

    async def run(self, state: ReviewState) -> ReviewState:
        llm = self.llm or get_llm_service()
        should_close = self.llm is None
        pr_info = state["pr_info"]
        risk_context = build_risk_prompt_context(state["risk_analysis"])

        try:
            result = await _retry(
                lambda: llm.review_pr(
                    pr_title=pr_info.title,
                    pr_description=pr_info.description,
                    diff=state.get("diff_text", ""),
                    language=state.get("language", "zh"),
                    risk_context=risk_context,
                ),
                max_attempts=self.max_attempts,
            )
        finally:
            if should_close:
                await llm.close()

        return {
            "review_result": result,
            "token_usage": {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "total_tokens": result.input_tokens + result.output_tokens,
            },
        }


class ReportGenerationNode(WorkflowNode):
    """Convert the LLM response into the existing final report model."""

    name = "report_generation"

    def __init__(self, generator: ReportGenerator | None = None) -> None:
        self.generator = generator or ReportGenerator()

    async def run(self, state: ReviewState) -> ReviewState:
        review_result = state["review_result"]
        report = self.generator.generate(
            raw_markdown=review_result.raw_markdown,
            risk=state.get("risk_analysis"),
            diff_summary=state.get("diff_analysis"),
        )
        report.llm_error = review_result.error
        return {"final_report": report}


class ErrorRecoveryNode(WorkflowNode):
    """Terminate failed workflows with the error recorded in state."""

    name = "error_recovery"

    async def run(self, state: ReviewState) -> ReviewState:
        return {"errors": state.get("errors", [])}


def build_diff_text(changed_files: list[Any]) -> str:
    """Build unified diff text from GitHub file payloads."""
    diff_lines: list[str] = []
    for file_diff in changed_files:
        patch = getattr(file_diff, "patch", None)
        if not patch:
            continue
        filename = getattr(file_diff, "filename", "")
        diff_lines.append(f"diff --git a/{filename} b/{filename}")
        diff_lines.append(f"--- a/{filename}")
        diff_lines.append(f"+++ b/{filename}")
        diff_lines.append(str(patch))
        diff_lines.append("")
    return "\n".join(diff_lines)


def route_after_node(state: ReviewState) -> str:
    """Conditional edge router used after each executable node."""
    return "error" if state.get("errors") else "ok"


async def _retry(operation: Callable[[], Awaitable[T]], max_attempts: int) -> T:
    """Retry transient node operations without hiding domain exceptions."""
    attempts = max(1, max_attempts)
    last_exception: Exception | None = None
    for attempt in range(attempts):
        try:
            return await operation()
        except (InvalidPRUrlError, PRNotFoundError):
            raise
        except Exception as exc:
            last_exception = exc
            if attempt == attempts - 1:
                raise
            logger.warning("Retrying workflow operation after error: %s", exc)
    raise RuntimeError("Workflow retry exhausted") from last_exception


def _with_latency(
    current: ReviewState,
    updates: ReviewState,
    node_name: str,
    start: float,
) -> ReviewState:
    latency = dict(current.get("latency", {}))
    latency[node_name] = int((time.monotonic() - start) * 1000)
    return {**updates, "latency": latency}
