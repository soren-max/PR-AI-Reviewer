"""
Checkpoint extension point for the LangGraph review workflow.

Persistence is intentionally not implemented in Sprint 3. The protocol keeps
the service constructor stable for a future LangGraph checkpointer or custom
state snapshot store.
"""
from __future__ import annotations

from typing import Protocol

from app.services.review.state import ReviewState


class ReviewCheckpoint(Protocol):
    """Future checkpoint storage contract."""

    async def save(self, state: ReviewState) -> None:
        """Persist a review workflow state snapshot."""
        ...

    async def load(self, review_id: str) -> ReviewState | None:
        """Load a previously persisted review workflow state snapshot."""
        ...
