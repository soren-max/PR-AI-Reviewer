"""
Prompt Builder — 构建 LLM 审查所用的 System + User Prompt。

Clean Architecture 层级: Domain
依赖: prompts/pr_review_agent.md
"""
from __future__ import annotations

import os
from typing import Tuple


_PROMPT_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "prompts", "pr_review_agent.md")
)


def _load_system_prompt() -> str:
    """Load the enterprise PR review agent system prompt."""
    try:
        with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return _FALLBACK_SYSTEM_PROMPT


_FALLBACK_SYSTEM_PROMPT = """You are a Senior Staff Software Engineer conducting a code review.

Output ONLY valid JSON with this structure:
{
  "summary": "...",
  "changed_modules": ["..."],
  "issues": [
    {
      "severity": "critical|major|minor|nit",
      "title": "...",
      "file": "...",
      "line": 0,
      "category": "bug|security|performance|maintainability",
      "reason": "...",
      "suggestion": "..."
    }
  ]
}

Focus on: Bug, Security, Performance, Maintainability.
Do NOT file issues for style, missing docs, or untestable claims."""


def build_review_prompt(
    pr_title: str,
    pr_description: str,
    diff: str,
    language: str = "zh",
    risk_context: str = "",
) -> Tuple[str, str]:
    """Build system and user prompts for code review.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    system_prompt = _load_system_prompt()

    # Append language instruction
    if language == "zh":
        system_prompt += "\n\n**Language**: Respond in Chinese (code snippets stay in English)."

    # Build user prompt
    user_prompt = f"""## Pull Request: {pr_title}

### Description
{pr_description or "_No description provided._"}

### Risk Context
{risk_context or "_No high-risk modules detected._"}

### Changed Files
```diff
{diff}
```

Review the above PR diff and output the result as JSON.
"""

    return system_prompt, user_prompt
