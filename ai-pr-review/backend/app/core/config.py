"""
Application configuration via Pydantic Settings.
All environment variables are validated at startup.
"""
from enum import Enum
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    QWEN = "qwen"


class Settings(BaseSettings):
    """Centralised configuration, loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    APP_NAME: str = "ai-pr-review"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/reviews.db"

    # --- GitHub ---
    GITHUB_TOKEN: str = ""
    GITHUB_API_BASE: str = "https://api.github.com"
    GITHUB_REQUEST_TIMEOUT: int = 30

    # --- LLM Provider Selection ---
    LLM_PROVIDER: LLMProvider = LLMProvider.DEEPSEEK

    # --- DeepSeek ---
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_MAX_TOKENS: int = 8192
    DEEPSEEK_TEMPERATURE: float = 0.1
    DEEPSEEK_TIMEOUT: int = 120

    # --- OpenAI ---
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_MAX_TOKENS: int = 8192
    OPENAI_TEMPERATURE: float = 0.1
    OPENAI_TIMEOUT: int = 120

    # --- Qwen (Alibaba Cloud) ---
    QWEN_API_KEY: str = ""
    QWEN_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-max"
    QWEN_MAX_TOKENS: int = 8192
    QWEN_TEMPERATURE: float = 0.1
    QWEN_TIMEOUT: int = 120

    # --- Rate Limiting ---
    RATE_LIMIT_PER_MINUTE: int = 30

    # --- Task ---
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_SECONDS: float = 2.0

    # --- Prompt ---
    MAX_DIFF_SIZE_BYTES: int = 500_000
    MAX_FILES_PER_REVIEW: int = 20
    MAX_COMMENTS_PER_REVIEW: int = 30

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    def get_active_provider_config(self) -> dict:
        """Return the active LLM provider's configuration dict."""
        provider = self.LLM_PROVIDER
        if provider == LLMProvider.DEEPSEEK:
            return {
                "api_key": self.DEEPSEEK_API_KEY,
                "api_base": self.DEEPSEEK_API_BASE,
                "model": self.DEEPSEEK_MODEL,
                "max_tokens": self.DEEPSEEK_MAX_TOKENS,
                "temperature": self.DEEPSEEK_TEMPERATURE,
                "timeout": self.DEEPSEEK_TIMEOUT,
            }
        elif provider == LLMProvider.OPENAI:
            return {
                "api_key": self.OPENAI_API_KEY,
                "api_base": self.OPENAI_API_BASE,
                "model": self.OPENAI_MODEL,
                "max_tokens": self.OPENAI_MAX_TOKENS,
                "temperature": self.OPENAI_TEMPERATURE,
                "timeout": self.OPENAI_TIMEOUT,
            }
        elif provider == LLMProvider.QWEN:
            return {
                "api_key": self.QWEN_API_KEY,
                "api_base": self.QWEN_API_BASE,
                "model": self.QWEN_MODEL,
                "max_tokens": self.QWEN_MAX_TOKENS,
                "temperature": self.QWEN_TEMPERATURE,
                "timeout": self.QWEN_TIMEOUT,
            }
        raise ValueError(f"Unknown LLM provider: {provider}")


settings = Settings()
