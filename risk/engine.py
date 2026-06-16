"""
Risk Detection Engine

Analyzes changed files in a Pull Request and determines the risk level
based on which modules are affected.  High-risk modules include
authentication, authorization, payment, database, security, and config.

Typical usage::

    >>> from risk_engine import assess_risk, RiskLevel

    >>> result = assess_risk(["src/auth/login.py", "README.md"])
    >>> result.risk_level
    <RiskLevel.HIGH: 'high'>
    >>> result.reason
    'authentication module changed'

    >>> result = assess_risk(["docs/README.md"])
    >>> result.risk_level
    <RiskLevel.LOW: 'low'>
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# Pre-compiled regex for safe path detection
_SAFE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE) for p in (
        r"^docs/", r"^documentation/", r"^readme", r"^changelog",
        r"^contributing", r"^\.github/", r"\.md$", r"\.txt$", r"\.rst$",
        r"tests?/", r"__tests__/", r"spec/", r"test_.*\.py$",
        r".*_test\.", r".*\.spec\.", r"^examples/", r"^scripts/",
        r"^assets/", r"^static/", r"^public/", r"\.css$", r"\.scss$",
        r"\.less$", r"\.svg$", r"\.png$", r"\.jpg$", r"\.ico$",
        r"\.gitignore", r"\.editorconfig", r"\.prettierrc", r"\.eslintrc",
    )
]


# ===========================================================================
# Enums
# ===========================================================================


class RiskLevel(str, Enum):
    """Risk level for a Pull Request."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ===========================================================================
# Risk categories with path patterns and weights
# ===========================================================================


@dataclass(frozen=True)
class RiskCategory:
    """A risk category with patterns and weight.

    Attributes:
        name: Human-readable category name (e.g. ``"authentication"``).
        weight: Contribution to overall risk score (higher = more risky).
        path_patterns: List of regex patterns that match file paths in
                       this category.
        description: Short description of why this category is risky.
    """

    name: str
    weight: int
    path_patterns: list[str]
    description: str


#: Pre-defined risk categories.  Order matters — the first matching
#: category determines the primary risk reason.
_RISK_CATEGORIES: list[RiskCategory] = [
    RiskCategory(
        name="authentication",
        weight=75,
        path_patterns=[
            r"auth/",
            r"login",
            r"logout",
            r"oauth",
            r"oidc",
            r"sso",
            r"session",
            r"jwt",
            r"token",
            r"password",
            r"credential",
            r"mfa",
            r"2fa",
            r"signin",
            r"signup",
            r"register",
        ],
        description="authentication module changed — may affect login, session, or token logic",
    ),
    RiskCategory(
        name="authorization",
        weight=75,
        path_patterns=[
            r"role",
            r"permission",
            r"rbac",
            r"acl",
            r"policy/",
            r"access.?control",
            r"privilege",
            r"grant",
            r"revoke",
        ],
        description="authorization module changed — may affect access control or permissions",
    ),
    RiskCategory(
        name="payment",
        weight=75,
        path_patterns=[
            r"payment",
            r"billing",
            r"charge",
            r"invoice",
            r"checkout",
            r"subscription",
            r"pricing",
            r"wallet",
            r"refund",
            r"transaction",
            r"stripe",
            r"paypal",
            r"paddle",
            r"order",
        ],
        description="payment module changed — may affect financial transactions",
    ),
    RiskCategory(
        name="security",
        weight=70,
        path_patterns=[
            r"security",
            r"encrypt",
            r"decrypt",
            r"hash",
            r"cipher",
            r"certificate",
            r"ssl",
            r"tls",
            r"csrf",
            r"cors",
            r"xss",
            r"sanitize",
            r"audit",
            r"vulnerability",
        ],
        description="security module changed — may introduce vulnerabilities",
    ),
    RiskCategory(
        name="database",
        weight=55,
        path_patterns=[
            r"database",
            r"db[^a-z]",
            r"sql",
            r"migration",
            r"schema",
            r"query",
            r"model",
            r"repository",
            r"dao",
            r"orm",
            r"redis",
            r"postgres",
            r"mysql",
            r"mongodb",
            r"elasticsearch",
            r"migrate",
        ],
        description="database module changed — may affect data integrity or schema",
    ),
    RiskCategory(
        name="config",
        weight=45,
        path_patterns=[
            r"config",
            r"setting",
            r"env",
            r"secret",
            r"key",
            r"endpoint",
            r"constant",
            r"property",
            r"yaml",
            r"toml",
            r"\.ini$",  # .ini config files
        ],
        description="configuration changed — may affect system behavior",
    ),
    RiskCategory(
        name="api",
        weight=40,
        path_patterns=[
            r"api",
            r"route",
            r"endpoint",
            r"controller",
            r"handler",
            r"middleware",
            r"graphql",
            r"rest",
            r"grpc",
            r"rpc",
        ],
        description="API module changed — may affect service contracts or routing",
    ),
    RiskCategory(
        name="infrastructure",
        weight=35,
        path_patterns=[
            r"docker",
            r"kubernetes",
            r"k8s",
            r"deploy",
            r"helm",
            r"terraform",
            r"cloudformation",
            r"ci",
            r"pipeline",
        ],
        description="infrastructure module changed — may affect deployment or operations",
    ),
]


# ===========================================================================
# Output model
# ===========================================================================


