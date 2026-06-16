"""
Integration tests for the LangGraph review workflow service.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import PRNotFoundError
from app.services.github import FileDiff, PRMetadata
from app.services.llm.base import LLMReviewResponse
from app.services.review import ReviewInput, ReviewService, WorkflowService


@pytest.fixture
def file_diff() -> FileDiff:
    return FileDiff(
        filename="src/auth.py",
        status="modified",
        additions=2,
        deletions=1,
        patch="@@ -1 +1,2 @@\n-old\n+new\n+def login():",
    )


@pytest.fixture
def llm_response() -> LLMReviewResponse:
    return LLMReviewResponse(
        raw_markdown=(
            '{"summary":{"overview":"Clean auth change."},'
            '"changed_modules":["src/auth.py"],'
            '"issues":[]}'
        ),
        input_tokens=100,
        output_tokens=40,
        model="deepseek-chat",
    )


@pytest.mark.asyncio
async def test_workflow_service_runs_langgraph_end_to_end(
    file_diff: FileDiff,
    llm_response: LLMReviewResponse,
) -> None:
    github = MagicMock()
    github.fetch_pr_metadata = AsyncMock(
        return_value=PRMetadata(title="Fix auth", description="Body")
    )
    github.fetch_pr_diff = AsyncMock(return_value=[file_diff])
    llm = MagicMock()
    llm.review_pr = AsyncMock(return_value=llm_response)

    state = await WorkflowService(github=github, llm=llm).run(
        "https://github.com/octocat/Hello-World/pull/1",
        language="en",
    )

    assert state["owner"] == "octocat"
    assert state["repo"] == "Hello-World"
    assert state["pull_number"] == 1
    assert state["pr_info"].title == "Fix auth"
    assert state["changed_files"] == [file_diff]
    assert state["diff_analysis"].total_files_changed == 1
    assert state["risk_analysis"].score >= 0
    assert state["review_result"].model == "deepseek-chat"
    assert state["final_report"].summary == "Clean auth change."
    assert state["token_usage"]["total_tokens"] == 140
    assert state["metrics"]["github_api_latency_ms"] >= 0
    assert state["metrics"]["llm_latency_ms"] >= 0
    assert state["metrics"]["prompt_length_chars"] > 0
    assert state["metrics"]["risk_score"] == state["risk_analysis"].score
    assert state["metrics"]["risk_level"] == state["risk_analysis"].risk_level.value
    assert state["errors"] == []
    assert {"parse_pr", "fetch_pr", "diff_analysis", "risk_detection", "review_generation", "report_generation", "total"} <= set(state["latency"])


@pytest.mark.asyncio
async def test_workflow_service_routes_errors_to_recovery() -> None:
    github = MagicMock()
    github.fetch_pr_metadata = AsyncMock(side_effect=PRNotFoundError("missing"))
    github.fetch_pr_diff = AsyncMock()
    llm = MagicMock()
    llm.review_pr = AsyncMock()

    state = await WorkflowService(github=github, llm=llm).run(
        "https://github.com/octocat/Hello-World/pull/404"
    )

    assert state["errors"]
    assert isinstance(state["last_exception"], PRNotFoundError)
    llm.review_pr.assert_not_called()


@pytest.mark.asyncio
async def test_review_service_facade_preserves_legacy_output(
    file_diff: FileDiff,
    llm_response: LLMReviewResponse,
) -> None:
    github = MagicMock()
    github.fetch_pr_metadata = AsyncMock(
        return_value=PRMetadata(title="Fix auth", description="Body")
    )
    github.fetch_pr_diff = AsyncMock(return_value=[file_diff])
    llm = MagicMock()
    llm.review_pr = AsyncMock(return_value=llm_response)

    output = await ReviewService(github=github, llm=llm).review(
        ReviewInput(pr_url="https://github.com/octocat/Hello-World/pull/1")
    )

    assert output.owner == "octocat"
    assert output.repo == "Hello-World"
    assert output.pull_number == 1
    assert output.pr_title == "Fix auth"
    assert output.report.summary == "Clean auth change."
    assert output.input_tokens == 100
    assert output.output_tokens == 40
    assert output.model == "deepseek-chat"
    assert output.metrics is not None
    assert output.metrics.review_time_ms >= 0
    assert output.metrics.prompt_tokens == 100
    assert output.metrics.completion_tokens == 40
    assert output.metrics.total_tokens == 140
    assert output.metrics.prompt_length_chars > 0
    assert output.metrics.risk_score == output.risk.score
