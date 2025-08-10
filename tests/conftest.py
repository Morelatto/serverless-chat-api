"""Shared test fixtures."""

import asyncio
import os
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient

from chat_api import app

# Set test environment
os.environ["CHAT_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["CHAT_LLM_PROVIDER"] = "gemini"
os.environ["CHAT_GEMINI_API_KEY"] = "test-key"
os.environ["CHAT_RATE_LIMIT"] = "1000/minute"
os.environ["CHAT_LOG_LEVEL"] = "ERROR"  # Reduce log noise


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Test client fixture - simple mocking via app.state."""
    from unittest.mock import AsyncMock

    from httpx import ASGITransport

    from chat_api.chat import ChatService
    from chat_api.providers import LLMResponse

    # Create mock dependencies
    mock_repository = AsyncMock()
    mock_cache = AsyncMock()
    mock_llm_provider = AsyncMock()

    # Setup default mock behaviors
    mock_repository.health_check.return_value = True
    mock_repository.get_history.return_value = []
    mock_repository.save.return_value = None
    mock_cache.get.return_value = None
    mock_cache.set.return_value = None
    mock_llm_provider.health_check.return_value = True
    mock_llm_provider.complete.return_value = LLMResponse(
        text="Test response",
        model="test-model",
        usage={"total_tokens": 10},
    )

    # Create ChatService with mocks and inject into app.state
    app.state.chat_service = ChatService(mock_repository, mock_cache, mock_llm_provider)

    # Also store individual mocks for tests that need them
    app.state.repository = mock_repository
    app.state.cache = mock_cache
    app.state.llm_provider = mock_llm_provider

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_message() -> dict[str, str]:
    """Sample message fixture."""
    return {"user_id": "test_user", "content": "Hello, world!"}


@pytest.fixture
def mock_llm_response() -> dict[str, Any]:
    """Mock LLM response."""
    return {
        "text": "Hello! How can I help you?",
        "model": "test-model",
        "usage": {"total_tokens": 10},
    }
