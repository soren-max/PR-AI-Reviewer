"""
Tests for the backend risk_analyzer adapter.

Verifies the adapter correctly wraps the root risk engine
and produces equivalent results.
"""
from __future__ import annotations

import sys
import unittest

# Add the backend directory to sys.path so we can import the adapter
sys.path.insert(0, "ai-pr-review/backend")

from app.services.review.risk_analyzer import (
    assess_risk,
    build_risk_prompt_context,
    RiskLevel,
)
from risk.engine import assess_risk as root_assess_risk


class TestAdapterParity(unittest.TestCase):
    """Backend adapter must produce same results as root engine."""

    def test_single_auth_file_returns_high(self) -> None:
        result = assess_risk(["src/auth/login.py"])
        self.assertEqual(result.risk_level, RiskLevel.HIGH)

    def test_multiple_categories_returns_critical(self) -> None:
        result = assess_risk(["auth/login.py", "payment/checkout.py"])
        self.assertEqual(result.risk_level, RiskLevel.CRITICAL)

    def test_safe_path_returns_low(self) -> None:
        result = assess_risk(["README.md"])
        self.assertEqual(result.risk_level, RiskLevel.LOW)

    def test_empty_list_returns_low(self) -> None:
        result = assess_risk([])
        self.assertEqual(result.risk_level, RiskLevel.LOW)
        self.assertEqual(result.score, 0)

    def test_adapter_matches_root_engine(self) -> None:
        """Adapter must produce identical results to root engine for all scenarios."""
        scenarios = [
            ["src/auth/login.py"],
            ["payment/checkout.py"],
            ["database/migrations/001_init.py"],
            ["config/settings.py"],
            ["README.md"],
            ["tests/test_thing.py"],
            ["src/auth/login.py", "payment/checkout.py"],
            [],
        ]
        for files in scenarios:
            with self.subTest(files=files):
                root_result = root_assess_risk(files)
                adapter_result = assess_risk(files)
                self.assertEqual(
                    root_result.risk_level, adapter_result.risk_level,
                    f"Risk level mismatch for {files}"
                )
                self.assertEqual(
                    root_result.score, adapter_result.score,
                    f"Score mismatch for {files}"
                )
                self.assertEqual(
                    root_result.matched_categories, adapter_result.matched_categories,
                    f"Categories mismatch for {files}"
                )

    def test_prompt_context_high_risk(self) -> None:
        risk = assess_risk(["auth/login.py"])
        ctx = build_risk_prompt_context(risk)
        self.assertIn("HIGH RISK", ctx.upper())

    def test_prompt_context_low_risk_empty(self) -> None:
        risk = assess_risk(["README.md"])
        ctx = build_risk_prompt_context(risk)
        self.assertEqual(ctx, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
