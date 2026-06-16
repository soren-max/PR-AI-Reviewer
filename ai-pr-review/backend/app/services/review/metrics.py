"""
Review workflow observability metrics.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ReviewMetrics:
    """Stable metrics exposed by the review workflow."""

    review_time_ms: int = 0
    workflow_latency_ms: int = 0
    github_api_latency_ms: int = 0
    llm_latency_ms: int = 0
    prompt_length_chars: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    risk_score: int = 0
    risk_level: str = "low"
    node_latency_ms: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable metrics payload."""
        return asdict(self)


def build_review_metrics(state: dict[str, Any]) -> ReviewMetrics:
    """Build metrics from workflow state using safe defaults."""
    latency = state.get("latency") or {}
    raw_metrics = state.get("metrics") or {}
    token_usage = state.get("token_usage") or {}
    risk = state.get("risk_analysis")

    prompt_tokens = _to_int(token_usage.get("input_tokens"))
    completion_tokens = _to_int(token_usage.get("output_tokens"))
    total_tokens = _to_int(token_usage.get("total_tokens")) or prompt_tokens + completion_tokens

    return ReviewMetrics(
        review_time_ms=_to_int(latency.get("total")),
        workflow_latency_ms=_to_int(latency.get("total")),
        github_api_latency_ms=_to_int(raw_metrics.get("github_api_latency_ms")),
        llm_latency_ms=_to_int(raw_metrics.get("llm_latency_ms")),
        prompt_length_chars=_to_int(raw_metrics.get("prompt_length_chars")),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        risk_score=_to_int(getattr(risk, "score", raw_metrics.get("risk_score", 0))),
        risk_level=str(getattr(getattr(risk, "risk_level", None), "value", raw_metrics.get("risk_level", "low"))),
        node_latency_ms={k: _to_int(v) for k, v in latency.items() if k != "total"},
    )


def _to_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
