"""
Risk Analyzer — 分析变更文件的风险等级。

Clean Architecture 层级: Domain
依赖: 无（纯函数）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    """Risk level for a Pull Request."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


_SAFE_PATH_RE = re.compile(
    r"(^docs/|^tests?/|readme|\.md$|\.txt$|\.rst$|\.css$|\.scss$|\.svg$|\.png$|\.jpg$|\.jpeg$)",
    re.IGNORECASE,
)

_RISK_RULES: tuple[tuple[str, int, tuple[str, ...], str], ...] = (
    ("authentication", 75, ("auth", "login", "oauth", "session", "jwt", "token", "password"), "authentication module changed"),
    ("authorization", 75, ("permission", "rbac", "access_control", "policy", "role"), "authorization module changed"),
    ("payment", 75, ("payment", "billing", "checkout", "invoice", "stripe", "order"), "payment module changed"),
    ("security", 70, ("security", "encrypt", "csrf", "xss", "sanitize", "secret"), "security module changed"),
    ("database", 55, ("database", "migration", "schema", "query", "model", "repository", "sql"), "database module changed"),
    ("config", 45, ("config", "settings", ".env", "yaml", "toml", ".ini"), "configuration changed"),
    ("api", 40, ("api", "route", "endpoint", "controller", "handler"), "API module changed"),
    ("infrastructure", 35, ("docker", "deploy", "k8s", "terraform", "ci"), "infrastructure changed"),
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
    matched: dict[str, tuple[int, str]] = {}
    safe_paths: list[str] = []

    for path in changed_files:
        normalized = path.replace("\\", "/").lower()
        matched_path = False
        for name, weight, patterns, description in _RISK_RULES:
            if any(pattern in normalized for pattern in patterns):
                matched[name] = (weight, description)
                matched_path = True
        if not matched_path and _SAFE_PATH_RE.search(normalized):
            safe_paths.append(path)

    if not matched:
        return RiskResult(safe_paths=safe_paths)

    score = min(sum(weight for weight, _ in matched.values()), 150)
    if score >= 100 or len(matched) >= 2 and score >= 95:
        level = RiskLevel.CRITICAL
    elif score >= 70:
        level = RiskLevel.HIGH
    elif score >= 35:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    descriptions = [description for _, description in matched.values()]
    return RiskResult(
        risk_level=level,
        score=score,
        reason="; ".join(descriptions),
        matched_categories=list(matched.keys()),
        safe_paths=safe_paths,
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
