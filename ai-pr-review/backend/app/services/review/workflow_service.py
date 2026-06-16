"""
LangGraph-powered review workflow service.
"""
from __future__ import annotations

import time
from typing import Any

from langgraph.graph import END, StateGraph

from app.services.github import GitHubService
from app.services.llm.base import BaseLLMService
from app.services.review.checkpoint import ReviewCheckpoint
from app.services.review.nodes import (
    DiffAnalysisNode,
    ErrorRecoveryNode,
    FetchPRNode,
    ParsePRNode,
    ReportGenerationNode,
    ReviewGenerationNode,
    RiskDetectionNode,
    route_after_node,
)
from app.services.review.state import ReviewState


class WorkflowService:
    """Run the PR review pipeline as a LangGraph state workflow."""

    def __init__(
        self,
        github: GitHubService,
        llm: BaseLLMService | None = None,
        checkpoint: ReviewCheckpoint | None = None,
        max_attempts: int = 2,
    ) -> None:
        self.github = github
        self.llm = llm
        self.checkpoint = checkpoint
        self.max_attempts = max_attempts
        self._graph = self._build_graph()

    async def run(self, pr_url: str, language: str = "zh") -> ReviewState:
        """Execute the LangGraph workflow from PR URL to final report."""
        started = time.monotonic()
        initial_state: ReviewState = {
            "pr_url": pr_url,
            "language": language,
            "errors": [],
            "latency": {},
            "metrics": {},
            "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            "checkpoint": self.checkpoint,
        }
        final_state = await self._graph.ainvoke(initial_state)
        latency = dict(final_state.get("latency", {}))
        latency["total"] = int((time.monotonic() - started) * 1000)
        final_state["latency"] = latency
        if self.checkpoint is not None:
            await self.checkpoint.save(final_state)
        return final_state

    def _build_graph(self) -> Any:
        graph = StateGraph(ReviewState)

        graph.add_node("parse_pr", ParsePRNode())
        graph.add_node("fetch_pr", FetchPRNode(self.github, max_attempts=self.max_attempts))
        graph.add_node("diff_analysis", DiffAnalysisNode())
        graph.add_node("risk_detection", RiskDetectionNode())
        graph.add_node("review_generation", ReviewGenerationNode(self.llm, max_attempts=self.max_attempts))
        graph.add_node("report_generation", ReportGenerationNode())
        graph.add_node("error_recovery", ErrorRecoveryNode())

        graph.set_entry_point("parse_pr")
        self._add_conditional_step(graph, "parse_pr", "fetch_pr")
        self._add_conditional_step(graph, "fetch_pr", "diff_analysis")
        self._add_conditional_step(graph, "diff_analysis", "risk_detection")
        self._add_conditional_step(graph, "risk_detection", "review_generation")
        self._add_conditional_step(graph, "review_generation", "report_generation")
        graph.add_conditional_edges(
            "report_generation",
            route_after_node,
            {"ok": END, "error": "error_recovery"},
        )
        graph.add_edge("error_recovery", END)

        return graph.compile()

    def _add_conditional_step(
        self,
        graph: StateGraph,
        source: str,
        next_node: str,
    ) -> None:
        graph.add_conditional_edges(
            source,
            route_after_node,
            {"ok": next_node, "error": "error_recovery"},
        )
