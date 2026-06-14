"""
Shared test fixtures.
"""
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import async_session_factory, engine, init_db
from app.main import app
from app.models.base import Base

# ---------------------------------------------------------------------------
# In-memory SQLite for tests
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a clean in-memory database engine for the test session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional test database session."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def async_client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client against the FastAPI app with overridden DB."""
    async def override_get_db():
        session_factory = async_sessionmaker(
            bind=test_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides.clear()
    from app.api.deps import get_db
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Mock fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_github_service():
    """Mock GitHubService for isolated service tests."""
    with patch("app.services.github.GitHubService", autospec=True) as mock:
        instance = mock.return_value
        instance.fetch_pr_metadata = AsyncMock(return_value=MagicMock(
            title="Test PR",
            author="testuser",
            base_branch="main",
            head_branch="feat/test",
            changed_files_count=2,
            additions=50,
            deletions=10,
        ))
        instance.fetch_pr_diff = AsyncMock(return_value=[])
        instance.verify_pr_exists = AsyncMock(return_value=None)
        yield instance


@pytest.fixture
def mock_llm_client():
    """Mock LLMClient for isolated service tests."""
    from app.services.llm import LLMResponse
    with patch("app.services.llm.LLMClient", autospec=True) as mock:
        instance = mock.return_value
        instance.chat_completion = AsyncMock(return_value=LLMResponse(
            content='{"overall_score":85,"summary":{"total_issues":2},"issues":[]}',
            input_tokens=500,
            output_tokens=150,
            total_tokens=650,
        ))
        yield instance
