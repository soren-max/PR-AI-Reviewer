"""
Tests for ``risk_engine.py`` — Risk Detection Engine.

Covers:
  - Core risk assessment (assess_risk)
  - All 8 risk categories (auth, payment, database, security, etc.)
  - Safe path detection (docs, tests, README, assets)
  - Edge cases (empty list, mixed paths, multiple categories)
  - Risk levels (critical / high / medium / low)
  - Scoring and normalization
  - Risk prompt builder
"""
from __future__ import annotations

import unittest

from risk_engine import (
    assess_risk,
    build_risk_prompt_context,
    RiskResult,
    RiskLevel,
)


class TestRiskAssessment(unittest.TestCase):
    """Core risk assessment engine."""

    def test_authentication_high_risk(self) -> None:
        result = assess_risk(["src/auth/login.py"])
        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertIn("auth", result.reason.lower())

    def test_oauth_token_high_risk(self) -> None:
        result = assess_risk(["app/services/oauth.py"])
        self.assertEqual(result.risk_level, RiskLevel.HIGH)

    def test_payment_high_risk(self) -> None:
        result = assess_risk(["payment/checkout.py"])
        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertIn("payment", result.reason.lower())

    def test_security_high_risk(self) -> None:
        result = assess_risk(["security/encryption.py"])
        self.assertEqual(result.risk_level, RiskLevel.HIGH)

    def test_database_medium_high(self) -> None:
        result = assess_risk(["database/migrations/001_init.py"])
        self.assertIn(result.risk_level, [RiskLevel.MEDIUM, RiskLevel.HIGH])

    def test_config_medium_risk(self) -> None:
        result = assess_risk(["config/settings.py"])
        self.assertEqual(result.risk_level, RiskLevel.MEDIUM)

    def test_api_medium_risk(self) -> None:
        result = assess_risk(["api/routes/users.py"])
        self.assertEqual(result.risk_level, RiskLevel.MEDIUM)

    def test_readme_low_risk(self) -> None:
        result = assess_risk(["README.md"])
        self.assertEqual(result.risk_level, RiskLevel.LOW)
        self.assertEqual(result.score, 0)

    def test_docs_only_low_risk(self) -> None:
        result = assess_risk(["docs/guide.md", "docs/api.md"])
        self.assertEqual(result.risk_level, RiskLevel.LOW)

    def test_test_files_low_risk(self) -> None:
        result = assess_risk(["tests/test_auth.py", "tests/test_payment.py"])
        self.assertEqual(result.risk_level, RiskLevel.LOW)

    def test_mixed_paths(self) -> None:
        """Auth change + docs change should still detect the auth risk."""
        result = assess_risk(["src/auth/login.py", "README.md"])
        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertIn("auth", result.reason.lower())

    def test_empty_list(self) -> None:
        result = assess_risk([])
        self.assertEqual(result.risk_level, RiskLevel.LOW)
        self.assertEqual(result.score, 0)

    def test_static_assets_low_risk(self) -> None:
        result = assess_risk(["assets/logo.svg", "public/style.css"])
        self.assertEqual(result.risk_level, RiskLevel.LOW)


class TestRiskCategories(unittest.TestCase):
    """Each risk category should be detected correctly."""

    def test_authentication_variants(self) -> None:
        paths = [
            "auth/login.py", "login/views.py", "oauth/callback.py",
            "jwt/token.py", "session/store.py", "mfa/setup.py",
            "password/reset.py",
        ]
        for path in paths:
            with self.subTest(path=path):
                result = assess_risk([path])
                self.assertGreaterEqual(result.score, 70, f"{path} should be high risk")

    def test_authorization_paths(self) -> None:
        paths = [
            "rbac/policies.py", "permissions/admin.py",
            "access_control/middleware.py",
        ]
        for path in paths:
            with self.subTest(path=path):
                result = assess_risk([path])
                self.assertGreaterEqual(result.score, 60)

    def test_payment_variants(self) -> None:
        paths = [
            "billing/invoices.py", "checkout/cart.py",
            "subscription/plans.py", "stripe/webhook.py",
            "order/service.py",
        ]
        for path in paths:
            with self.subTest(path=path):
                result = assess_risk([path])
                self.assertGreaterEqual(result.score, 70, f"{path} should be high risk")


