"""Test ChatService core business logic."""

from unittest.mock import AsyncMock, patch

import pytest

from chat_api.chat import ChatService
from chat_api.exceptions import LLMProviderError, StorageError
from chat_api.providers import LLMResponse
from chat_api.storage import cache_key


@pytest.mark.asyncio
async def test_process_message_cache_miss() -> None:
    """Test message processing with cache miss - full flow."""
    # Create mocks
    mock_repository = AsyncMock()
    mock_cache = AsyncMock()
    mock_llm_provider = AsyncMock()

    # Setup cache miss
    mock_cache.get.return_value = None

    # Setup LLM response
    mock_llm_provider.complete.return_value = LLMResponse(
        text="Hello! How can I help you?",
        model="gemini-1.5-flash",
        usage={"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
    )

    service = ChatService(mock_repository, mock_cache, mock_llm_provider)

    # Process message
    result = await service.process_message("user123", "Hello")

    # Verify result
    assert "id" in result
    assert len(result["id"]) > 0  # UUID generated
    assert result["content"] == "Hello! How can I help you?"
    assert result["model"] == "gemini-1.5-flash"
    assert result["cached"] is False

    # Verify calls
    mock_cache.get.assert_called_once_with(cache_key("user123", "Hello"))
    mock_llm_provider.complete.assert_called_once_with("Hello")
    mock_repository.save.assert_called_once()

    # Verify save arguments
    save_args = mock_repository.save.call_args.kwargs
    assert save_args["user_id"] == "user123"
    assert save_args["content"] == "Hello"
    assert save_args["response"] == "Hello! How can I help you?"
    assert save_args["model"] == "gemini-1.5-flash"
    assert save_args["usage"] == {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}

    # Verify cache set
    mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_process_message_cache_hit() -> None:
    """Test message processing with cache hit."""
    mock_repository = AsyncMock()
    mock_cache = AsyncMock()
    mock_llm_provider = AsyncMock()

    # Setup cache hit
    cached_result = {
        "id": "cached-123",
        "content": "Cached response",
        "model": "cached-model",
        "cached": False,
    }
    mock_cache.get.return_value = cached_result

    service = ChatService(mock_repository, mock_cache, mock_llm_provider)
    result = await service.process_message("user123", "Hello")

    # Should return cached result with cached=True
    assert result["id"] == "cached-123"
    assert result["content"] == "Cached response"
    assert result["model"] == "cached-model"
    assert result["cached"] is True

    # Should not call LLM or save to repository
    mock_llm_provider.complete.assert_not_called()
    mock_repository.save.assert_not_called()
    mock_cache.set.assert_not_called()


@pytest.mark.asyncio
async def test_process_message_llm_error() -> None:
    """Test handling of LLM provider errors."""
    mock_repository = AsyncMock()
    mock_cache = AsyncMock()
    mock_llm_provider = AsyncMock()

    # Setup cache miss and LLM error
    mock_cache.get.return_value = None
    mock_llm_provider.complete.side_effect = LLMProviderError("API rate limit exceeded")

    service = ChatService(mock_repository, mock_cache, mock_llm_provider)

    # Should propagate LLM error
    with pytest.raises(LLMProviderError, match="API rate limit exceeded"):
        await service.process_message("user123", "Hello")

    # Should not save or cache on error
    mock_repository.save.assert_not_called()
    mock_cache.set.assert_not_called()


@pytest.mark.asyncio
async def test_process_message_storage_error() -> None:
    """Test handling of storage errors."""
    mock_repository = AsyncMock()
    mock_cache = AsyncMock()
    mock_llm_provider = AsyncMock()

    # Setup successful LLM call but storage failure
    mock_cache.get.return_value = None
    mock_llm_provider.complete.return_value = LLMResponse(
        text="Response text",
        model="test-model",
        usage={"total_tokens": 10},
    )
    mock_repository.save.side_effect = StorageError("Database connection failed")

    service = ChatService(mock_repository, mock_cache, mock_llm_provider)

    # Should propagate storage error
    with pytest.raises(StorageError, match="Database connection failed"):
        await service.process_message("user123", "Hello")

    # LLM should have been called, but cache should not be set on storage error
    mock_llm_provider.complete.assert_called_once()
    mock_cache.set.assert_not_called()


@pytest.mark.asyncio
async def test_get_history() -> None:
    """Test retrieving user history."""
    mock_repository = AsyncMock()
    mock_cache = AsyncMock()
    mock_llm_provider = AsyncMock()

    # Setup repository response
    history_data = [
        {"id": "msg-1", "content": "Hello", "response": "Hi", "timestamp": "2025-01-01T00:00:00Z"},
        {
            "id": "msg-2",
            "content": "How are you?",
            "response": "I'm good",
            "timestamp": "2025-01-01T00:01:00Z",
        },
    ]
    mock_repository.get_history.return_value = history_data

    service = ChatService(mock_repository, mock_cache, mock_llm_provider)
    result = await service.get_history("user123", 10)

    assert result == history_data
    mock_repository.get_history.assert_called_once_with("user123", 10)


@pytest.mark.asyncio
async def test_health_check_all_healthy() -> None:
    """Test health check when all components are healthy."""
    mock_repository = AsyncMock()
    mock_cache = AsyncMock()
    mock_llm_provider = AsyncMock()

    # Setup healthy responses
    mock_repository.health_check.return_value = True
    mock_llm_provider.health_check.return_value = True

    service = ChatService(mock_repository, mock_cache, mock_llm_provider)
    result = await service.health_check()

    assert result == {"storage": True, "llm": True, "cache": True}


@pytest.mark.asyncio
async def test_health_check_storage_unhealthy() -> None:
    """Test health check when storage is unhealthy."""
    mock_repository = AsyncMock()
    mock_cache = AsyncMock()
    mock_llm_provider = AsyncMock()

    # Storage fails, LLM is healthy
    mock_repository.health_check.return_value = False
    mock_llm_provider.health_check.return_value = True

    service = ChatService(mock_repository, mock_cache, mock_llm_provider)
    result = await service.health_check()

    assert result == {"storage": False, "llm": True, "cache": True}


@pytest.mark.asyncio
async def test_health_check_llm_unhealthy() -> None:
    """Test health check when LLM provider is unhealthy."""
    mock_repository = AsyncMock()
    mock_cache = AsyncMock()
    mock_llm_provider = AsyncMock()

    # LLM fails, storage is healthy
    mock_repository.health_check.return_value = True
    mock_llm_provider.health_check.return_value = False

    service = ChatService(mock_repository, mock_cache, mock_llm_provider)
    result = await service.health_check()

    assert result == {"storage": True, "llm": False, "cache": True}


@pytest.mark.asyncio
async def test_process_message_generates_unique_ids() -> None:
    """Test that each message gets a unique ID."""
    mock_repository = AsyncMock()
    mock_cache = AsyncMock()
    mock_llm_provider = AsyncMock()

    # Setup cache miss and LLM response
    mock_cache.get.return_value = None
    mock_llm_provider.complete.return_value = LLMResponse(
        text="Response",
        model="test-model",
        usage={"total_tokens": 5},
    )

    service = ChatService(mock_repository, mock_cache, mock_llm_provider)

    # Process multiple messages
    result1 = await service.process_message("user1", "Hello")
    result2 = await service.process_message("user2", "Hi")

    # Should generate different UUIDs
    assert result1["id"] != result2["id"]
    assert len(result1["id"]) > 0
    assert len(result2["id"]) > 0

    # Both should be valid UUID format (36 chars with dashes)
    assert len(result1["id"]) == 36
    assert len(result2["id"]) == 36


@pytest.mark.asyncio
async def test_process_message_with_usage_logging() -> None:
    """Test that token usage is properly logged."""
    mock_repository = AsyncMock()
    mock_cache = AsyncMock()
    mock_llm_provider = AsyncMock()

    mock_cache.get.return_value = None
    mock_llm_provider.complete.return_value = LLMResponse(
        text="Test response",
        model="gpt-4",
        usage={
            "prompt_tokens": 15,
            "completion_tokens": 25,
            "total_tokens": 40,
            "cost_usd": "0.0012",
        },
    )

    service = ChatService(mock_repository, mock_cache, mock_llm_provider)

    with patch("chat_api.chat.logger") as mock_logger:
        await service.process_message("user123", "Test message")

        # Verify usage logging
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert "Token usage" in str(log_call[0][0])
        # The extra dict is in kwargs, not args
        extra = log_call.kwargs.get("extra", {})
        assert extra["user_id"] == "user123..."
        assert extra["model"] == "gpt-4"
        assert extra["prompt_tokens"] == 15
        assert extra["completion_tokens"] == 25
        assert extra["total_tokens"] == 40


@pytest.mark.asyncio
async def test_process_message_cache_key_consistency() -> None:
    """Test that cache keys are generated consistently."""
    mock_repository = AsyncMock()
    mock_cache = AsyncMock()
    mock_llm_provider = AsyncMock()

    # Setup cache miss then hit
    mock_cache.get.side_effect = [None, {"id": "cached", "content": "cached", "cached": False}]
    mock_llm_provider.complete.return_value = LLMResponse(
        text="Response",
        model="test",
        usage={"total_tokens": 5},
    )

    service = ChatService(mock_repository, mock_cache, mock_llm_provider)

    # First call - cache miss
    await service.process_message("user123", "Hello world")
    first_cache_key = mock_cache.get.call_args_list[0][0][0]

    # Second call - same inputs should use same cache key
    await service.process_message("user123", "Hello world")
    second_cache_key = mock_cache.get.call_args_list[1][0][0]

    assert first_cache_key == second_cache_key
