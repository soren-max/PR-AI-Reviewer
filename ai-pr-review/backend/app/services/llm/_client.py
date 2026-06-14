"""
LLM client — communicates with DeepSeek V4 Pro API.
Implements retry with exponential backoff.
"""
import asyncio
import json
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import LLMAPIError
from app.core.logging import setup_logging

logger = setup_logging(__name__)


@dataclass
class LLMResponse:
    """Structured response from the LLM."""

    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class LLMClient:
    """
    Asynchronous client for DeepSeek Chat Completions API.

    Features:
    - 3x retry with exponential backoff
    - 120s timeout for large diffs
    - Token usage tracking
    """

    def __init__(self):
        self._api_base = settings.DEEPSEEK_API_BASE.rstrip("/")
        self._api_key = settings.DEEPSEEK_API_KEY
        self._model = settings.DEEPSEEK_MODEL
        self._max_tokens = settings.DEEPSEEK_MAX_TOKENS
        self._temperature = settings.DEEPSEEK_TEMPERATURE
        self._max_retries = settings.MAX_RETRIES
        self._backoff = settings.RETRY_BACKOFF_SECONDS
        self._timeout = settings.DEEPSEEK_TIMEOUT

        if not self._api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set")

        self._client = httpx.AsyncClient(
            base_url=self._api_base,
            timeout=self._timeout,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        """
        Send a chat completion request with retry logic.

        Args:
            system_prompt: System-level instructions for the LLM.
            user_prompt: The PR diff and review request.

        Returns:
            LLMResponse with parsed content and token usage.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        last_error: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._client.post(
                    "/chat/completions",
                    json={
                        "model": self._model,
                        "messages": messages,
                        "max_tokens": self._max_tokens,
                        "temperature": self._temperature,
                        "response_format": {"type": "json_object"},
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    choice = data["choices"][0]
                    usage = data.get("usage", {})

                    content = choice["message"]["content"]

                    return LLMResponse(
                        content=content,
                        input_tokens=usage.get("prompt_tokens", 0),
                        output_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                    )

                elif response.status_code == 401:
                    raise LLMAPIError("DeepSeek API authentication failed — check API key")
                elif response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", self._backoff * (2 ** (attempt - 1))))
                    logger.warning("LLM rate limited, retrying after %ss (attempt %d/%d)", retry_after, attempt, self._max_retries)
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    logger.error("LLM API error: %s %s", response.status_code, response.text[:200])
                    if attempt == self._max_retries:
                        raise LLMAPIError(f"DeepSeek API returned {response.status_code}")
                    await asyncio.sleep(self._backoff * (2 ** (attempt - 1)))

            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning("LLM request timed out (attempt %d/%d)", attempt, self._max_retries)
                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff * (2 ** (attempt - 1)))
                continue

            except httpx.RequestError as exc:
                last_error = exc
                logger.error("LLM request error: %s", str(exc))
                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff * (2 ** (attempt - 1)))
                continue

        raise LLMAPIError(
            f"LLM API call failed after {self._max_retries} retries"
        ) from last_error

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
