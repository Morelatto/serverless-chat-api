"""Shared test fixtures."""

import asyncio
import os
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient

from chat_api.app import app

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
    """Test client fixture."""
    from unittest.mock import AsyncMock

    from httpx import ASGITransport

    # Initialize mock repository and cache in app state
    app.state.repository = AsyncMock()
    app.state.cache = AsyncMock()

    # Setup default mock behaviors
    app.state.repository.health_check.return_value = True
    app.state.repository.get_history.return_value = []
    app.state.repository.save.return_value = None
    app.state.cache.get.return_value = None
    app.state.cache.set.return_value = None

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
