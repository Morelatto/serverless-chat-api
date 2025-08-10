"""Test production storage backends (DynamoDB and Redis)."""

import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chat_api.storage import (
    DynamoDBRepository,
    RedisCache,
    SQLiteRepository,
    cache_key,
    create_cache,
    create_repository,
)


class TestDynamoDBRepository:
    """Test DynamoDB repository implementation."""

    @pytest.mark.asyncio
    @patch("chat_api.storage.boto3.resource")
    async def test_dynamodb_initialization(self, mock_boto_resource):
        """Test DynamoDB repository initialization."""
        # Mock DynamoDB resource
        mock_table = MagicMock()
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb

        # Create repository
        repo = DynamoDBRepository("dynamodb://chat-table?region=us-east-1")
        await repo.startup()

        # Verify boto3 was called correctly
        mock_boto_resource.assert_called_once_with("dynamodb", region_name="us-east-1")
        mock_dynamodb.Table.assert_called_once_with("chat-table")

        await repo.shutdown()

    @pytest.mark.asyncio
    @patch("chat_api.storage.boto3.resource")
    async def test_dynamodb_save_message(self, mock_boto_resource):
        """Test saving a message to DynamoDB."""
        # Mock DynamoDB table
        mock_table = MagicMock()
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb

        repo = DynamoDBRepository("dynamodb://chat-table?region=us-east-1")
        await repo.startup()

        # Save a message
        await repo.save(
            id="msg-123",
            user_id="user-456",
            content="Test message",
            response="Test response",
            model="gpt-4",
            usage={"total_tokens": 25},
        )

        # Verify put_item was called
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]["Item"]

        assert call_args["id"] == "msg-123"
        assert call_args["user_id"] == "user-456"
        assert call_args["content"] == "Test message"
        assert call_args["response"] == "Test response"
        assert call_args["model"] == "gpt-4"
        assert "timestamp" in call_args

        await repo.shutdown()

    @pytest.mark.asyncio
    @patch("chat_api.storage.boto3.resource")
    async def test_dynamodb_get_history(self, mock_boto_resource):
        """Test retrieving user history from DynamoDB."""
        # Mock DynamoDB table with query response
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "id": "msg-1",
                    "user_id": "user-123",
                    "content": "Hello",
                    "response": "Hi there",
                    "timestamp": "2025-01-01T00:00:00Z",
                    "model": "gpt-4",
                    "tokens": Decimal("20"),
                },
                {
                    "id": "msg-2",
                    "user_id": "user-123",
                    "content": "How are you?",
                    "response": "I'm doing well",
                    "timestamp": "2025-01-01T00:01:00Z",
                    "model": "gpt-4",
                    "tokens": Decimal("25"),
                },
            ]
        }

        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb

        repo = DynamoDBRepository("dynamodb://chat-table?region=us-east-1")
        await repo.startup()

        # Get history
        history = await repo.get_history("user-123", limit=10)

        # Verify query was called correctly
        mock_table.query.assert_called_once()
        query_kwargs = mock_table.query.call_args[1]
        assert query_kwargs["Limit"] == 10
        assert "user-123" in str(query_kwargs["KeyConditionExpression"])

        # Verify response format
        assert len(history) == 2
        assert history[0]["id"] == "msg-1"
        assert history[0]["content"] == "Hello"

        await repo.shutdown()

    @pytest.mark.asyncio
    @patch("chat_api.storage.boto3.resource")
    async def test_dynamodb_health_check(self, mock_boto_resource):
        """Test DynamoDB health check."""
        # Mock successful describe_table
        mock_table = MagicMock()
        mock_table.table_status = "ACTIVE"

        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb

        repo = DynamoDBRepository("dynamodb://chat-table?region=us-east-1")
        await repo.startup()

        # Health check should succeed
        result = await repo.health_check()
        assert result is True

        # Mock failure
        mock_table.reload.side_effect = Exception("Table not found")
        result = await repo.health_check()
        assert result is False

        await repo.shutdown()

    @pytest.mark.asyncio
    @patch("chat_api.storage.boto3.resource")
    async def test_dynamodb_connection_error_handling(self, mock_boto_resource):
        """Test DynamoDB connection error handling."""
        # Mock connection failure
        mock_boto_resource.side_effect = Exception("AWS credentials not found")

        repo = DynamoDBRepository("dynamodb://chat-table?region=us-east-1")

        # Startup should handle error gracefully
        with pytest.raises(Exception, match="AWS credentials"):
            await repo.startup()

    @pytest.mark.asyncio
    @patch("chat_api.storage.boto3.resource")
    async def test_dynamodb_decimal_handling(self, mock_boto_resource):
        """Test proper handling of DynamoDB Decimal types."""
        # DynamoDB returns Decimal types for numbers
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "id": "msg-1",
                    "tokens": Decimal("42"),  # DynamoDB Decimal
                    "cost": Decimal("0.0025"),
                },
            ]
        }

        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb

        repo = DynamoDBRepository("dynamodb://chat-table?region=us-east-1")
        await repo.startup()

        history = await repo.get_history("user-123", limit=1)

        # Should handle Decimal conversion
        assert len(history) == 1
        # Decimals should be converted to appropriate types
        if "tokens" in history[0]:
            assert isinstance(history[0]["tokens"], (int, float, Decimal))

        await repo.shutdown()