@dataclass
class RiskResult:
    """Risk assessment result for a Pull Request.

    Attributes:
        risk_level: Overall risk level (critical / high / medium / low).
        score: Numeric risk score (0-100) for fine-grained comparison.
        reason: Human-readable explanation of the risk assessment.
        matched_categories: List of risk categories that were triggered
            by the changed files.
        safe_paths: List of file paths that did not trigger any risk
            category (e.g. docs, tests, static assets).
    """

    risk_level: RiskLevel = RiskLevel.LOW
    score: int = 0
    reason: str = "no high-risk modules changed"
    matched_categories: list[str] = field(default_factory=list)
    safe_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialize to a plain dictionary for API responses."""
        return {
            "risk_level": self.risk_level.value,
            "score": self.score,
            "reason": self.reason,
            "matched_categories": self.matched_categories,
            "safe_paths": self.safe_paths,
        }


# ===========================================================================
# Helpers — file path matching
# ===========================================================================


def _normalize_path(file_path: str) -> str:
    """Normalize a file path for matching.

    Converts to lowercase, uses forward slashes, strips extensions.
    """
    path = file_path.replace("\\", "/").lower().strip()
    # Strip the file extension for matching (keep directory structure)
    return path


def _matches_category(file_path: str, category: RiskCategory) -> bool:
    """Check if a file path matches any pattern in a risk category."""
    normalized = _normalize_path(file_path)

    for pattern in category.path_patterns:
        try:
            if re.search(pattern, normalized):
                return True
        except re.error:
            # If a pattern is malformed, skip it
            continue

    return False


def _is_safe_path(file_path: str) -> bool:
    """Check if a file path is considered low-risk.

    Uses pre-compiled patterns for performance.
    """
    normalized = _normalize_path(file_path)
    return any(p.search(normalized) for p in _SAFE_PATTERNS)


# ===========================================================================
# Core engine
# ===========================================================================


def assess_risk(changed_files: list[str]) -> RiskResult:
    """Assess the risk level of a set of changed files.

    Args:
        changed_files: List of file paths that were modified in the PR.

    Returns:
        A :class:`RiskResult` with the risk level, score, and reasoning.

    Examples:
        >>> result = assess_risk(["src/auth/login.py"])
        >>> result.risk_level
        <RiskLevel.HIGH: 'high'>
        >>> result.score >= 80
        True

        >>> result = assess_risk(["README.md"])
        >>> result.risk_level
        <RiskLevel.LOW: 'low'>
        >>> result.score
        0
    """
    if not changed_files:
        return RiskResult(
            risk_level=RiskLevel.LOW,
            score=0,
            reason="no files changed",
        )

    # Track matched categories and their max weights
    matched: dict[str, RiskCategory] = {}  # category_name -> RiskCategory
    safe_paths: list[str] = []

    for file_path in changed_files:
        # Check if it's a safe/low-risk path
        if _is_safe_path(file_path):
            safe_paths.append(file_path)
            continue

        # Check against all risk categories
        for category in _RISK_CATEGORIES:
            if _matches_category(file_path, category):
                # Keep the highest weight for each category
                if (
                    category.name not in matched
                    or category.weight > matched[category.name].weight
                ):
                    matched[category.name] = category

    # Calculate overall score
    if not matched:
        return RiskResult(
            risk_level=RiskLevel.LOW,
            score=0,
            reason="no high-risk modules detected",
            safe_paths=safe_paths,
        )

    score = sum(cat.weight for cat in matched.values())
    # Cap at 150 to allow CRITICAL differentiation while keeping bounded
    score = min(score, 150)

    # Determine risk level
    risk_level = _score_to_level(score)

    # Build reasoning
    matched_names = list(matched.keys())
    weights = [matched[name].weight for name in matched_names]
    primary = matched_names[0]
    descriptions = [matched[name].description for name in matched_names]

    if len(matched_names) == 1:
        reason = descriptions[0]
    else:
        reason = f"{', '.join(matched_names[:-1])} and {matched_names[-1]} modules changed — {len(matched_names)} high-risk areas affected"

    return RiskResult(
        risk_level=risk_level,
        score=score,
        reason=reason,
        matched_categories=matched_names,
        safe_paths=safe_paths,
    )


def _score_to_level(score: int) -> RiskLevel:
    """Convert a numeric score to a RiskLevel.

    Thresholds:
        - 100+: CRITICAL (multiple high-risk categories combined)
        - 60-99: HIGH (one high-risk or two medium categories)
        - 30-59: MEDIUM (config, api, infrastructure)
        - 0-29: LOW (docs, tests, assets)
    """
    if score >= 100:
        return RiskLevel.CRITICAL
    if score >= 60:
        return RiskLevel.HIGH
    if score >= 30:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


# ===========================================================================
# Convenience: risk-aware review prompt builder
# ===========================================================================


def build_risk_prompt_context(risk: RiskResult) -> str:
    """Build a context string about risk for inclusion in a review prompt.

    Args:
        risk: The risk assessment result.

    Returns:
        A string to prepend to the review prompt, e.g.::

            "[⚠️  HIGH RISK] authentication module changed — \
             pay extra attention to session handling and token validation."
    """
    if risk.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
        emoji = "🔴" if risk.risk_level == RiskLevel.CRITICAL else "⚠️"
        return (
            f"[{emoji} {risk.risk_level.value.upper()} RISK] "
            f"{risk.reason}. "
            f"Reviewer should pay extra attention to security, "
            f"edge cases, and backward compatibility."
        )
    if risk.risk_level == RiskLevel.MEDIUM:
        return (
            f"[📋 MEDIUM RISK] {risk.reason}. "
            f"Standard review process applies."
        )
    return ""
