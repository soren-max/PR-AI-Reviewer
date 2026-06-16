"""
Tests for review workflow observability metrics.
"""
from __future__ import annotations

from app.services.review.metrics import build_review_metrics


def test_build_review_metrics_uses_safe_defaults() -> None:
    metrics = build_review_metrics({})

    assert metrics.review_time_ms == 0
    assert metrics.workflow_latency_ms == 0
    assert metrics.github_api_latency_ms == 0
    assert metrics.llm_latency_ms == 0
    assert metrics.prompt_length_chars == 0
    assert metrics.prompt_tokens == 0
    assert metrics.completion_tokens == 0
    assert metrics.total_tokens == 0
    assert metrics.risk_score == 0
    assert metrics.risk_level == "low"
    assert metrics.node_latency_ms == {}


def test_build_review_metrics_derives_total_tokens_when_missing() -> None:
    metrics = build_review_metrics({
        "latency": {"parse_pr": 3, "total": 2500},
        "metrics": {
            "github_api_latency_ms": 120,
            "llm_latency_ms": 2100,
            "prompt_length_chars": 4096,
            "risk_score": 85,
            "risk_level": "high",
        },
        "token_usage": {"input_tokens": 3200, "output_tokens": 450},
    })

    assert metrics.review_time_ms == 2500
    assert metrics.workflow_latency_ms == 2500
    assert metrics.github_api_latency_ms == 120
    assert metrics.llm_latency_ms == 2100
    assert metrics.prompt_length_chars == 4096
    assert metrics.prompt_tokens == 3200
    assert metrics.completion_tokens == 450
    assert metrics.total_tokens == 3650
    assert metrics.risk_score == 85
    assert metrics.risk_level == "high"
    assert metrics.node_latency_ms == {"parse_pr": 3}
