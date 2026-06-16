"""
Risk Analyzer — 分析变更文件的风险等级。

Clean Architecture 层级: Domain 适配器
依赖: risk.engine (核心引擎)

此模块是 Clean Architecture 的适配器层，包装 root 层的 risk/engine.py。
不重复实现业务逻辑。
"""
from __future__ import annotations

from risk.engine import (
    assess_risk as _assess_risk,
    build_risk_prompt_context as _build_risk_context,
    RiskResult,
    RiskLevel,
)

__all__ = [
    "assess_risk",
    "build_risk_prompt_context",
    "RiskResult",
    "RiskLevel",
]


def assess_risk(changed_files: list[str]) -> RiskResult:
    """Assess risk from changed file paths.
    
    Thin adapter over the risk detection engine.
    """
    return _assess_risk(changed_files)


def build_risk_prompt_context(risk: RiskResult) -> str:
    """Build risk warning string for LLM prompt.
    
    Thin adapter over the risk detection engine.
    """
    return _build_risk_context(risk)
