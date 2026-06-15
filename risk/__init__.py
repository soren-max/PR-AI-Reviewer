"""
Risk detection module.

Detects high-risk code changes based on file path patterns.
Covers: authentication, authorization, payment, security, database, etc.

Usage:
    from risk.engine import assess_risk, build_risk_prompt_context
"""
from risk.engine import assess_risk, build_risk_prompt_context, RiskResult, RiskLevel

__all__ = [
    "assess_risk",
    "build_risk_prompt_context",
    "RiskResult",
    "RiskLevel",
]
