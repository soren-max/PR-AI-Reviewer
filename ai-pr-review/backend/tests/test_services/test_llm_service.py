"""
Tests for the LLM Service Layer — base class, provider implementations,
factory, and prompt builder.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.core.config import LLMProvider
from app.services.llm import (
    BaseLLMService,
    LLMReviewResponse,
    ReviewSection,
    get_llm_service,
    get_provider_names,
)
from app.services.llm.prompts import build_review_prompt


# ===========================================================================
# Base class tests
# ===========================================================================

class TestLLMReviewResponse(unittest.TestCase):
    """LLMReviewResponse data class behaviour."""

    def test_empty_response(self) -> None:
        resp = LLMReviewResponse(raw_markdown="")
        self.assertEqual(resp.raw_markdown, "")
        self.assertIsNone(resp.error)
        self.assertFalse(resp.is_complete)

    def test_complete_response(self) -> None:
        resp = LLMReviewResponse(
            raw_markdown="full markdown",
            summary="Good PR",
            changed_modules="src/auth.py",
            potential_risks="None",
        )
        self.assertTrue(resp.is_complete)

    def test_incomplete_response(self) -> None:
        resp = LLMReviewResponse(
            raw_markdown="partial",
            summary="Good PR",
            # missing changed_modules and potential_risks
        )
        self.assertFalse(resp.is_complete)

    def test_token_cost_estimate(self) -> None:
        resp = LLMReviewResponse(
            raw_markdown="",
            input_tokens=1000,
            output_tokens=500,
        )
        # (1000 * 2 + 500 * 8) / 1_000_000 = 0.006
        self.assertAlmostEqual(resp.token_cost_estimate, 0.006)

    def test_error_response(self) -> None:
        resp = LLMReviewResponse(
            raw_markdown="",
            error="APIError: authentication failed",
        )
        self.assertEqual(resp.error, "APIError: authentication failed")


class TestReviewSection(unittest.TestCase):
    def test_section_creation(self) -> None:
        section = ReviewSection(
            title="Bug Suggestions",
            body="1. src/auth.py:42 — Missing null check",
            raw="## 🐛 Bug Suggestions\n\n1. src/auth.py:42 — Missing null check",
        )
        self.assertEqual(section.title, "Bug Suggestions")
        self.assertIn("Missing null check", section.body)


# ===========================================================================
# Prompt builder tests
# ===========================================================================

class TestBuildReviewPrompt(unittest.TestCase):
    def test_basic_prompt(self) -> None:
        system, user = build_review_prompt(
            pr_title="Fix login bug",
            pr_description="Fixed the OAuth redirect issue",
            diff="diff --git a/src/auth.py b/src/auth.py\n@@ -1,3 +1,5 @@\n+fix",
            language="en",
        )
        self.assertIsInstance(system, str)
        self.assertIsInstance(user, str)
        self.assertGreater(len(system), 50)
        self.assertGreater(len(user), 50)
        self.assertIn("Fix login bug", user)
        self.assertIn("OAuth redirect", user)
        self.assertIn("diff --git", user)

    def test_chinese_language(self) -> None:
        system, user = build_review_prompt(
            pr_title="修复登录问题",
            pr_description="修复了 OAuth 重定向问题",
            diff="diff --git a/src/auth.py b/src/auth.py",
            language="zh",
        )
        self.assertIn("中文", system + user)

    def test_empty_description(self) -> None:
        system, user = build_review_prompt(
            pr_title="Test",
            pr_description="",
            diff="diff",
        )
        self.assertIn("No description", user)

    def test_risk_context_is_included(self) -> None:
        system, user = build_review_prompt(
            pr_title="Auth change",
            pr_description="Updates auth middleware",
            diff="diff",
            risk_context="[HIGH RISK] Authentication code changed.",
        )
        self.assertIn("Risk Context", user)
        self.assertIn("Authentication code changed", user)

    def test_diff_truncation(self) -> None:
        """Very large diffs should be truncated."""
        large_diff = "x" * 600_000  # > MAX_DIFF_SIZE_BYTES (500k)
        system, user = build_review_prompt(
            pr_title="Large PR",
            pr_description="",
            diff=large_diff,
        )
        # The diff should be truncated
        self.assertLess(len(user), 600_000 + 500)  # some overhead for prefix/suffix
        self.assertIn("truncated", user)


# ===========================================================================
# Factory tests
# ===========================================================================

class TestGetLLMService(unittest.TestCase):
    def test_default_provider(self) -> None:
        """Should return a service instance without error."""
        service = get_llm_service()
        self.assertIsInstance(service, BaseLLMService)
        self.assertIn(service.provider_name, ["deepseek", "openai", "qwen"])

    def test_explicit_deepseek(self) -> None:
        """Should return DeepSeekService when specified."""
        service = get_llm_service(LLMProvider.DEEPSEEK)
        self.assertEqual(service.provider_name, "deepseek")

    def test_explicit_openai(self) -> None:
        """Should return OpenAIService when specified."""
        service = get_llm_service(LLMProvider.OPENAI, api_key="sk-test")
        self.assertEqual(service.provider_name, "openai")

    def test_explicit_qwen(self) -> None:
        """Should return QwenService when specified."""
        service = get_llm_service(LLMProvider.QWEN, api_key="sk-test")
        self.assertEqual(service.provider_name, "qwen")

    def test_provider_list(self) -> None:
        """Should list all registered providers."""
        names = get_provider_names()
        self.assertIn("deepseek", names)
        self.assertIn("openai", names)
        self.assertIn("qwen", names)

    def test_service_is_async_context_manager(self) -> None:
        """Service should support 'async with'."""
        service = get_llm_service()
        self.assertTrue(hasattr(service, "__aenter__"))
        self.assertTrue(hasattr(service, "__aexit__"))


# ===========================================================================
# Provider integration tests (mocked API)
# ===========================================================================

class TestDeepSeekService(unittest.TestCase):
    """Tests for DeepSeekService with mocked HTTP client."""

    def setUp(self) -> None:
        from app.services.llm.deepseek import DeepSeekService
        self.service = DeepSeekService(
            api_key="sk-test",
            max_retries=0,  # Don't retry in tests
        )

    def test_provider_name(self) -> None:
        self.assertEqual(self.service.provider_name, "deepseek")

    def test_model_name(self) -> None:
        self.assertIn("deepseek", self.service.model_name)

    def _make_mock_post(self, status_code: int = 200, json_data: dict | None = None):
        """Create an async mock for ``self._client.post``.

        Returns an async function that when awaited returns a mock response
        with the given status code and json data.
        """
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json = MagicMock(return_value=json_data or {})

        async def mock_post(*args, **kwargs):
            return mock_response

        return mock_post

    async def _mock_successful_review(self) -> LLMReviewResponse:
        """Helper: mock a successful API response and call review_pr."""
        mock_content = """## 📋 PR Summary

