"""Test LLM providers."""

from unittest.mock import MagicMock, patch

import pytest

from chat_api.exceptions import ConfigurationError
from chat_api.providers import (
    GeminiProvider,
    LLMConfig,
    LLMResponse,
    OpenRouterProvider,
    create_llm_provider,
)


@pytest.fixture
def llm_config() -> LLMConfig:
    """Create test LLM config."""
    return LLMConfig(
        model="test-model",
        api_key="test-api-key",
        temperature=0.5,
        timeout=30,
        max_retries=3,
        retry_min_wait=1,
        retry_max_wait=10,
        seed=42,
    )


@pytest.mark.asyncio
async def test_gemini_provider_complete(llm_config: LLMConfig) -> None:
    """Test Gemini provider completion."""
    provider = GeminiProvider(llm_config)

    with patch("litellm.acompletion") as mock_completion:
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Test response"))],
            model="gemini/gemini-1.5-flash",
            usage={"total_tokens": 50},
        )

        response = await provider.complete("Test prompt")

        assert isinstance(response, LLMResponse)
        assert response.text == "Test response"
        assert response.model == "gemini/gemini-1.5-flash"
        assert response.usage == {"total_tokens": 50}

        # Check that litellm was called with expected args
        mock_completion.assert_called_once()
        call_args = mock_completion.call_args[1]
        assert call_args["model"] == "gemini/test-model"
        assert call_args["messages"] == [{"role": "user", "content": "Test prompt"}]
        assert call_args["api_key"] == "test-api-key"
        assert call_args["temperature"] == 0.5
        assert call_args["timeout"] == 30
        assert call_args["seed"] == 42


@pytest.mark.asyncio
async def test_openrouter_provider_complete(llm_config: LLMConfig) -> None:
    """Test OpenRouter provider completion."""
    provider = OpenRouterProvider(llm_config)

    with patch("litellm.acompletion") as mock_completion:
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="OpenRouter response"))],
            model="openrouter/test-model",
            usage={"total_tokens": 75},
        )

        response = await provider.complete("Test prompt")

        assert isinstance(response, LLMResponse)
        assert response.text == "OpenRouter response"
        assert response.model == "openrouter/test-model"
        assert response.usage == {"total_tokens": 75}

        # Check that litellm was called with expected args
        mock_completion.assert_called_once()
        call_args = mock_completion.call_args[1]
        assert call_args["model"] == "openrouter/test-model"
        assert call_args["messages"] == [{"role": "user", "content": "Test prompt"}]
        assert call_args["api_key"] == "test-api-key"
        assert call_args["temperature"] == 0.5
        assert call_args["timeout"] == 30
        assert call_args["seed"] == 42


@pytest.mark.asyncio
async def test_provider_retry_logic(llm_config: LLMConfig) -> None:
    """Test provider retry logic on failures."""
    provider = GeminiProvider(llm_config)

    with patch("litellm.acompletion") as mock_completion:
        # First two calls fail, third succeeds
        mock_completion.side_effect = [
            Exception("API error"),
            Exception("Timeout"),
            MagicMock(
                choices=[MagicMock(message=MagicMock(content="Success after retry"))],
                model="gemini/test-model",
                usage={},
            ),
        ]

        with patch("asyncio.sleep") as mock_sleep:
            response = await provider.complete("Test prompt")

            assert response.text == "Success after retry"
            assert mock_completion.call_count == 3
            # Check exponential backoff was used
            assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_provider_max_retries_exceeded(llm_config: LLMConfig) -> None:
    """Test provider fails after max retries."""
    provider = GeminiProvider(llm_config)

    with patch("litellm.acompletion") as mock_completion:
        mock_completion.side_effect = Exception("Persistent error")

        with patch("asyncio.sleep"), pytest.raises(Exception, match="Persistent error"):
            await provider.complete("Test prompt")

        # Should have tried max_retries times
        assert mock_completion.call_count == llm_config.max_retries


