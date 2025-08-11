"""Test storage functionality - SQLite core features only."""

import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from chat_api.storage import (
    DEFAULT_CACHE_SIZE,
    DynamoDBRepository,
    InMemoryCache,
    RedisCache,
    SQLiteRepository,
    cache_key,
    create_cache,
    create_repository,
)


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


def test_inmemory_cache_creation():
    """Test in-memory cache creation."""
    cache = InMemoryCache()

    assert cache.max_size == DEFAULT_CACHE_SIZE
    assert cache.cache == {}


def test_inmemory_cache_custom_size():
    """Test in-memory cache with custom size."""
    cache = InMemoryCache(max_size=500)

    assert cache.max_size == 500
    assert cache.cache == {}


def test_inmemory_cache_set_and_get():
    """Test basic cache set and get."""
    cache = InMemoryCache()

    test_data = {"id": "test-123", "content": "test response"}
    cache.cache["test-key"] = (test_data, time.time() + 3600)  # 1 hour from now

    # Directly check cache contents
    assert "test-key" in cache.cache
    data, expiry = cache.cache["test-key"]
    assert data == test_data
    assert expiry > time.time()  # Should not be expired


def test_inmemory_cache_expiry():
    """Test cache expiry logic."""
    cache = InMemoryCache()

    test_data = {"id": "test-123", "content": "test response"}
    # Set item that's already expired
    cache.cache["expired-key"] = (test_data, time.time() - 1)  # 1 second ago

    # Check that expired item exists in cache
    assert "expired-key" in cache.cache

    # But the get method should handle expiry (when we call it via async methods)
    data, expiry = cache.cache["expired-key"]
    assert expiry < time.time()  # Should be expired


def test_cache_clear():
    """Test cache clearing."""
    cache = InMemoryCache()
    cache.cache["test-key"] = ({"test": "data"}, time.time() + 3600)

    assert len(cache.cache) == 1
    cache.cache.clear()
    assert len(cache.cache) == 0


@pytest.mark.asyncio
async def test_inmemory_cache_startup():
    """Test InMemoryCache startup - covers lines 76-78."""
    cache = InMemoryCache()

    # startup does nothing but should be callable
    await cache.startup()

    # Cache should still be empty
    assert cache.cache == {}


@pytest.mark.asyncio
async def test_inmemory_cache_shutdown():
    """Test InMemoryCache shutdown - covers lines 88-90."""
    cache = InMemoryCache()
    cache.cache["test"] = ({"data": "test"}, time.time() + 3600)

    assert len(cache.cache) == 1

    await cache.shutdown()

    # Cache should be cleared
    assert len(cache.cache) == 0


@pytest.mark.asyncio
async def test_inmemory_cache_get_miss():
    """Test InMemoryCache get with cache miss - covers line 99."""
    cache = InMemoryCache()

    result = await cache.get("nonexistent")

    assert result is None


@pytest.mark.asyncio
async def test_inmemory_cache_get_expired():
    """Test InMemoryCache get with expired item - covers lines 103-104."""
    cache = InMemoryCache()

    # Add expired item
    cache.cache["expired"] = ({"data": "old"}, time.time() - 1)

    result = await cache.get("expired")

    assert result is None
    # Expired item should be removed
    assert "expired" not in cache.cache


@pytest.mark.asyncio
async def test_inmemory_cache_get_valid():
    """Test InMemoryCache get with valid item."""
    cache = InMemoryCache()

    test_data = {"data": "valid"}
    cache.cache["valid"] = (test_data, time.time() + 3600)

    result = await cache.get("valid")

    assert result == test_data


@pytest.mark.asyncio
async def test_inmemory_cache_set():
    """Test InMemoryCache set method."""
    cache = InMemoryCache()

    test_data = {"id": "123", "content": "test"}
    await cache.set("test_key", test_data, ttl=3600)

    # Check it was added
    assert "test_key" in cache.cache
    stored_data, expiry = cache.cache["test_key"]
    assert stored_data == test_data
    assert expiry > time.time()


@pytest.mark.asyncio
async def test_inmemory_cache_set_eviction():
    """Test InMemoryCache eviction when over max_size."""
    cache = InMemoryCache(max_size=2)

    # Add items up to max size
    await cache.set("key1", {"data": 1}, ttl=3600)
    await cache.set("key2", {"data": 2}, ttl=3600)

    assert len(cache.cache) == 2

    # Add one more - should evict the oldest
    await cache.set("key3", {"data": 3}, ttl=3600)

    # Should still be at max size
    assert len(cache.cache) == 2
    # First item should be evicted (FIFO based on insertion order)
    assert "key1" not in cache.cache
    assert "key2" in cache.cache
    assert "key3" in cache.cache


@pytest.mark.asyncio
async def test_redis_cache_startup_success():
    """Test RedisCache successful startup - covers lines 111-113, 117-119."""
    with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_from_url:
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        cache = RedisCache("redis://localhost:6379")
        await cache.startup()

        # Should have created client and pinged
        mock_from_url.assert_called_once_with("redis://localhost:6379")
        mock_client.ping.assert_called_once()
        assert cache.client == mock_client