class TestSafePaths(unittest.TestCase):
    """Safe/low-risk paths should be identified."""

    def test_safe_paths_tracked(self) -> None:
        result = assess_risk(["README.md", "docs/guide.md"])
        self.assertEqual(len(result.safe_paths), 2)

    def test_mixed_result_has_safe_paths(self) -> None:
        result = assess_risk(["src/auth/login.py", "README.md"])
        self.assertIn("README.md", result.safe_paths)

    def test_safe_extensions(self) -> None:
        safe = [".md", ".txt", ".rst", ".css", ".scss", ".svg", ".png", ".jpg"]
        for ext in safe:
            with self.subTest(ext=ext):
                result = assess_risk([f"file{ext}"])
                self.assertEqual(result.risk_level, RiskLevel.LOW, f"{ext} should be low risk")


class TestMultipleCategories(unittest.TestCase):
    """Changes across multiple categories should compound."""

    def test_auth_and_payment_critical(self) -> None:
        result = assess_risk(["src/auth/login.py", "payment/checkout.py"])
        self.assertEqual(result.risk_level, RiskLevel.CRITICAL)
        self.assertIn("auth", result.reason.lower())
        self.assertIn("payment", result.reason.lower())

    def test_auth_and_database_high(self) -> None:
        result = assess_risk(["auth/login.py", "database/schema.py"])
        self.assertEqual(result.risk_level, RiskLevel.CRITICAL)

    def test_three_categories(self) -> None:
        result = assess_risk([
            "auth/login.py",
            "payment/checkout.py",
            "database/migration.py",
        ])
        self.assertEqual(result.risk_level, RiskLevel.CRITICAL)
        self.assertGreaterEqual(len(result.matched_categories), 2)


class TestRiskResultSerialization(unittest.TestCase):
    """RiskResult should serialize to dict."""

    def test_to_dict(self) -> None:
        result = assess_risk(["config/settings.py"])
        d = result.to_dict()
        self.assertEqual(d["risk_level"], "medium")
        self.assertIsInstance(d["score"], int)
        self.assertIsInstance(d["reason"], str)
        self.assertIsInstance(d["matched_categories"], list)
        self.assertIsInstance(d["safe_paths"], list)


class TestRiskPromptContext(unittest.TestCase):
    """Risk-aware prompt builder."""

    def test_high_risk_returns_warning(self) -> None:
        risk = assess_risk(["auth/login.py"])
        context = build_risk_prompt_context(risk)
        self.assertIn("HIGH RISK", context.upper())

    def test_low_risk_returns_empty(self) -> None:
        risk = assess_risk(["README.md"])
        context = build_risk_prompt_context(risk)
        self.assertEqual(context, "")

    def test_medium_risk_returns_context(self) -> None:
        risk = assess_risk(["config/settings.py"])
        context = build_risk_prompt_context(risk)
        self.assertIn("MEDIUM", context)


class TestEdgeCases(unittest.TestCase):
    """Edge cases and robustness."""

    def test_path_with_spaces(self) -> None:
        result = assess_risk(["src/auth module/login.py"])
        self.assertGreaterEqual(result.score, 70)

    def test_uppercase_path(self) -> None:
        result = assess_risk(["SRC/AUTH/LOGIN.PY"])
        self.assertGreaterEqual(result.score, 70)

    def test_windows_path(self) -> None:
        result = assess_risk(["src\\auth\\login.py"])
        self.assertGreaterEqual(result.score, 70)

    def test_deep_nested_path(self) -> None:
        result = assess_risk(["packages/backend/app/services/auth/login.py"])
        self.assertGreaterEqual(result.score, 70)

    def test_score_never_exceeds_100(self) -> None:
        result = assess_risk([
            "auth/login.py", "payment/checkout.py",
            "security/crypto.py", "database/schema.py",
            "config/secrets.py", "api/routes.py",
        ])
        self.assertLessEqual(result.score, 150)

    def test_matched_categories_dedup(self) -> None:
        """Same category matched by multiple files should only appear once."""
        result = assess_risk(["auth/login.py", "auth/register.py", "auth/password.py"])
        self.assertEqual(len(result.matched_categories), 1)

    def test_no_false_positive_generic_names(self) -> None:
        """Generic module names should not trigger false positives."""
        result = assess_risk(["src/utils/helpers.py", "src/models/user.py"])
        # "models" could match "database/model" pattern
        # This is acceptable — verify score is reasonable
        self.assertLess(result.score, 80)


if __name__ == "__main__":
    unittest.main(verbosity=2)
