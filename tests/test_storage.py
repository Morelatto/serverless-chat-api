"""Tests for storage operations."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from chat_api.storage import (
    cache_key,
    create_cache,
    create_repository,
)
from chat_api.storage.cache import NoOpCache, RedisCache
from chat_api.storage.sqlite import SQLiteRepository


@pytest.mark.asyncio
async def test_save_message() -> None:
    """Test saving message to database."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create repository with temp file
        repo = SQLiteRepository(f"sqlite+aiosqlite:///{db_path}")
        await repo.startup()

        # Save a message
        await repo.save(
            id="msg-123",
            user_id="test_user",
            content="Hello",
            response="Hi there!",
            model="test-model",
            tokens=10,
        )

        # Verify by getting history
        history = await repo.get_history("test_user", 10)
        assert len(history) == 1
        assert history[0]["id"] == "msg-123"
        assert history[0]["content"] == "Hello"

        await repo.shutdown()
    finally:
        # Clean up temp file
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_get_user_history() -> None:
    """Test retrieving user history from database."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create repository with temp file
        repo = SQLiteRepository(f"sqlite+aiosqlite:///{db_path}")
        await repo.startup()

        # Save multiple messages
        for i in range(3):
            await repo.save(
                id=f"msg-{i}",
                user_id="test_user",
                content=f"Hello {i}",
                response=f"Hi there {i}!",
                model="test-model",
            )

        # Get history
        history = await repo.get_history("test_user", 10)
        assert len(history) == 3
        # Should be in reverse order (newest first)
        assert history[0]["id"] == "msg-2"
        assert history[2]["id"] == "msg-0"

        await repo.shutdown()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_get_user_history_empty() -> None:
    """Test retrieving history for user with no messages."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create repository with temp file
        repo = SQLiteRepository(f"sqlite+aiosqlite:///{db_path}")
        await repo.startup()

        history = await repo.get_history("new_user", 10)
        assert history == []

        await repo.shutdown()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_get_cached_hit() -> None:
    """Test cache hit scenario."""
    with patch("redis.asyncio.from_url") as mock_redis_from_url:
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.get.return_value = '{"id": "test", "content": "cached response"}'
        mock_redis.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis

        # Create cache and initialize
        cache = RedisCache("redis://localhost")
        await cache.startup()

        # Test cache get
        result = await cache.get("test_key")
        assert result is not None
        assert result["content"] == "cached response"

        mock_redis.get.assert_called_once_with("test_key")
        await cache.shutdown()


@pytest.mark.asyncio
async def test_get_cached_miss() -> None:
    """Test cache miss scenario."""
    with patch("redis.asyncio.from_url") as mock_redis_from_url:
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis

        # Create cache and initialize
        cache = RedisCache("redis://localhost")
        await cache.startup()

        # Test cache miss
        result = await cache.get("test_key")
        assert result is None

        mock_redis.get.assert_called_once_with("test_key")
        await cache.shutdown()


@pytest.mark.asyncio
async def test_set_cached() -> None:
    """Test setting data in cache."""
    with patch("redis.asyncio.from_url") as mock_redis_from_url:
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis

        # Create cache and initialize
        cache = RedisCache("redis://localhost")
        await cache.startup()

        # Test cache set
        test_data = {"id": "test", "content": "response"}
        await cache.set("test_key", test_data, 3600)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == "test_key"
        assert call_args[1] == 3600

        await cache.shutdown()


@pytest.mark.asyncio
async def test_health_check_healthy() -> None:
    """Test health check when database is healthy."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create repository with temp file
        repo = SQLiteRepository(f"sqlite+aiosqlite:///{db_path}")
        await repo.startup()

        result = await repo.health_check()
        assert result is True

        await repo.shutdown()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_health_check_database_failure() -> None:
    """Test health check when database fails."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create repository with temp file
        repo = SQLiteRepository(f"sqlite+aiosqlite:///{db_path}")
        await repo.startup()

        # Mock execute to fail
        with patch.object(repo.database, "execute", side_effect=ConnectionError("DB error")):
            result = await repo.health_check()
            assert result is False

        await repo.shutdown()
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_generate_cache_key() -> None:
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

    # Keys should be reasonable length and format
    assert len(key1) == 16  # We limit to 16 chars
    assert isinstance(key1, str)


