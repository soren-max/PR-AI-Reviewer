"""
Unit tests for LangGraph review workflow nodes.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import InvalidPRUrlError
from app.services.github import FileDiff, PRMetadata
from app.services.llm.base import LLMReviewResponse
from app.services.review.nodes import (
    DiffAnalysisNode,
    FetchPRNode,
    ParsePRNode,
    ReportGenerationNode,
    ReviewGenerationNode,
    RiskDetectionNode,
    build_diff_text,
    route_after_node,
)
from app.services.review.state import ReviewState


def sample_file_diff() -> FileDiff:
    return FileDiff(
        filename="src/auth.py",
        status="modified",
        additions=3,
        deletions=1,
        patch="@@ -1 +1,2 @@\n-old\n+new\n+def login():",
    )


@pytest.mark.asyncio
async def test_parse_pr_node_extracts_pr_components() -> None:
    state: ReviewState = {"pr_url": "https://github.com/octocat/Hello-World/pull/42"}

    result = await ParsePRNode()(state)

    assert result["owner"] == "octocat"
    assert result["repo"] == "Hello-World"
    assert result["pull_number"] == 42
    assert route_after_node(result) == "ok"


@pytest.mark.asyncio
async def test_parse_pr_node_records_invalid_url_error() -> None:
    result = await ParsePRNode()({"pr_url": "not-a-pr"})

    assert result["errors"]
    assert isinstance(result["last_exception"], InvalidPRUrlError)
    assert route_after_node(result) == "error"


@pytest.mark.asyncio
async def test_fetch_pr_node_retries_transient_github_error() -> None:
    github = MagicMock()
    github.fetch_pr_metadata = AsyncMock(
        side_effect=[
            RuntimeError("temporary failure"),
            PRMetadata(title="Fix auth", description="Body"),
        ]
    )
    github.fetch_pr_diff = AsyncMock(return_value=[sample_file_diff()])

    result = await FetchPRNode(github, max_attempts=2)({
        "owner": "octocat",
        "repo": "Hello-World",
        "pull_number": 1,
    })

    assert result["pr_info"].title == "Fix auth"
    assert result["changed_files"][0].filename == "src/auth.py"
    assert "diff --git a/src/auth.py b/src/auth.py" in result["diff_text"]
    assert github.fetch_pr_metadata.await_count == 2


@pytest.mark.asyncio
async def test_diff_and_risk_nodes_build_domain_analysis() -> None:
    diff_text = build_diff_text([sample_file_diff()])

    diff_state = await DiffAnalysisNode()({"diff_text": diff_text})
    risk_state = await RiskDetectionNode()({**diff_state})

    assert diff_state["diff_analysis"].total_files_changed == 1
    assert diff_state["diff_analysis"].changed_paths == ["src/auth.py"]
    assert risk_state["risk_analysis"].score >= 0


@pytest.mark.asyncio
async def test_review_generation_node_calls_llm_with_risk_context() -> None:
    llm_result = LLMReviewResponse(
        raw_markdown='{"summary":"ok","changed_modules":[],"issues":[]}',
        input_tokens=10,
        output_tokens=5,
        model="deepseek-chat",
    )
    llm = MagicMock()
    llm.review_pr = AsyncMock(return_value=llm_result)

    diff_state = await DiffAnalysisNode()({"diff_text": build_diff_text([sample_file_diff()])})
    risk_state = await RiskDetectionNode()({**diff_state})
    state: ReviewState = {
        **diff_state,
        **risk_state,
        "pr_info": PRMetadata(title="Fix auth", description="Body"),
        "diff_text": build_diff_text([sample_file_diff()]),
        "language": "zh",
    }

    result = await ReviewGenerationNode(llm=llm)(state)

    assert result["review_result"].model == "deepseek-chat"
    assert result["token_usage"]["total_tokens"] == 15
    llm.review_pr.assert_awaited_once()
    call_kwargs = llm.review_pr.await_args.kwargs
    assert call_kwargs["pr_title"] == "Fix auth"
    assert call_kwargs["language"] == "zh"
    assert "risk_context" in call_kwargs


@pytest.mark.asyncio
async def test_report_generation_node_preserves_llm_error() -> None:
    llm_result = LLMReviewResponse(
        raw_markdown="",
        error="ProviderAuthError: invalid API key",
        model="deepseek-chat",
    )
    diff_state = await DiffAnalysisNode()({"diff_text": build_diff_text([sample_file_diff()])})
    risk_state = await RiskDetectionNode()({**diff_state})

    result = await ReportGenerationNode()({
        **diff_state,
        **risk_state,
        "review_result": llm_result,
    })

    assert result["final_report"].llm_error == "ProviderAuthError: invalid API key"
