"""Pytest configuration and shared fixtures"""
import asyncio
import os
import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = ":memory:"
os.environ["ENABLE_CACHE"] = "false"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_database():
    """Create a mock database for testing"""
    from src.shared.database import DatabaseInterface

    db = DatabaseInterface()
    await db.initialize()
    yield db


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing"""
    return {"response": "Test response", "model": "mock", "tokens": 10, "latency_ms": 100}


@pytest.fixture
def mock_chat_service():
    """Mock ChatService for API testing"""
    from unittest.mock import AsyncMock

    mock_service = AsyncMock()
    mock_service.process_prompt.return_value = {
        "interaction_id": "test-123",  # Service returns this
        "response": "Test response",
        "model": "mock",
        "timestamp": "2025-01-01T00:00:00",
        "cached": False,
        "latency_ms": 100,
    }

    mock_service.check_dependencies.return_value = {
        "database": True,
        "llm_provider": True,
        "cache": True,
    }

    return mock_service


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing"""
    from unittest.mock import AsyncMock

    provider = AsyncMock()
    provider.generate.return_value = "Generated response"
    provider.is_available.return_value = True
    provider.get_model_name.return_value = "test-model"

    return provider


@pytest.fixture
def valid_chat_request():
    """Valid chat request payload"""
    return {"prompt": "Test prompt", "userId": "test123"}


@pytest.fixture
def mock_database_interface():
    """Mock database interface"""
    from unittest.mock import AsyncMock

    db = AsyncMock()
    db.save_interaction.return_value = None
    db.get_interaction.return_value = {
        "interaction_id": "test-123",
        "user_id": "test123",
        "prompt": "Test prompt",
        "response": "Test response",
        "timestamp": "2025-01-01T00:00:00",
    }
    db.get_user_history.return_value = []
    db.health_check.return_value = True

    return db