@pytest.mark.asyncio
async def test_redis_cache_startup_failure():
    """Test RedisCache startup failure - covers lines 120-122."""
    with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_from_url:
        mock_client = AsyncMock()
        mock_client.ping.side_effect = ConnectionError("Connection refused")
        mock_from_url.return_value = mock_client

        cache = RedisCache("redis://localhost:6379")

        with pytest.raises(ConnectionError, match="Failed to connect to Redis"):
            await cache.startup()


@pytest.mark.asyncio
async def test_redis_cache_shutdown():
    """Test RedisCache shutdown - covers lines 124-126, 130-131."""
    cache = RedisCache("redis://localhost:6379")

    # Test shutdown with no client
    await cache.shutdown()  # Should not raise

    # Test shutdown with client
    mock_client = AsyncMock()
    cache.client = mock_client

    await cache.shutdown()
    mock_client.close.assert_called_once()

    # Test shutdown with client that fails
    mock_client_fail = AsyncMock()
    mock_client_fail.close.side_effect = ConnectionError("Close failed")
    cache.client = mock_client_fail

    # Should not raise, just log warning
    await cache.shutdown()


@pytest.mark.asyncio
async def test_redis_cache_get():
    """Test RedisCache get method - covers lines 133-135, 139-142."""
    cache = RedisCache("redis://localhost:6379")

    # Mock client
    mock_client = AsyncMock()
    cache.client = mock_client

    # Test cache hit
    mock_client.get.return_value = '{"id": "123", "data": "test"}'
    result = await cache.get("test_key")

    assert result == {"id": "123", "data": "test"}
    mock_client.get.assert_called_once_with("test_key")

    # Test cache miss
    mock_client.get.return_value = None
    result = await cache.get("missing_key")

    assert result is None

    # Test invalid JSON - should raise (lines 150-153)
    mock_client.reset_mock()
    mock_client.get.return_value = "invalid json {"

    # The cache should catch and re-raise the JSON error
    from json import JSONDecodeError

    with pytest.raises(JSONDecodeError):  # JSONDecodeError is re-raised
        await cache.get("bad_key")


@pytest.mark.asyncio
async def test_redis_cache_get_error():
    """Test RedisCache get with error - covers lines 143-145."""
    cache = RedisCache("redis://localhost:6379")

    mock_client = AsyncMock()
    mock_client.get.side_effect = ConnectionError("Redis unavailable")
    cache.client = mock_client

    with pytest.raises(ConnectionError):
        await cache.get("test_key")


@pytest.mark.asyncio
async def test_redis_cache_set():
    """Test RedisCache set method - covers lines 147-153."""
    cache = RedisCache("redis://localhost:6379")

    mock_client = AsyncMock()
    cache.client = mock_client

    test_data = {"id": "123", "content": "test"}
    await cache.set("test_key", test_data, ttl=3600)

    # Verify setex was called with correct args
    mock_client.setex.assert_called_once()
    call_args = mock_client.setex.call_args[0]
    assert call_args[0] == "test_key"
    assert call_args[1] == 3600
    assert '"id": "123"' in call_args[2]


@pytest.mark.asyncio
async def test_redis_cache_set_error():
    """Test RedisCache set with error - covers lines 157-159."""
    cache = RedisCache("redis://localhost:6379")

    mock_client = AsyncMock()
    mock_client.setex.side_effect = ConnectionError("Redis unavailable")
    cache.client = mock_client

    with pytest.raises(ConnectionError):
        await cache.set("test_key", {"data": "test"}, ttl=3600)


@pytest.mark.asyncio
async def test_redis_cache_set_serialization_error():
    """Test RedisCache set with serialization error - covers lines 160-162."""
    cache = RedisCache("redis://localhost:6379")

    mock_client = AsyncMock()
    cache.client = mock_client

    # Create non-serializable object
    class NonSerializable:
        pass

    with pytest.raises(TypeError):
        await cache.set("test_key", {"obj": NonSerializable()}, ttl=3600)


def test_create_cache_no_redis():
    """Test create_cache without Redis URL - covers line 411."""
    cache = create_cache()
    assert isinstance(cache, InMemoryCache)


def test_create_cache_with_redis():
    """Test create_cache with Redis URL - covers lines 406-407."""
    cache = create_cache("redis://localhost:6379")
    assert isinstance(cache, RedisCache)
    assert cache.redis_url == "redis://localhost:6379"


def test_create_repository_sqlite():
    """Test create_repository with SQLite URL."""
    from chat_api.storage import SQLiteRepository

    repo = create_repository("sqlite+aiosqlite:///test.db")
    assert isinstance(repo, SQLiteRepository)


def test_create_repository_dynamodb():
    """Test create_repository with DynamoDB URL - covers lines 421-422."""

    repo = create_repository("dynamodb://test-table?region=us-east-1")
    assert isinstance(repo, DynamoDBRepository)
    assert repo.table_name == "test-table"
    assert repo.region == "us-east-1"
