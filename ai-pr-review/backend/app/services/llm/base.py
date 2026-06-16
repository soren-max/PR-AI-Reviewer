"""
Abstract base class for all LLM provider implementations.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ReviewSection:
    """A parsed section of the review output."""

    title: str
    body: str
    raw: str  # Original markdown of this section


@dataclass
class LLMReviewResponse:
    """Structured result from a PR review call.

    Attributes:
        raw_markdown: The complete markdown output from the LLM.
        summary: Extracted PR Summary section.
        changed_modules: Extracted Changed Modules section.
        potential_risks: Extracted Potential Risks section.
        bug_suggestions: Extracted Bug Suggestions section.
        performance_suggestions: Extracted Performance Suggestions section.
        security_suggestions: Extracted Security Suggestions section.
        input_tokens: Number of prompt tokens consumed.
        output_tokens: Number of completion tokens generated.
        total_tokens: Total tokens used.
        model: Model identifier used for this review.
    """

    raw_markdown: str
    summary: str = ""
    changed_modules: str = ""
    potential_risks: str = ""
    bug_suggestions: str = ""
    performance_suggestions: str = ""
    security_suggestions: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    error: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        """``True`` if all major sections were populated."""
        return all([
            self.summary,
            self.changed_modules,
            self.potential_risks,
        ])

    @property
    def token_cost_estimate(self) -> float:
        """Rough cost estimate in USD (using ~$2/M input, ~$8/M output)."""
        return (self.input_tokens * 2 + self.output_tokens * 8) / 1_000_000


class BaseLLMService(ABC):
    """Abstract interface for LLM-based PR review services.

    All providers (DeepSeek, OpenAI, Qwen) implement this interface.
    Callers should obtain a service instance via :func:`get_llm_service`
    and never instantiate a provider directly.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name (e.g. ``"deepseek"``, ``"openai"``)."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier used for completions (e.g. ``"deepseek-chat"``)."""
        ...

    @abstractmethod
    async def review_pr(
        self,
        pr_title: str,
        pr_description: str,
        diff: str,
        language: str = "zh",
        risk_context: str = "",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMReviewResponse:
        """Perform a full code review on a Pull Request diff.

        Args:
            pr_title: The title of the Pull Request.
            pr_description: The description / body of the Pull Request.
            diff: The unified diff output of the PR (changed files with patches).
            language: Output language — ``"zh"`` (Chinese, default) or
                      ``"en"`` (English).
            risk_context: Optional deterministic risk hints from file/path analysis.
            max_tokens: Maximum completion tokens (overrides config default).
            temperature: Sampling temperature (overrides config default).

        Returns:
            An :class:`LLMReviewResponse` containing the structured review
            output, token usage, and metadata.

        Raises:
            LLMAPIError: If the API call fails after all retries.
            ProviderAuthError: If the API key is missing or invalid.
        """
        ...

    @abstractmethod
    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> tuple[str, int, int]:
        """Low-level chat completion — send raw prompts, get raw response.

        This is the primitive used by :meth:`review_pr`.  Exposed for
        advanced use cases (e.g. chunked analysis of very large diffs).

        Args:
            system_prompt: System-level instructions.
            user_prompt: User message content.
            max_tokens: Max completion tokens.
            temperature: Sampling temperature.

        Returns:
            Tuple of ``(content_text, input_tokens, output_tokens)``.

        Raises:
            LLMAPIError: On API failure.
        """
        ...

    async def close(self) -> None:
        """Release any underlying HTTP connections."""
        ...

    async def __aenter__(self) -> BaseLLMService:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
