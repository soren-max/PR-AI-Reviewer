"""
OpenAI provider implementation.

Uses the OpenAI Chat Completions API.  Configuration is read from
``settings.OPENAI_*``.  This provider is functionally identical to
DeepSeek at the API level (both are OpenAI-compatible), but has
separate config keys and model defaults.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import LLMAPIError
from app.core.logging import setup_logging
from app.services.llm.base import BaseLLMService, LLMReviewResponse
from app.services.llm.prompts import build_review_prompt

logger = setup_logging(__name__)


class OpenAIService(BaseLLMService):
    """LLM service using OpenAI's Chat Completions API.

    Supports GPT-4, GPT-4-turbo, GPT-3.5-turbo, etc.
    Configuration is read from ``settings.OPENAI_*``.
    """

    PROVIDER = "openai"

    def __init__(
        self,
        api_key: str = "",
        api_base: str = "",
        model: str = "",
        max_tokens: int = 8192,
        temperature: float = 0.1,
        timeout: int = 120,
        max_retries: int = 0,
    ) -> None:
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._api_base = (api_base or settings.OPENAI_API_BASE).rstrip("/")
        self._model = model or settings.OPENAI_MODEL
        self._max_tokens = max_tokens or settings.OPENAI_MAX_TOKENS
        self._temperature = temperature if temperature is not None else settings.OPENAI_TEMPERATURE
        self._timeout = timeout or settings.OPENAI_TIMEOUT
        self._max_retries = max_retries or settings.MAX_RETRIES
        self._backoff = settings.RETRY_BACKOFF_SECONDS

        if not self._api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Set it in your .env file or environment variables."
            )

        self._client = httpx.AsyncClient(
            base_url=self._api_base,
            timeout=self._timeout,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return self.PROVIDER

    @property
    def model_name(self) -> str:
        return self._model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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
        system_prompt, user_prompt = build_review_prompt(
            pr_title=pr_title,
            pr_description=pr_description,
            diff=diff,
            language=language,
            risk_context=risk_context,
        )

        try:
            raw_markdown, input_tokens, output_tokens = await self.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            logger.exception("OpenAI review_pr failed")
            return LLMReviewResponse(
                raw_markdown="",
                error=f"{type(exc).__name__}: {exc}",
                model=self._model,
            )

        return LLMReviewResponse(
            raw_markdown=raw_markdown,
            summary=_extract_section(raw_markdown, "PR Summary"),
            changed_modules=_extract_section(raw_markdown, "Changed Modules"),
            potential_risks=_extract_section(raw_markdown, "Potential Risks"),
            bug_suggestions=_extract_section(raw_markdown, "Bug Suggestions"),
            performance_suggestions=_extract_section(raw_markdown, "Performance Suggestions"),
            security_suggestions=_extract_section(raw_markdown, "Security Suggestions"),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            model=self._model,
        )

    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> tuple[str, int, int]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        request_body = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens or self._max_tokens,
            "temperature": temperature if temperature is not None else self._temperature,
        }

        last_exception: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._client.post(
                    "/chat/completions",
                    json=request_body,
                )

                if response.status_code == 200:
                    data = response.json()
                    choice = data["choices"][0]
                    usage = data.get("usage", {})

                    content: str = choice["message"]["content"]
                    input_tokens = usage.get("prompt_tokens", 0)
                    output_tokens = usage.get("completion_tokens", 0)

                    logger.info(
                        "OpenAI API success: %d in / %d out tokens (attempt %d/%d)",
                        input_tokens, output_tokens, attempt, self._max_retries,
                    )
                    return content, input_tokens, output_tokens

                elif response.status_code == 401:
                    raise LLMAPIError(
                        "OpenAI API authentication failed — check OPENAI_API_KEY"
                    )
                elif response.status_code == 429:
                    retry_after = float(
                        response.headers.get("Retry-After", self._backoff * (2 ** (attempt - 1)))
                    )
                    logger.warning(
                        "OpenAI rate limited, retrying after %.1fs (attempt %d/%d)",
                        retry_after, attempt, self._max_retries,
                    )
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    logger.error(
                        "OpenAI API error: HTTP %d: %s",
                        response.status_code, response.text[:300],
                    )
                    if attempt == self._max_retries:
                        raise LLMAPIError(
                            f"OpenAI API returned HTTP {response.status_code}"
                        )
                    await asyncio.sleep(self._backoff * (2 ** (attempt - 1)))

            except httpx.TimeoutException as exc:
                last_exception = exc
                logger.warning(
                    "OpenAI request timed out (attempt %d/%d)",
                    attempt, self._max_retries,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff * (2 ** (attempt - 1)))
                    continue
                raise LLMAPIError(
                    f"OpenAI API timed out after {self._max_retries} retries"
                ) from exc

            except httpx.RequestError as exc:
                last_exception = exc
                logger.error(
                    "OpenAI request error: %s (attempt %d/%d)",
                    exc, attempt, self._max_retries,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff * (2 ** (attempt - 1)))
                    continue
                raise LLMAPIError(
                    f"OpenAI API request failed after {self._max_retries} retries: {exc}"
                ) from exc

        raise LLMAPIError(
            f"OpenAI API call failed after {self._max_retries} retries"
        ) from last_exception

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> OpenAIService:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()


def _extract_section(markdown: str, section_title: str) -> str:
    """Extract a named section from a markdown document."""
    import re

    pattern = re.compile(
        rf"^#{{2,3}}\s+\S*\s*{re.escape(section_title)}\s*$",
        re.MULTILINE,
    )
    match = pattern.search(markdown)
    if not match:
        return ""

    start = match.end()
    next_heading = re.search(r"^##[\s#]", markdown[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(markdown)

    return markdown[start:end].strip()
