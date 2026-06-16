"""
Compatibility wrapper for the canonical LLM review prompt builder.

The active prompt implementation lives in ``app.services.llm.prompts`` because
all LLM providers share it. This module keeps the older review-domain import
path stable without maintaining a second prompt implementation.
"""
from __future__ import annotations

from app.services.llm.prompts import build_review_prompt

__all__ = ["build_review_prompt"]
