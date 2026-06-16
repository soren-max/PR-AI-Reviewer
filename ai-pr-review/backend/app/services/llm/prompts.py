"""
Prompt construction for PR review.

Builds structured system + user prompts from PR metadata and diff,
loading the PR Review Agent system prompt from the prompts directory.
"""
from __future__ import annotations

import os
from typing import Tuple

from app.core.config import settings
from app.core.logging import setup_logging

logger = setup_logging(__name__)

# Path to the PR Review Agent system prompt
_PROMPT_FILE = os.path.join(
    os.path.dirname(__file__),        # backend/app/services/llm/
    "..", "..", "..", "..",          # up to project root
    "prompts", "pr_review_agent.md",
)
_PROMPT_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), _PROMPT_FILE))
# Actually let's use an absolute path from the project root
# __file__ = backend/app/services/llm/prompts.py
# Go up: llm/ -> services/ -> app/ -> backend/ -> ai-pr-review/ -> project root
_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
_PROMPT_PATH = os.path.join(_PROJECT_ROOT, "prompts", "pr_review_agent.md")


def _load_system_prompt() -> str:
    """Load the PR Review Agent system prompt from file.

    Falls back to a built-in minimal prompt if the file cannot be read.
    """
    try:
        with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning(
            "PR Review Agent prompt not found at %s, using built-in fallback",
            _PROMPT_PATH,
        )
        return _FALLBACK_SYSTEM_PROMPT
    except Exception as exc:
        logger.error("Failed to read prompt file: %s", exc)
        return _FALLBACK_SYSTEM_PROMPT


_FALLBACK_SYSTEM_PROMPT = """You are a Staff Software Engineer conducting a code review.

Review the Pull Request diff below and produce a structured review with these sections:
## 📋 PR Summary
## 🔧 Changed Modules
## ⚠️ Potential Risks
## 🐛 Bug Suggestions
## ⚡ Performance Suggestions
## 🔒 Security Suggestions

For bugs/performance/security, include: file path, line number, severity (🔴 Critical/🟠 Major/🟡 Minor), explanation, and fix suggestion.

Output in Markdown format only."""


def build_review_prompt(
    pr_title: str,
    pr_description: str,
    diff: str,
    language: str = "zh",
    risk_context: str = "",
) -> Tuple[str, str]:
    """Build the system and user prompts for a PR review.

    Args:
        pr_title: Pull Request title.
        pr_description: Pull Request description / body.
        diff: Unified diff output of the PR.
        language: Output language (``"zh"`` or ``"en"``).
        risk_context: Optional deterministic risk hints from pre-LLM analysis.

    Returns:
        Tuple of ``(system_prompt, user_prompt)``.
    """
    system_prompt = _load_system_prompt()

    # Limit diff size to prevent token overflow
    max_diff_chars = settings.MAX_DIFF_SIZE_BYTES
    if len(diff) > max_diff_chars:
        truncated = diff[:max_diff_chars]
        logger.warning(
            "Diff truncated from %d to %d chars",
            len(diff), max_diff_chars,
        )
        diff = truncated + "\n\n*[Diff truncated due to size limits]*"

    # Language instruction
    lang_instruction = ""
    if language == "zh":
        lang_instruction = (
            "\n\n**Language**: 请用中文输出审核报告，代码片段保留英文。\n"
        )
    elif language == "en":
        lang_instruction = (
            "\n\n**Language**: Output the review in English.\n"
        )

    user_prompt = f"""## Pull Request: {pr_title}

### Description
{pr_description or "_No description provided._"}

### Risk Context
{risk_context or "_No high-risk modules detected._"}

### Changed Files
```diff
{diff}
```
{lang_instruction}
"""

    logger.info(
        "Built review prompt: title=%r, diff=%d chars, language=%s",
        pr_title, len(diff), language,
    )

    return system_prompt, user_prompt
