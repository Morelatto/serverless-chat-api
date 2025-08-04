"""Pytest configuration and shared fixtures"""
import os
import sys
import pytest
import asyncio
from pathlib import Path

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
    return {
        "response": "Test response",
        "model": "mock",
        "tokens": 10,
        "latency_ms": 100
    }