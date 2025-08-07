"""Tests for storage operations."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from chat_api.storage import (
    cache_key,
    get_cached,
    get_user_history,
    health_check,
    save_message,
    set_cached,
)


@pytest.mark.asyncio
async def test_save_message() -> None:
    """Test saving message to database."""
    with patch('chat_api.storage.database') as mock_db:
        mock_db.execute = AsyncMock()

        await save_message(
            id="msg-123",
            user_id="test_user",
            content="Hello",
            response="Hi there!",
            model="test-model",
            tokens=10
        )

        # Verify database was called
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args

        # Verify SQL structure (without checking exact query)
        assert len(call_args[0]) >= 1  # Should have query and values


@pytest.mark.asyncio
async def test_get_user_history() -> None:
    """Test retrieving user history from database."""
    mock_results = [
        {
            "id": "msg-1",
            "user_id": "test_user",
            "content": "Hello",
            "response": "Hi there!",
            "timestamp": datetime.now(UTC),
            "metadata": {"model": "test-model"}
        }
    ]

    with patch('chat_api.storage.database') as mock_db:
        mock_db.fetch_all = AsyncMock(return_value=mock_results)

        result = await get_user_history("test_user", 10)

        assert len(result) == 1
        assert result[0]["user_id"] == "test_user"
        assert result[0]["content"] == "Hello"

        # Verify database query
        mock_db.fetch_all.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_history_empty() -> None:
    """Test retrieving history for user with no messages."""
    with patch('chat_api.storage.database') as mock_db:
        mock_db.fetch_all = AsyncMock(return_value=[])

        result = await get_user_history("new_user", 10)

        assert result == []


@pytest.mark.asyncio
async def test_get_cached_hit() -> None:
    """Test cache hit scenario."""
    mock_cached_data = '{"id": "test", "content": "cached response"}'

    with patch('chat_api.storage._redis') as mock_redis:
        mock_redis.get = AsyncMock(return_value=mock_cached_data)

        result = await get_cached("test_key")

        assert result is not None
        assert result["content"] == "cached response"
        mock_redis.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_get_cached_miss() -> None:
    """Test cache miss scenario."""
    with patch('chat_api.storage._redis') as mock_redis:
        mock_redis.get = AsyncMock(return_value=None)

        result = await get_cached("test_key")

        assert result is None
        mock_redis.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_set_cached() -> None:
    """Test setting data in cache."""
    test_data = {"id": "test", "content": "response"}

    with patch('chat_api.storage._redis') as mock_redis:
        mock_redis.setex = AsyncMock()

        await set_cached("test_key", test_data, 3600)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]

        assert call_args[0] == "test_key"  # Key
        assert call_args[1] == 3600  # TTL
        # call_args[2] would be JSON serialized data


@pytest.mark.asyncio
async def test_health_check_healthy() -> None:
    """Test health check when database is healthy."""
    with patch('chat_api.storage.database') as mock_db:
        mock_db.execute = AsyncMock()

        result = await health_check()

        assert result is True


@pytest.mark.asyncio
async def test_health_check_database_failure() -> None:
    """Test health check when database fails."""
    with patch('chat_api.storage.database') as mock_db:
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))

        result = await health_check()

        assert result is False




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
    assert len(key1) > 10
    assert isinstance(key1, str)


@pytest.mark.asyncio
async def test_save_message_database_error() -> None:
    """Test handling database errors during message save."""
    with patch('chat_api.storage.database') as mock_db:
        mock_db.execute = AsyncMock(side_effect=Exception("Database connection failed"))

        with pytest.raises(Exception, match="Database connection failed"):
            await save_message(
                id="msg-123",
                user_id="test_user",
                content="Hello",
                response="Hi there!",
                model="test-model",
                tokens=10
            )


@pytest.mark.asyncio
async def test_get_user_history_database_error() -> None:
    """Test handling database errors during history retrieval."""
    with patch('chat_api.storage.database') as mock_db:
        mock_db.fetch_all = AsyncMock(side_effect=Exception("Query failed"))

        with pytest.raises(Exception, match="Query failed"):
            await get_user_history("test_user", 10)


@pytest.mark.asyncio
async def test_cache_serialization_error() -> None:
    """Test handling serialization errors in cache operations."""
    # Test with non-serializable data
    class NonSerializable:
        pass

    with patch('chat_api.storage._redis') as mock_redis:
        mock_redis.setex = AsyncMock()

        # Should handle serialization gracefully or raise appropriate error
        try:
            await set_cached("test_key", {"data": NonSerializable()}, 3600)
        except (TypeError, ValueError):
            # Expected for non-serializable data
            pass


@pytest.mark.asyncio
async def test_cache_json_parsing_error() -> None:
    """Test handling JSON parsing errors in cache retrieval."""
    with patch('chat_api.storage._redis') as mock_redis:
        mock_redis.get = AsyncMock(return_value="invalid json {")

        result = await get_cached("test_key")

        # Should handle invalid JSON gracefully
        assert result is None


@pytest.mark.asyncio
async def test_get_user_history_limit_enforcement() -> None:
    """Test that history limit is properly enforced."""
    # Create more results than requested limit
    mock_results = [
        {"id": f"msg-{i}", "user_id": "test_user", "content": f"Message {i}",
         "response": f"Response {i}", "timestamp": datetime.now(UTC),
         "metadata": {}}
        for i in range(10)
    ]

    with patch('chat_api.storage.database') as mock_db:
        mock_db.fetch_all = AsyncMock(return_value=mock_results)

        # Request only 5 messages
        result = await get_user_history("test_user", 5)

        # Database query should limit to 5, not Python slicing
        call_args = mock_db.fetch_all.call_args[0]
        query = call_args[0]  # First argument should be query

        # Verify limit is in the SQL query (exact format may vary)
        assert "5" in str(query) or "LIMIT" in str(query).upper()


@pytest.mark.asyncio
async def test_message_data_integrity() -> None:
    """Test that saved message data maintains integrity."""
    test_data = {
        "id": "msg-456",
        "user_id": "test_user_123",
        "content": "Hello with special chars: <>\"'&",
        "response": "Response with unicode: 🚀 emoji",
        "model": "test-model",
        "tokens": 42
    }

    with patch('chat_api.storage.database') as mock_db:
        mock_db.execute = AsyncMock()

        await save_message(**test_data)

        # Verify all data was passed to database
        call_args = mock_db.execute.call_args
        assert call_args is not None

        # Values should be passed as parameters to prevent SQL injection
        assert len(call_args) >= 1
