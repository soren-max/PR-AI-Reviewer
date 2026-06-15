"""
Risk Analyzer — 分析变更文件的风险等级。

Clean Architecture 层级: Domain
依赖: 无（纯函数）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# Re-export from the existing risk engine
from risk.engine import (
    assess_risk as _assess_risk,
    build_risk_prompt_context as _build_risk_context,
    RiskLevel,
)


@dataclass
class RiskResult:
    risk_level: RiskLevel = RiskLevel.LOW
    score: int = 0
    reason: str = ""
    matched_categories: list[str] = field(default_factory=list)
    safe_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "risk_level": self.risk_level.value,
            "score": self.score,
            "reason": self.reason,
            "matched_categories": self.matched_categories,
            "safe_paths": self.safe_paths,
        }


def assess_risk(changed_files: list[str]) -> RiskResult:
    """Assess risk from a list of changed file paths."""
    raw = _assess_risk(changed_files)
    return RiskResult(
        risk_level=raw.risk_level,
        score=raw.score,
        reason=raw.reason,
        matched_categories=raw.matched_categories,
        safe_paths=raw.safe_paths,
    )


def build_risk_prompt_context(risk: RiskResult) -> str:
    """Build a risk warning string for inclusion in the LLM prompt."""
    if risk.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
        emoji = "🔴" if risk.risk_level == RiskLevel.CRITICAL else "⚠️"
        return (
            f"[{emoji} {risk.risk_level.value.upper()} RISK] "
            f"{risk.reason}. "
            f"Pay extra attention to security, edge cases, "
            f"and backward compatibility."
        )
    if risk.risk_level == RiskLevel.MEDIUM:
        return f"[📋 MEDIUM RISK] {risk.reason}."
    return ""
