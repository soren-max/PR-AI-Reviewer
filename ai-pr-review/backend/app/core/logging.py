"""
Structured JSON logging configuration.
Request ID is injected via contextvars for traceability.
"""
import json
import logging
import sys
from contextvars import ContextVar

from app.core.config import settings

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIDFilter(logging.Filter):
    """Inject request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        return True


class JSONFormatter(logging.Formatter):
    """Output logs as single-line JSON for structured ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%03dZ"),
            "level": record.levelname,
            "name": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        # Sensitive data masking
        msg = log_entry.get("message", "")
        for secret_key in ["DEEPSEEK_API_KEY", "GITHUB_TOKEN"]:
            if secret_key in msg:
                log_entry["message"] = _mask_secret(msg, secret_key)
        return json.dumps(log_entry, ensure_ascii=False)


def _mask_secret(msg: str, key: str) -> str:
    """Mask all but last 4 chars of a secret value in a log message."""
    import re
    pattern = rf"{key}=([^\s&]+)"
    def replacer(m: re.Match) -> str:
        val = m.group(1)
        return f"{key}={val[:1]}***{val[-4:]}" if len(val) > 5 else f"{key}=***"
    return re.sub(pattern, replacer, msg)


def setup_logging(name: str | None = None) -> logging.Logger:
    """Configure the root logger with JSON formatting."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(RequestIDFilter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # Suppress noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logging.getLogger(name or __name__)