Clean change that fixes the login redirect.

## 🔧 Changed Modules

- `src/auth.py` — Added redirect validation

## ⚠️ Potential Risks

None identified.

## 🐛 Bug Suggestions

1. **`src/auth.py:42`** 🟠 Major — Missing null check on redirect URL

## ⚡ Performance Suggestions

None identified.

## 🔒 Security Suggestions

None identified."""

        json_data = {
            "choices": [{"message": {"content": mock_content}}],
            "usage": {"prompt_tokens": 450, "completion_tokens": 180},
        }

        with patch.object(
            self.service._client, "post",
            side_effect=self._make_mock_post(200, json_data),
        ):
            result = await self.service.review_pr(
                pr_title="Fix login redirect",
                pr_description="Fixed the callback URL",
                diff="diff --git a/src/auth.py\n@@ -1,3 +1,8 @@\n+validated",
            )

        return result

    def test_review_pr_success(self) -> None:
        """A mocked successful API call should return a structured review."""
        import asyncio
        result = asyncio.run(self._mock_successful_review())

        self.assertIsInstance(result, LLMReviewResponse)
        self.assertIn("PR Summary", result.raw_markdown)
        self.assertIn("login redirect", result.summary)
        self.assertIn("src/auth.py", result.changed_modules)
        self.assertEqual(result.input_tokens, 450)
        self.assertEqual(result.output_tokens, 180)
        self.assertEqual(result.total_tokens, 630)
        self.assertIsNone(result.error)

    def test_review_pr_api_error(self) -> None:
        """An API error should return a response with error populated."""
        import asyncio

        async def mock_post_error(*args, **kwargs):
            raise Exception("Connection refused")

        with patch.object(
            self.service._client, "post",
            side_effect=mock_post_error,
        ):
            result = asyncio.run(
                self.service.review_pr("T", "D", "diff"),
            )

        self.assertIsNotNone(result.error)
        self.assertIn("Connection refused", result.error)


class TestOpenAIService(unittest.TestCase):
    def setUp(self) -> None:
        from app.services.llm.openai import OpenAIService
        self.service = OpenAIService(
            api_key="sk-test",
            max_retries=0,
        )

    def test_provider_name(self) -> None:
        self.assertEqual(self.service.provider_name, "openai")

    def test_model_name(self) -> None:
        self.assertIn("gpt", self.service.model_name)


class TestQwenService(unittest.TestCase):
    def setUp(self) -> None:
        from app.services.llm.qwen import QwenService
        self.service = QwenService(
            api_key="sk-test",
            max_retries=0,
        )

    def test_provider_name(self) -> None:
        self.assertEqual(self.service.provider_name, "qwen")

    def test_model_name(self) -> None:
        self.assertIn("qwen", self.service.model_name)


# ===========================================================================
# Abstract base: cannot instantiate directly
# ===========================================================================

class TestBaseClass(unittest.TestCase):
    def test_cannot_instantiate_abstract(self) -> None:
        """BaseLLMService should not be instantiable directly."""
        with self.assertRaises(TypeError):
            BaseLLMService()  # type: ignore[abstract]


if __name__ == "__main__":
    unittest.main(verbosity=2)
