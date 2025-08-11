"""Test LLM provider complete functionality."""

from unittest.mock import AsyncMock, patch

import pytest

from chat_api.exceptions import LLMProviderError
from chat_api.providers import LLMConfig, LLMResponse


@pytest.mark.asyncio
async def test_provider_complete_success():
    """Test successful LLM completion."""
    from chat_api.providers import SimpleLLMProvider

    config = LLMConfig(model="test-model", api_key="test-key")
    provider = SimpleLLMProvider(config)

    # Mock litellm response
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content="Hello world"))]
    mock_response.model = "test-model"
    mock_response.usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

    with patch("chat_api.providers.litellm.acompletion", return_value=mock_response):
        result = await provider.complete("Test prompt")

        assert isinstance(result, LLMResponse)
        assert result.text == "Hello world"
        assert result.model == "test-model"
        assert result.usage["total_tokens"] == 30


@pytest.mark.asyncio
async def test_provider_complete_empty_response():
    """Test handling of empty LLM response."""
    from chat_api.providers import SimpleLLMProvider

    config = LLMConfig(model="test-model", api_key="test-key")
    provider = SimpleLLMProvider(config)

    # Mock empty response
    mock_response = AsyncMock()
    mock_response.choices = []

    with (
        patch("chat_api.providers.litellm.acompletion", return_value=mock_response),
        pytest.raises(LLMProviderError, match="No response from LLM"),
    ):
        await provider.complete("Test prompt")


@pytest.mark.asyncio
async def test_provider_complete_api_error():
    """Test handling of API errors."""
    from chat_api.providers import SimpleLLMProvider

    config = LLMConfig(model="test-model", api_key="test-key")
    provider = SimpleLLMProvider(config)

    with (
        patch("chat_api.providers.litellm.acompletion", side_effect=Exception("API Error")),
        pytest.raises(LLMProviderError, match="LLM request failed"),
    ):
        await provider.complete("Test prompt")


@pytest.mark.asyncio
async def test_provider_complete_with_system_prompt():
    """Test completion with system prompt."""
    from chat_api.providers import SimpleLLMProvider

    config = LLMConfig(
        model="test-model", api_key="test-key", system_prompt="You are a helpful assistant"
    )
    provider = SimpleLLMProvider(config)

    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content="Response"))]
    mock_response.model = "test-model"
    mock_response.usage = {"total_tokens": 10}

    with patch(
        "chat_api.providers.litellm.acompletion", return_value=mock_response
    ) as mock_complete:
        await provider.complete("User message")

        # Verify system prompt was included
        call_args = mock_complete.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "User message"


@pytest.mark.asyncio
async def test_provider_complete_with_cost():
    """Test completion with cost calculation."""
    from chat_api.providers import SimpleLLMProvider

    config = LLMConfig(model="gpt-4", api_key="test-key")
    provider = SimpleLLMProvider(config)

    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content="Response"))]
    mock_response.model = "gpt-4"
    mock_response.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

    # Mock cost calculation
    with (
        patch("chat_api.providers.litellm.acompletion", return_value=mock_response),
        patch("chat_api.providers.litellm.completion_cost", return_value=0.005),
    ):
        result = await provider.complete("Test")

        assert result.usage["total_tokens"] == 150
        # Cost should be included if litellm provides it
