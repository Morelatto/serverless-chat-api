"""Simple unit tests for provider functionality."""

from decimal import Decimal

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


def test_create_llm_provider_gemini():
    """Test creating Gemini provider."""
    provider = create_llm_provider(
        provider_type="gemini",
        model="gemini/gemini-1.5-flash",
        api_key="test-key",
    )

    assert provider.config.model == "gemini/gemini-1.5-flash"
    assert provider.config.api_key == "test-key"


def test_create_llm_provider_openrouter():
    """Test creating OpenRouter provider."""
    provider = create_llm_provider(
        provider_type="openrouter",
        model="openrouter/test-model",
        api_key="test-key",
    )

    assert provider.config.model == "openrouter/test-model"
    assert provider.config.api_key == "test-key"


def test_create_llm_provider_invalid():
    """Test creating provider with invalid type."""
    with pytest.raises(ConfigurationError, match="Unknown provider type"):
        create_llm_provider(provider_type="invalid", model="some-model", api_key="test-key")
