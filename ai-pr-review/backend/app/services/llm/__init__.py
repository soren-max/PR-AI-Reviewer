"""
LLM Service Layer — provider-agnostic code review engine.

Provides a unified ``review_pr()`` interface that works across DeepSeek,
OpenAI, and Qwen.  New providers implement ``BaseLLMService``.

Typical usage::

    from app.services.llm import get_llm_service

    service = get_llm_service()
    result = await service.review_pr(
        pr_title="Fix login redirect",
        pr_description="Updated callback URL",
        diff="diff --git a/src/auth.py...",
    )

**Backwards compatibility**::
    ``LLMClient`` and ``LLMResponse`` are re-exported from the old
    ``app/services/llm.py`` module, which has been moved to
    ``app/services/llm/_client.py``.
"""

from app.services.llm.base import BaseLLMService, LLMReviewResponse, ReviewSection
from app.services.llm.factory import get_llm_service, get_provider_names

# Backwards compatibility — re-export the old LLMClient/LLMResponse
from app.services.llm._client import LLMClient, LLMResponse  # noqa: F401

__all__ = [
    # New service interface
    "BaseLLMService",
    "LLMReviewResponse",
    "ReviewSection",
    "get_llm_service",
    "get_provider_names",
    # Backwards compat
    "LLMClient",
    "LLMResponse",
]
