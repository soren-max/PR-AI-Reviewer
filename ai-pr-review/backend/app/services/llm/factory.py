"""
LLM Service factory — selects the right provider based on configuration.

Usage::

    from app.services.llm import get_llm_service

    # Returns DeepSeekService, OpenAIService, or QwenService
    # depending on settings.LLM_PROVIDER
    service = get_llm_service()
    result = await service.review_pr(...)
"""
from __future__ import annotations

from typing import Type

from app.core.config import LLMProvider, settings
from app.core.logging import setup_logging
from app.services.llm.base import BaseLLMService

logger = setup_logging(__name__)

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

_provider_registry: dict[LLMProvider, Type[BaseLLMService]] = {}


def register_provider(provider: LLMProvider, service_class: Type[BaseLLMService]) -> None:
    """Register an LLM provider implementation.

    Called at module import time by each provider.
    """
    _provider_registry[provider] = service_class
    logger.debug("Registered LLM provider: %s -> %s", provider.value, service_class.__name__)


# ---------------------------------------------------------------------------
# Late imports to register providers
# ---------------------------------------------------------------------------

# Importing these modules triggers register_provider() calls at module level.
# This is done lazily so the registry is populated before get_llm_service().
_imported = False


def _import_providers() -> None:
    """Trigger registration of all available providers."""
    global _imported
    if _imported:
        return
    from app.services.llm.deepseek import DeepSeekService  # noqa: F401
    from app.services.llm.openai import OpenAIService      # noqa: F401
    from app.services.llm.qwen import QwenService          # noqa: F401
    _imported = True


# ---------------------------------------------------------------------------
# Registration calls
# ---------------------------------------------------------------------------

# These execute when the module is first imported.
# We do them after the import functions so the classes are available.

def _init_registry() -> None:
    """Populate the provider registry with built-in implementations."""
    from app.services.llm.deepseek import DeepSeekService
    from app.services.llm.openai import OpenAIService
    from app.services.llm.qwen import QwenService

    register_provider(LLMProvider.DEEPSEEK, DeepSeekService)
    register_provider(LLMProvider.OPENAI, OpenAIService)
    register_provider(LLMProvider.QWEN, QwenService)


_init_registry()

# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def get_llm_service(
    provider: LLMProvider | None = None,
    **kwargs,
) -> BaseLLMService:
    """Return an LLM service instance for the given (or configured) provider.

    Args:
        provider: The LLM provider to use.  Defaults to
                  ``settings.LLM_PROVIDER``.
        **kwargs: Additional keyword arguments passed to the provider's
                  constructor (e.g. ``api_key``, ``model``).

    Returns:
        An instance of :class:`BaseLLMService`.

    Raises:
        ValueError: If the provider is not registered.

    Example::

        # Default provider (from settings.LLM_PROVIDER)
        service = get_llm_service()

        # Explicit provider
        service = get_llm_service(LLMProvider.OPENAI)

        # Override specific parameters
        service = get_llm_service(
            LLMProvider.DEEPSEEK,
            model="deepseek-chat",
            temperature=0.0,
        )
    """
    provider = provider or settings.LLM_PROVIDER

    _import_providers()

    service_class = _provider_registry.get(provider)
    if not service_class:
        raise ValueError(
            f"Unknown LLM provider: {provider.value!r}. "
            f"Available: {list(_provider_registry.keys())}. "
            f"Check that the provider module is imported."
        )

    # If user passed constructor kwargs, use them; otherwise use config
    if kwargs:
        return service_class(**kwargs)

    return service_class()


def get_provider_names() -> list[str]:
    """Return the list of registered provider names.

    Useful for API discovery or configuration UIs.
    """
    _import_providers()
    return [p.value for p in _provider_registry]
