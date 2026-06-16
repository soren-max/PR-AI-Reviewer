"""
Dependency injection utilities.
"""
from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import LLMProvider
from app.core.database import async_session_factory
from app.services.llm import BaseLLMService, get_llm_service


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_llm(
    provider: Optional[LLMProvider] = None,
) -> BaseLLMService:
    """Provide an LLM service instance via dependency injection.

    Usage in FastAPI routes::

        from app.api.deps import get_llm

        @router.post("/reviews")
        async def create_review(
            llm: BaseLLMService = Depends(get_llm),
        ):
            result = await llm.review_pr(...)

    The provider is selected based on ``settings.LLM_PROVIDER``, but can
    be overridden by passing the ``provider`` argument.
    """
    service = get_llm_service(provider=provider)
    try:
        yield service
    finally:
        await service.close()
