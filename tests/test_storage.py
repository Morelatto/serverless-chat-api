"""Test storage functionality - SQLite core features only."""

import tempfile
from pathlib import Path

import pytest

from chat_api.storage import SQLiteRepository, cache_key, create_cache, create_repository


@pytest.mark.asyncio
async def test_sqlite_basic_operations() -> None:
    """Test basic SQLite operations."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create repository with temp file
        repo = SQLiteRepository(f"sqlite+aiosqlite:///{db_path}")
        await repo.startup()

        # Test save
        await repo.save(
            id="msg-123",
            user_id="test_user",
            content="Hello",
            response="Hi there!",
            model="test-model",
        )

        # Test get history
        history = await repo.get_history("test_user", 10)
        assert len(history) == 1
        assert history[0]["id"] == "msg-123"
        assert history[0]["content"] == "Hello"

        # Test health check
        assert await repo.health_check() is True

        await repo.shutdown()
    finally:
        # Clean up temp file
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_cache_operations() -> None:
    """Test cache functionality."""
    cache = create_cache()  # Uses in-memory cache
    await cache.startup()

    # Test cache miss
    result = await cache.get("test_key")
    assert result is None

    # Test cache set and get
    test_data = {"id": "test", "content": "cached response"}
    await cache.set("test_key", test_data)

    result = await cache.get("test_key")
    assert result is not None
    assert result["content"] == "cached response"

    await cache.shutdown()


def test_cache_key_generation() -> None:
    """Test cache key generation."""
    key1 = cache_key("user123", "Hello world")
    key2 = cache_key("user123", "Hello world")  # Same inputs
    key3 = cache_key("user123", "Different message")  # Different message
    key4 = cache_key("user456", "Hello world")  # Different user

    # Same inputs should generate same key
    assert key1 == key2

    # Different inputs should generate different keys
    assert key1 != key3
    assert key1 != key4
    assert key3 != key4

    # Keys should be reasonable length and format (blake2b with 16-byte digest = 32 hex chars)
    assert len(key1) == 32
    assert isinstance(key1, str)


@pytest.mark.asyncio
async def test_repository_factory() -> None:
    """Test repository factory function."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        repo = create_repository(f"sqlite+aiosqlite:///{db_path}")
        assert isinstance(repo, SQLiteRepository)

        await repo.startup()
        assert await repo.health_check() is True
        await repo.shutdown()
    finally:
        Path(db_path).unlink(missing_ok=True)
