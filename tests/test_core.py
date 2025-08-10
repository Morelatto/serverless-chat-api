"""Test core business logic (chat module)."""

from unittest.mock import AsyncMock

import pytest

from chat_api.chat import ChatService, process_message_with_deps
from chat_api.exceptions import LLMProviderError
from chat_api.providers import LLMResponse


@pytest.mark.asyncio
async def test_process_message() -> None:
    """Test message processing."""
    # Create mock dependencies
    mock_repo = AsyncMock()
    mock_cache = AsyncMock()
    mock_provider = AsyncMock()

    # Mock provider response
    mock_provider.complete.return_value = LLMResponse(
        text="Hello! How can I help you?",
        model="test-model",
        usage={"total_tokens": 10},
    )

    # No cache hit
    mock_cache.get.return_value = None
    mock_cache.set.return_value = None
    mock_repo.save.return_value = None

    result = await process_message_with_deps(
        "user123",
        "Hello",
        mock_repo,
        mock_cache,
        mock_provider,
    )

    assert "id" in result
    assert result["content"] == "Hello! How can I help you?"
    assert result["cached"] is False
    assert result["model"] == "test-model"

    # Verify calls
    mock_provider.complete.assert_called_once_with("Hello")
    mock_repo.save.assert_called_once()
    mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_process_message_cached() -> None:
    """Test message processing with cache hit."""
    # Create mock dependencies
    mock_repo = AsyncMock()
    mock_cache = AsyncMock()
    mock_provider = AsyncMock()

    # Mock cache hit
    cached_result = {
        "id": "cached-123",
        "content": "Cached response",
        "model": "cached-model",
        "cached": False,
    }
    mock_cache.get.return_value = cached_result

    result = await process_message_with_deps(
        "user123",
        "Hello",
        mock_repo,
        mock_cache,
        mock_provider,
    )

    assert result["id"] == "cached-123"
    assert result["cached"] is True

    # Should not call repository or LLM when cached
    mock_repo.save.assert_not_called()
    mock_provider.complete.assert_not_called()


@pytest.mark.asyncio
async def test_chat_service() -> None:
    """Test ChatService class."""
    # Create mock dependencies
    mock_repo = AsyncMock()
    mock_cache = AsyncMock()
    mock_provider = AsyncMock()

    # Create service
    service = ChatService(mock_repo, mock_cache, mock_provider)

    # Mock provider response
    mock_provider.complete.return_value = LLMResponse(
        text="Service response",
        model="gpt-4",
        usage={"total_tokens": 15},
    )

    # No cache hit
    mock_cache.get.return_value = None

    # Test process_message
    result = await service.process_message("user456", "Test message")

    assert "id" in result
    assert result["content"] == "Service response"
    assert result["model"] == "gpt-4"
    assert result["cached"] is False

    # Test get_history
    mock_repo.get_history.return_value = [
        {"id": "hist-1", "content": "Message 1"},
    ]
    history = await service.get_history("user456")
    assert len(history) == 1
    assert history[0]["id"] == "hist-1"

    # Test health_check
    mock_repo.health_check.return_value = True
    mock_provider.health_check.return_value = True

    health = await service.health_check()
    assert health["storage"] is True
    assert health["llm"] is True


@pytest.mark.asyncio
async def test_health_check_failures() -> None:
    """Test health check with component failures."""
    # Create mock dependencies
    mock_repo = AsyncMock()
    mock_cache = AsyncMock()
    mock_provider = AsyncMock()

    # Create service
    service = ChatService(mock_repo, mock_cache, mock_provider)

    # Storage failure
    mock_repo.health_check.return_value = False
    mock_provider.health_check.return_value = True

    health = await service.health_check()
    assert health["storage"] is False
    assert health["llm"] is True

    # LLM failure - should be caught in health check
    mock_repo.health_check.return_value = True
    mock_provider.health_check.side_effect = LLMProviderError("LLM down")

    health = await service.health_check()
    assert health["storage"] is True
    assert health["llm"] is False


@pytest.mark.asyncio
async def test_cache_key_generation() -> None:
    """Test that cache key is properly generated."""
    from chat_api.storage import cache_key

    # Same inputs should produce same key
    key1 = cache_key("user123", "Hello")
    key2 = cache_key("user123", "Hello")
    assert key1 == key2

    # Different inputs should produce different keys
    key3 = cache_key("user456", "Hello")
    key4 = cache_key("user123", "Goodbye")
    assert key1 != key3
    assert key1 != key4


@pytest.mark.asyncio
async def test_llm_error_handling() -> None:
    """Test that LLM provider errors are properly propagated."""
    # Create mock dependencies
    mock_repo = AsyncMock()
    mock_cache = AsyncMock()
    mock_provider = AsyncMock()

    # Mock provider that fails
    mock_provider.complete.side_effect = Exception("LLM API error")

    # No cache hit
    mock_cache.get.return_value = None

    with pytest.raises(LLMProviderError, match="Failed to generate response"):
        await process_message_with_deps(
            "user123",
            "Hello",
            mock_repo,
            mock_cache,
            mock_provider,
        )


@pytest.mark.asyncio
async def test_process_message_full_flow() -> None:
    """Test complete message processing flow."""
    # Create mock dependencies
    mock_repo = AsyncMock()
    mock_cache = AsyncMock()
    mock_provider = AsyncMock()

    # Mock provider response
    mock_provider.complete.return_value = LLMResponse(
        text="Generated response",
        model="gpt-4",
        usage={"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
    )

    # No cache hit
    mock_cache.get.return_value = None

    result = await process_message_with_deps(
        "user456",
        "Test message",
        mock_repo,
        mock_cache,
        mock_provider,
    )

    # Verify result structure
    assert "id" in result
    assert len(result["id"]) > 0  # UUID should be generated
    assert result["content"] == "Generated response"
    assert result["model"] == "gpt-4"
    assert result["cached"] is False

    # Verify save was called with correct parameters
    save_call_args = mock_repo.save.call_args[1]  # keyword arguments
    assert save_call_args["user_id"] == "user456"
    assert save_call_args["content"] == "Test message"
    assert save_call_args["response"] == "Generated response"
    assert save_call_args["model"] == "gpt-4"
    assert save_call_args["usage"] == {
        "prompt_tokens": 5,
        "completion_tokens": 10,
        "total_tokens": 15,
    }

    # Verify caching
    mock_cache.set.assert_called_once()
    cache_call_args = mock_cache.set.call_args[0]  # positional arguments
    assert len(cache_call_args) >= 2  # key and value
