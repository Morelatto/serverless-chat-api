"""Test core business logic."""

from unittest.mock import AsyncMock, patch

import pytest

from chat_api.core import health_check, process_message


@pytest.mark.asyncio
@patch("chat_api.core._call_llm")
async def test_process_message(mock_call_llm: AsyncMock) -> None:
    """Test message processing."""
    # Create mock repository and cache
    mock_repo = AsyncMock()
    mock_cache = AsyncMock()

    # Mock LLM response
    mock_llm_response = {
        "text": "Hello! How can I help you?",
        "model": "test-model",
        "usage": {"total_tokens": 10},
    }
    mock_call_llm.return_value = mock_llm_response

    # No cache hit
    mock_cache.get.return_value = None
    mock_cache.set.return_value = None
    mock_repo.save.return_value = None

    result = await process_message("user123", "Hello", mock_repo, mock_cache)

    assert "id" in result
    assert result["content"] == "Hello! How can I help you?"
    assert result["cached"] is False
    assert result["model"] == "test-model"

    # Verify calls
    mock_call_llm.assert_called_once_with("Hello")
    mock_repo.save.assert_called_once()
    mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_process_message_cached() -> None:
    """Test message processing with cache hit."""
    # Create mock repository and cache
    mock_repo = AsyncMock()
    mock_cache = AsyncMock()

    # Mock cache hit
    cached_result = {
        "id": "cached-123",
        "content": "Cached response",
        "model": "cached-model",
        "cached": False,
    }
    mock_cache.get.return_value = cached_result

    result = await process_message("user123", "Hello", mock_repo, mock_cache)

    assert result["id"] == "cached-123"
    assert result["cached"] is True

    # Should not call repository or LLM when cached
    mock_repo.save.assert_not_called()


@pytest.mark.asyncio
@patch("chat_api.core.settings")
async def test_health_check(mock_settings: AsyncMock) -> None:
    """Test health check."""
    mock_repo = AsyncMock()
    mock_repo.health_check.return_value = True
    # Valid LLM configuration
    mock_settings.llm_provider = "openrouter"
    mock_settings.openrouter_api_key = "test-key"
    mock_settings.llm_model = "openrouter/test-model"

    result = await health_check(mock_repo)

    assert result["storage"] is True
    assert result["llm"] is True


@pytest.mark.asyncio
@patch("chat_api.core.settings")
async def test_health_check_llm_failure(mock_settings: AsyncMock) -> None:
    """Test health check with LLM failure."""
    mock_repo = AsyncMock()
    mock_repo.health_check.return_value = True
    # Simulate missing API key
    mock_settings.llm_provider = "openrouter"
    mock_settings.openrouter_api_key = None
    mock_settings.llm_model = "openrouter/test-model"

    result = await health_check(mock_repo)

    assert result["storage"] is True
    assert result["llm"] is False


@pytest.mark.asyncio
@patch("chat_api.core.settings")
async def test_health_check_storage_failure(mock_settings: AsyncMock) -> None:
    """Test health check with storage failure."""
    mock_repo = AsyncMock()
    mock_repo.health_check.return_value = False
    # Valid LLM configuration
    mock_settings.llm_provider = "openrouter"
    mock_settings.openrouter_api_key = "test-key"
    mock_settings.llm_model = "openrouter/test-model"

    result = await health_check(mock_repo)

    assert result["storage"] is False
    assert result["llm"] is True


@pytest.mark.asyncio
@patch("chat_api.core.cache_key")
async def test_process_message_cache_key_generation(mock_cache_key: AsyncMock) -> None:
    """Test that cache key is properly generated."""
    mock_repo = AsyncMock()
    mock_cache = AsyncMock()

    mock_cache_key.return_value = "test-cache-key"
    mock_cache.get.return_value = None

    # This will fail on the LLM call but we want to test cache key generation
    with (
        patch("chat_api.core._call_llm", side_effect=Exception("Stop here")),
        pytest.raises(Exception, match="Stop here"),
    ):
        await process_message("user123", "Hello", mock_repo, mock_cache)

    mock_cache_key.assert_called_once_with("user123", "Hello")
    mock_cache.get.assert_called_once_with("test-cache-key")


@pytest.mark.asyncio
@patch("chat_api.core._call_llm")
async def test_call_llm_error_handling(mock_call_llm: AsyncMock) -> None:
    """Test that _call_llm errors are properly propagated."""
    mock_repo = AsyncMock()
    mock_cache = AsyncMock()

    mock_call_llm.side_effect = Exception("LLM API error")
    mock_cache.get.return_value = None

    with pytest.raises(Exception, match="LLM API error"):
        await process_message("user123", "Hello", mock_repo, mock_cache)


@pytest.mark.asyncio
@patch("chat_api.core._call_llm")
async def test_process_message_full_flow(mock_call_llm: AsyncMock) -> None:
    """Test complete message processing flow."""
    mock_repo = AsyncMock()
    mock_cache = AsyncMock()

    # Mock LLM response
    mock_llm_response = {
        "text": "Generated response",
        "model": "gpt-4",
        "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
    }
    mock_call_llm.return_value = mock_llm_response

    # No cache hit
    mock_cache.get.return_value = None

    result = await process_message("user456", "Test message", mock_repo, mock_cache)

    # Verify result structure
    assert "id" in result
    assert len(result["id"]) > 0  # UUID should be generated
    assert result["content"] == "Generated response"
    assert result["model"] == "gpt-4"
    assert result["cached"] is False

    # Verify save_message was called with correct parameters
    save_call_args = mock_repo.save.call_args[1]  # keyword arguments
    assert save_call_args["user_id"] == "user456"
    assert save_call_args["content"] == "Test message"
    assert save_call_args["response"] == "Generated response"
    assert save_call_args["model"] == "gpt-4"
    assert save_call_args["usage"] == mock_llm_response["usage"]

    # Verify caching
    mock_cache.set.assert_called_once()
    cache_call_args = mock_cache.set.call_args[0]  # positional arguments
    assert len(cache_call_args) >= 2  # key and value
