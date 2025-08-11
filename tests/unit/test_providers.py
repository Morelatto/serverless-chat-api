"""Simple unit tests for provider functionality."""

import os
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from chat_api.exceptions import ConfigurationError
from chat_api.providers import LLMConfig, LLMResponse, create_llm_provider


def test_llm_config_creation():
    """Test LLM config creation with defaults."""
    config = LLMConfig(model="gemini/gemini-1.5-flash")

    assert config.model == "gemini/gemini-1.5-flash"
    assert config.temperature == 0.1  # Actual default
    assert config.timeout == 30  # Actual default
    assert config.seed == 42  # Actual default
    assert config.api_key is None  # No key set


def test_llm_response_creation():
    """Test LLM response creation."""
    response = LLMResponse(text="Test response", model="test-model", usage={"total_tokens": 10})

    assert response.text == "Test response"
    assert response.model == "test-model"
    assert response.usage == {"total_tokens": 10}


def test_llm_response_with_cost():
    """Test LLM response with cost information."""
    response = LLMResponse(
        text="Test response",
        model="test-model",
        usage={
            "prompt_tokens": 5,
            "completion_tokens": 5,
            "total_tokens": 10,
            "cost_usd": Decimal("0.001"),
        },
    )

    assert response.usage["cost_usd"] == Decimal("0.001")
    assert response.usage["prompt_tokens"] == 5


@pytest.mark.asyncio
async def test_provider_health_check():
    """Test provider health check only checks config."""
    # Import the class locally since it's not exported
    from chat_api.providers import SimpleLLMProvider

    config = LLMConfig(model="test-model", api_key="test-key")
    provider = SimpleLLMProvider(config)

    # Health check should return True when configured
    result = await provider.health_check()
    assert result is True

    # Health check should return False when no API key
    provider.config.api_key = None
    result = await provider.health_check()
    assert result is False


@pytest.mark.asyncio
async def test_provider_complete():
    """Test provider complete method."""
    from chat_api.providers import SimpleLLMProvider

    config = LLMConfig(model="test-model", api_key="test-key")
    provider = SimpleLLMProvider(config)

    # Mock the litellm completion
    with patch("chat_api.providers.litellm.acompletion") as mock_completion:
        mock_completion.return_value = AsyncMock(
            choices=[AsyncMock(message=AsyncMock(content="Test response"))],
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )

        result = await provider.complete("Test prompt")

        assert result.text == "Test response"
        assert result.model == "test-model"
        assert result.usage["total_tokens"] == 30

        # Verify litellm was called correctly
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["messages"][0]["content"] == "Test prompt"


def test_create_llm_provider_with_env():
    """Test creating provider from environment."""
    with patch.dict(
        os.environ, {"CHAT_LLM_PROVIDER": "openrouter", "CHAT_OPENROUTER_API_KEY": "test-key"}
    ):
        # Need to reload settings to pick up env vars
        from chat_api.config import Settings

        test_settings = Settings()

        with patch("chat_api.providers.settings", test_settings):
            provider = create_llm_provider()
            assert provider.config.api_key == "test-key"


def test_create_llm_provider_no_keys():
    """Test creating provider with no API keys raises error."""
    with (
        patch.dict(
            os.environ, {"CHAT_LLM_PROVIDER": "gemini", "CHAT_GEMINI_API_KEY": ""}, clear=True
        ),
        pytest.raises(ConfigurationError, match="No LLM provider configured"),
    ):
        create_llm_provider()