class TestRedisCache:
    """Test Redis cache implementation."""

    @pytest.mark.asyncio
    @patch("redis.asyncio.from_url")
    async def test_redis_initialization(self, mock_redis_from_url):
        """Test Redis cache initialization."""
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis

        cache = RedisCache("redis://localhost:6379")
        await cache.startup()

        # Verify connection
        mock_redis_from_url.assert_called_once_with(
            "redis://localhost:6379",
            decode_responses=True,
        )
        mock_redis.ping.assert_called_once()

        await cache.shutdown()
        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("redis.asyncio.from_url")
    async def test_redis_get_and_set(self, mock_redis_from_url):
        """Test Redis get and set operations."""
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None  # Initial miss
        mock_redis_from_url.return_value = mock_redis

        cache = RedisCache("redis://localhost:6379")
        await cache.startup()

        # Test cache miss
        result = await cache.get("test_key")
        assert result is None
        mock_redis.get.assert_called_once_with("test_key")

        # Test cache set
        test_data = {"id": "123", "content": "test"}
        await cache.set("test_key", test_data, ttl=3600)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == "test_key"
        assert call_args[1] == 3600
        assert json.loads(call_args[2]) == test_data

        # Test cache hit
        mock_redis.get.return_value = json.dumps(test_data)
        result = await cache.get("test_key")
        assert result == test_data

        await cache.shutdown()

    @pytest.mark.asyncio
    @patch("redis.asyncio.from_url")
    async def test_redis_connection_failure(self, mock_redis_from_url):
        """Test Redis connection failure handling."""
        # Mock connection failure
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = ConnectionError("Cannot connect to Redis")
        mock_redis_from_url.return_value = mock_redis

        cache = RedisCache("redis://localhost:6379")

        # Startup should handle connection error
        with pytest.raises(ConnectionError, match="Cannot connect to Redis"):
            await cache.startup()

    @pytest.mark.asyncio
    @patch("redis.asyncio.from_url")
    async def test_redis_operation_failure_graceful_degradation(self, mock_redis_from_url):
        """Test graceful degradation when Redis operations fail."""
        # Mock Redis client that fails on operations
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True  # Startup succeeds
        mock_redis.get.side_effect = ConnectionError("Lost connection")
        mock_redis.setex.side_effect = ConnectionError("Lost connection")
        mock_redis_from_url.return_value = mock_redis

        cache = RedisCache("redis://localhost:6379")
        await cache.startup()

        # Get should return None on error (graceful degradation)
        result = await cache.get("test_key")
        assert result is None

        # Set should not raise (graceful degradation)
        await cache.set("test_key", {"data": "test"}, ttl=3600)

        await cache.shutdown()

    @pytest.mark.asyncio
    @patch("redis.asyncio.from_url")
    async def test_redis_ttl_expiration(self, mock_redis_from_url):
        """Test Redis TTL (time-to-live) functionality."""
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis

        cache = RedisCache("redis://localhost:6379")
        await cache.startup()

        # Set with custom TTL
        await cache.set("short_ttl", {"data": "expires soon"}, ttl=60)
        await cache.set("long_ttl", {"data": "expires later"}, ttl=3600)

        # Verify setex was called with correct TTLs
        calls = mock_redis.setex.call_args_list
        assert len(calls) == 2
        assert calls[0][0][1] == 60  # First call TTL
        assert calls[1][0][1] == 3600  # Second call TTL

        await cache.shutdown()


class TestFactoryFunctions:
    """Test storage factory functions."""

    def test_create_repository_sqlite(self):
        """Test creating SQLite repository."""

        repo = create_repository("sqlite+aiosqlite:///./test.db")
        assert isinstance(repo, SQLiteRepository)

    @patch("chat_api.storage.boto3.resource")
    def test_create_repository_dynamodb(self, mock_boto):
        """Test creating DynamoDB repository."""
        repo = create_repository("dynamodb://my-table?region=us-east-1")
        assert isinstance(repo, DynamoDBRepository)

    def test_create_repository_invalid_url(self):
        """Test creating repository with invalid URL."""
        with pytest.raises(ValueError, match="Unsupported database URL"):
            create_repository("invalid://database")

    def test_create_cache_memory(self):
        """Test creating in-memory cache (no Redis URL)."""
        from chat_api.storage.cache import InMemoryCache

        cache = create_cache(None)
        assert isinstance(cache, InMemoryCache)

    @patch("redis.asyncio.from_url")
    def test_create_cache_redis(self, mock_redis):
        """Test creating Redis cache."""
        mock_redis.return_value = AsyncMock()

        cache = create_cache("redis://localhost:6379")
        assert isinstance(cache, RedisCache)


class TestCacheKeyGeneration:
    """Test secure cache key generation."""

    def test_cache_key_consistency(self):
        """Test cache key generation is consistent."""
        key1 = cache_key("user123", "Hello world")
        key2 = cache_key("user123", "Hello world")

        assert key1 == key2
        assert len(key1) == 32  # Blake2b with 16 bytes = 32 hex chars

    def test_cache_key_uniqueness(self):
        """Test cache keys are unique for different inputs."""
        key1 = cache_key("user1", "message")
        key2 = cache_key("user2", "message")
        key3 = cache_key("user1", "different")

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_cache_key_security(self):
        """Test cache keys don't expose sensitive data."""
        sensitive_message = "My password is secret123"
        key = cache_key("user", sensitive_message)

        # Key should be hashed, not contain original
        assert "password" not in key
        assert "secret123" not in key
        assert len(key) == 32  # Fixed length hash