@pytest.mark.asyncio
async def test_gemini_health_check() -> None:
    """Test Gemini provider health check."""
    config = LLMConfig(api_key="test-key", model="test-model")
    provider = GeminiProvider(config)

    with patch("litellm.acompletion") as mock_completion:
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="ok"))],
        )

        result = await provider.health_check()
        assert result is True

        # Check that health check was called
        mock_completion.assert_called_once()
        call_args = mock_completion.call_args[1]
        assert call_args["model"] == "gemini/test-model"
        assert call_args["messages"] == [{"role": "user", "content": "ping"}]
        assert call_args["api_key"] == "test-key"
        assert call_args["timeout"] == 5


@pytest.mark.asyncio
async def test_openrouter_health_check() -> None:
    """Test OpenRouter provider health check."""
    config = LLMConfig(api_key="test-key", model="test-model")
    provider = OpenRouterProvider(config)

    with patch("litellm.acompletion") as mock_completion:
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="ok"))],
        )

        result = await provider.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_provider_health_check_failure() -> None:
    """Test provider health check failure."""
    config = LLMConfig(model="test-model", api_key="test-key")
    provider = GeminiProvider(config)

    with patch("litellm.acompletion") as mock_completion:
        mock_completion.side_effect = Exception("API down")

        result = await provider.health_check()
        assert result is False


def test_create_llm_provider_gemini() -> None:
    """Test creating Gemini provider."""
    provider = create_llm_provider(
        provider_type="gemini",
        model="gemini-1.5-flash",
        api_key="test-key",
    )

    assert isinstance(provider, GeminiProvider)
    assert provider.config.model == "gemini-1.5-flash"
    assert provider.config.api_key == "test-key"


def test_create_llm_provider_openrouter() -> None:
    """Test creating OpenRouter provider."""
    provider = create_llm_provider(
        provider_type="openrouter",
        model="gpt-4",
        api_key="test-key",
    )

    assert isinstance(provider, OpenRouterProvider)
    assert provider.config.model == "gpt-4"
    assert provider.config.api_key == "test-key"


def test_create_llm_provider_invalid() -> None:
    """Test creating provider with invalid type."""
    with pytest.raises(ConfigurationError, match="Unknown provider type: invalid"):
        create_llm_provider(
            provider_type="invalid",
            model="test-model",
            api_key="test-key",
        )


def test_create_llm_provider_custom_params() -> None:
    """Test creating provider with custom parameters."""
    provider = create_llm_provider(
        provider_type="gemini",
        model="test-model",
        api_key="test-key",
        temperature=0.2,
        timeout=60,
        max_retries=5,
    )

    assert provider.config.temperature == 0.2
    assert provider.config.timeout == 60
    assert provider.config.max_retries == 5


@pytest.mark.asyncio
async def test_provider_empty_response_handling(llm_config: LLMConfig) -> None:
    """Test provider handles empty response."""
    provider = GeminiProvider(llm_config)

    with patch("litellm.acompletion") as mock_completion:
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=""))],
            model="gemini/test-model",
            usage={},
        )

        response = await provider.complete("Test prompt")
        assert response.text == ""


@pytest.mark.asyncio
async def test_provider_none_usage_handling(llm_config: LLMConfig) -> None:
    """Test provider handles None usage data."""
    provider = GeminiProvider(llm_config)

    with patch("litellm.acompletion") as mock_completion:
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Response"))],
            model="gemini/test-model",
            usage=None,
        )

        response = await provider.complete("Test prompt")
        assert response.usage == {}


@pytest.mark.asyncio
async def test_provider_partial_usage_data(llm_config: LLMConfig) -> None:
    """Test provider handles partial usage data."""
    provider = OpenRouterProvider(llm_config)

    with patch("litellm.acompletion") as mock_completion:
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Response"))],
            model="openrouter/test-model",
            usage={"prompt_tokens": 10},  # Missing completion_tokens
        )

        response = await provider.complete("Test prompt")
        assert response.usage == {"prompt_tokens": 10}


@pytest.mark.asyncio
async def test_provider_model_fallback(llm_config: LLMConfig) -> None:
    """Test provider model name fallback."""
    provider = GeminiProvider(llm_config)

    with patch("litellm.acompletion") as mock_completion:
        # Response doesn't include model field
        response_mock = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Response"))],
            usage={},
        )
        del response_mock.model  # Remove model attribute
        mock_completion.return_value = response_mock

        response = await provider.complete("Test prompt")
        # Should fallback to configured model
        assert response.model == "gemini/test-model"