@pytest.mark.asyncio
async def test_save_message_database_error() -> None:
    """Test handling database errors during message save."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create repository with temp file
        repo = SQLiteRepository(f"sqlite+aiosqlite:///{db_path}")
        await repo.startup()

        # Mock execute to fail
        with patch.object(
            repo.database, "execute", side_effect=Exception("Database connection failed")
        ):
            with pytest.raises(Exception, match="Database connection failed"):
                await repo.save(
                    id="msg-123",
                    user_id="test_user",
                    content="Hello",
                    response="Hi there!",
                    model="test-model",
                    tokens=10,
                )

        await repo.shutdown()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_get_user_history_database_error() -> None:
    """Test handling database errors during history retrieval."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create repository with temp file
        repo = SQLiteRepository(f"sqlite+aiosqlite:///{db_path}")
        await repo.startup()

        # Mock fetch_all to fail
        with patch.object(repo.database, "fetch_all", side_effect=Exception("Query failed")):
            with pytest.raises(Exception, match="Query failed"):
                await repo.get_history("test_user", 10)

        await repo.shutdown()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_cache_serialization_error() -> None:
    """Test handling serialization errors in cache operations."""
    # NoOpCache should handle any data gracefully
    cache = NoOpCache()
    await cache.startup()

    # Should not raise any error
    class NonSerializable:
        pass

    await cache.set("test_key", {"data": NonSerializable()}, 3600)  # type: ignore
    result = await cache.get("test_key")
    assert result is None  # NoOpCache always returns None

    await cache.shutdown()


@pytest.mark.asyncio
async def test_cache_json_parsing_error() -> None:
    """Test handling JSON parsing errors in cache retrieval."""
    with patch("redis.asyncio.from_url") as mock_redis_from_url:
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "invalid json {"
        mock_redis.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis

        # Create cache and initialize
        cache = RedisCache("redis://localhost")
        await cache.startup()

        # Should handle invalid JSON gracefully
        result = await cache.get("test_key")
        assert result is None

        await cache.shutdown()


@pytest.mark.asyncio
async def test_get_user_history_limit_enforcement() -> None:
    """Test that history limit is properly enforced."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create repository with temp file
        repo = SQLiteRepository(f"sqlite+aiosqlite:///{db_path}")
        await repo.startup()

        # Save more messages than limit
        for i in range(10):
            await repo.save(
                id=f"msg-{i}",
                user_id="test_user",
                content=f"Message {i}",
                response=f"Response {i}",
                model="test-model",
            )

        # Request only 5 messages
        history = await repo.get_history("test_user", 5)
        assert len(history) == 5
        # Should get the 5 most recent (9, 8, 7, 6, 5)
        assert history[0]["id"] == "msg-9"
        assert history[4]["id"] == "msg-5"

        await repo.shutdown()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_message_data_integrity() -> None:
    """Test that saved message data maintains integrity."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create repository with temp file
        repo = SQLiteRepository(f"sqlite+aiosqlite:///{db_path}")
        await repo.startup()

        test_data = {
            "id": "msg-456",
            "user_id": "test_user_123",
            "content": "Hello with special chars: <>\"'&",
            "response": "Response with unicode: 🚀 emoji",
            "model": "test-model",
            "tokens": 42,
        }

        await repo.save(**test_data)

        # Retrieve and verify
        history = await repo.get_history("test_user_123", 1)
        assert len(history) == 1
        msg = history[0]
        assert msg["id"] == "msg-456"
        assert msg["content"] == "Hello with special chars: <>\"'&"
        assert msg["response"] == "Response with unicode: 🚀 emoji"
        assert msg.get("model") == "test-model"
        assert msg.get("tokens") == 42

        await repo.shutdown()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_factory_functions() -> None:
    """Test factory functions for creating repository and cache."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Test repository creation
        repo = create_repository(f"sqlite+aiosqlite:///{db_path}")
        assert isinstance(repo, SQLiteRepository)

        # Test cache creation
        cache = create_cache()  # Should create NoOpCache without Redis URL
        assert isinstance(cache, NoOpCache)
    finally:
        Path(db_path).unlink(missing_ok=True)
