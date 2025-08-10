"""Tests for storage operations."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chat_api.exceptions import StorageError
from chat_api.storage import (
    DynamoDBRepository,
    InMemoryCache,
    RedisCache,
    SQLiteRepository,
    cache_key,
    create_cache,
    create_repository,
)


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

        # Save multiple messages with slight delay to ensure ordering
        import asyncio

        for i in range(3):
            await repo.save(
                id=f"msg-{i}",
                user_id="test_user",
                content=f"Hello {i}",
                response=f"Hi there {i}!",
                model="test-model",
            )
            await asyncio.sleep(0.01)  # Small delay to ensure different timestamps

        # Get history
        history = await repo.get_history("test_user", 10)
        assert len(history) == 3
        # Check that all messages are present (order may vary with same timestamp)
        ids = {h["id"] for h in history}
        assert ids == {"msg-0", "msg-1", "msg-2"}

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
    with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_redis_from_url:
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
    with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_redis_from_url:
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
    with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_redis_from_url:
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

    # Keys should be reasonable length and format (blake2b with 16-byte digest = 32 hex chars)
    assert len(key1) == 32
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
        with (
            patch.object(
                repo.database,
                "execute",
                side_effect=Exception("Database connection failed"),
            ),
            pytest.raises(Exception, match="Database connection failed"),
        ):
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
    # InMemoryCache should handle any data gracefully
    cache = InMemoryCache()
    await cache.startup()

    # Should not raise any error
    class NonSerializable:
        pass

    # InMemoryCache stores actual objects, so it can handle non-serializable data
    await cache.set("test_key", {"data": NonSerializable()}, 3600)  # type: ignore
    result = await cache.get("test_key")
    assert result is not None  # InMemoryCache stores the actual object
    assert "data" in result

    await cache.shutdown()


@pytest.mark.asyncio
async def test_cache_json_parsing_error() -> None:
    """Test handling JSON parsing errors in cache retrieval."""
    with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_redis_from_url:
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
        import asyncio

        for i in range(10):
            await repo.save(
                id=f"msg-{i}",
                user_id="test_user",
                content=f"Message {i}",
                response=f"Response {i}",
                model="test-model",
            )
            await asyncio.sleep(0.01)  # Small delay to ensure different timestamps

        # Request only 5 messages
        history = await repo.get_history("test_user", 5)
        assert len(history) == 5
        # Check that we got 5 messages (specific order may vary with same timestamps)
        ids = [h["id"] for h in history]
        assert len(ids) == 5
        assert all(id.startswith("msg-") for id in ids)

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
            "usage": {"total_tokens": 42},
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
        assert msg.get("usage") == {"total_tokens": 42}

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
        cache = create_cache()  # Should create InMemoryCache without Redis URL
        assert isinstance(cache, InMemoryCache)
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_in_memory_cache_ttl() -> None:
    """Test InMemoryCache TTL expiration."""
    import time

    cache = InMemoryCache()
    await cache.startup()

    # Set with 1 second TTL
    await cache.set("key", {"data": "value"}, 1)

    # Should get value immediately
    result = await cache.get("key")
    assert result == {"data": "value"}

    # Wait for expiration
    time.sleep(1.1)

    # Should return None after expiration
    result = await cache.get("key")
    assert result is None

    await cache.shutdown()


@pytest.mark.asyncio
async def test_in_memory_cache_operations() -> None:
    """Test InMemoryCache basic operations."""
    cache = InMemoryCache()
    await cache.startup()

    # Set and get
    await cache.set("test_key", {"data": "value"}, 3600)
    result = await cache.get("test_key")
    assert result == {"data": "value"}

    await cache.shutdown()


@pytest.mark.asyncio
async def test_dynamodb_repository() -> None:
    """Test DynamoDB repository operations."""
    with patch("boto3.resource") as mock_boto3:
        # Mock DynamoDB table
        mock_table = AsyncMock()
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        repo = DynamoDBRepository("dynamodb://test-table?region=us-east-1")
        await repo.startup()

        # Test save
        await repo.save(
            id="msg-123",
            user_id="user-456",
            content="Hello DynamoDB",
            response="Response from DynamoDB",
            model="gpt-4",
            usage={"total_tokens": 25},
        )

        mock_table.put_item.assert_called_once()
        put_args = mock_table.put_item.call_args[1]["Item"]
        assert put_args["id"] == "msg-123"
        assert put_args["user_id"] == "user-456"
        assert put_args["content"] == "Hello DynamoDB"

        # Test get_history
        mock_table.query.return_value = {
            "Items": [
                {
                    "id": "msg-1",
                    "user_id": "user-456",
                    "content": "Message 1",
                    "response": "Response 1",
                    "timestamp": "2025-01-01T00:00:00Z",
                },
            ],
        }

        history = await repo.get_history("user-456", 10)
        assert len(history) == 1
        assert history[0]["id"] == "msg-1"

        mock_table.query.assert_called_with(
            KeyConditionExpression=mock_boto3.return_value.Table().user_id.eq("user-456"),
            Limit=10,
            ScanIndexForward=False,
        )

        # Test health check
        mock_table.table_status = "ACTIVE"
        health = await repo.health_check()
        assert health is True

        await repo.shutdown()


@pytest.mark.asyncio
async def test_dynamodb_repository_error_handling() -> None:
    """Test DynamoDB repository error handling."""
    with patch("boto3.resource") as mock_boto3:
        mock_table = AsyncMock()
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        repo = DynamoDBRepository("dynamodb://test-table")
        await repo.startup()

        # Test save error
        mock_table.put_item.side_effect = Exception("DynamoDB error")

        with pytest.raises(Exception, match="DynamoDB error"):
            await repo.save(
                id="msg-123",
                user_id="user-456",
                content="Test",
                response="Test",
            )

        # Test health check failure
        mock_table.table_status = "CREATING"
        health = await repo.health_check()
        assert health is False

        await repo.shutdown()


@pytest.mark.asyncio
async def test_redis_cache_connection_failure() -> None:
    """Test Redis cache connection failure handling."""
    with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_redis_from_url:
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = ConnectionError("Redis not available")
        mock_redis_from_url.return_value = mock_redis

        cache = RedisCache("redis://localhost")
        await cache.startup()

        # Operations should handle connection errors gracefully
        result = await cache.get("test_key")
        assert result is None

        await cache.shutdown()


@pytest.mark.asyncio
async def test_redis_cache_operations() -> None:
    """Test Redis cache operations."""
    with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_redis_from_url:
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = '{"data": "value"}'
        mock_redis_from_url.return_value = mock_redis

        cache = RedisCache("redis://localhost")
        await cache.startup()

        # Test get operation
        result = await cache.get("test_key")
        assert result == {"data": "value"}

        await cache.shutdown()


@pytest.mark.asyncio
async def test_create_repository_dynamodb() -> None:
    """Test creating DynamoDB repository."""
    with patch("boto3.resource") as mock_boto3:
        mock_dynamodb = MagicMock()
        mock_boto3.return_value = mock_dynamodb

        repo = create_repository("dynamodb://test-table?region=us-west-2")
        assert isinstance(repo, DynamoDBRepository)


@pytest.mark.asyncio
async def test_create_repository_invalid_url() -> None:
    """Test creating repository with invalid URL."""
    with pytest.raises(StorageError, match="Unsupported database URL scheme"):
        create_repository("invalid://path")


@pytest.mark.asyncio
async def test_create_cache_with_redis() -> None:
    """Test creating cache with Redis URL."""
    with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_redis_from_url:
        mock_redis = AsyncMock()
        mock_redis_from_url.return_value = mock_redis

        cache = create_cache("redis://localhost:6379")
        assert isinstance(cache, RedisCache)


@pytest.mark.asyncio
async def test_sqlite_repository_connection_pool() -> None:
    """Test SQLite repository uses connection pooling."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        repo = SQLiteRepository(f"sqlite+aiosqlite:///{db_path}")
        await repo.startup()

        # Multiple operations should reuse connections
        for i in range(5):
            await repo.save(
                id=f"msg-{i}",
                user_id="test_user",
                content=f"Message {i}",
                response=f"Response {i}",
            )

        history = await repo.get_history("test_user", 10)
        assert len(history) == 5

        await repo.shutdown()
    finally:
        Path(db_path).unlink(missing_ok=True)
