"""Tests for LLM provider functionality."""

import os
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from chat_api.exceptions import ConfigurationError, LLMProviderError
from chat_api.providers import LLMConfig, LLMResponse, create_llm_provider


class TestLLMConfig:
    """Test LLM configuration."""

    def test_creation_with_defaults(self):
        """Test LLM config creation with defaults."""
        config = LLMConfig(model="gemini/gemini-1.5-flash")

        assert config.model == "gemini/gemini-1.5-flash"
        assert config.temperature == 0.1
        assert config.timeout == 30
        assert config.seed == 42
        assert config.api_key is None


class TestLLMResponse:
    """Test LLM response model."""

    def test_basic_response(self):
        """Test basic LLM response creation."""
        response = LLMResponse(text="Test response", model="test-model", usage={"total_tokens": 10})

        assert response.text == "Test response"
        assert response.model == "test-model"
        assert response.usage == {"total_tokens": 10}

    def test_response_with_cost(self):
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


class TestSimpleLLMProvider:
    """Test SimpleLLMProvider implementation."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test provider health check only checks config."""
        from chat_api.providers import SimpleLLMProvider

        config = LLMConfig(model="test-model", api_key="test-key")
        provider = SimpleLLMProvider(config, "TestProvider")

        # Health check should return True when configured
        result = await provider.health_check()
        assert result is True

        # Health check should return False when no API key
        provider.config.api_key = None
        result = await provider.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_complete_success(self):
        """Test successful LLM completion."""
        from chat_api.providers import SimpleLLMProvider

        config = LLMConfig(model="test-model", api_key="test-key")
        provider = SimpleLLMProvider(config, "TestProvider")

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Hello world"))]
        mock_response.model = "test-model"

        # Create a mock usage object with model_dump method
        mock_usage = Mock()
        mock_usage.model_dump = Mock(
            return_value={
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            }
        )
        mock_response.usage = mock_usage

        with patch("chat_api.providers.litellm.acompletion", return_value=mock_response):
            result = await provider.complete("Test prompt")

            assert isinstance(result, LLMResponse)
            assert result.text == "Hello world"
            assert result.model == "test-model"
            assert result.usage["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_complete_empty_response(self):
        """Test handling of empty LLM response."""
        from chat_api.providers import SimpleLLMProvider

        config = LLMConfig(model="test-model", api_key="test-key")
        provider = SimpleLLMProvider(config, "TestProvider")

        mock_response = Mock()
        mock_response.choices = []
        mock_response.usage = None

        with (
            patch("chat_api.providers.litellm.acompletion", return_value=mock_response),
            pytest.raises((LLMProviderError, IndexError)),
        ):
            await provider.complete("Test prompt")

    @pytest.mark.asyncio
    async def test_complete_api_error(self):
        """Test handling of API errors during completion."""
        from chat_api.providers import SimpleLLMProvider

        config = LLMConfig(model="test-model", api_key="test-key")
        provider = SimpleLLMProvider(config, "TestProvider")

        with (
            patch("chat_api.providers.litellm.acompletion", side_effect=Exception("API Error")),
            pytest.raises(LLMProviderError, match="LLM request failed"),
        ):
            await provider.complete("Test prompt")

    @pytest.mark.asyncio
    async def test_complete_with_system_prompt(self):
        """Test completion with system prompt."""
        from chat_api.providers import SimpleLLMProvider

        config = LLMConfig(
            model="test-model",
            api_key="test-key",
            system_prompt="You are a helpful assistant",
        )
        provider = SimpleLLMProvider(config, "TestProvider")

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Response"))]
        mock_response.model = "test-model"

        # Create a mock usage object with model_dump method
        mock_usage = Mock()
        mock_usage.model_dump = Mock(return_value={"total_tokens": 10})
        mock_response.usage = mock_usage

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
    async def test_complete_with_cost_calculation(self):
        """Test completion with cost calculation."""
        from chat_api.providers import SimpleLLMProvider

        config = LLMConfig(model="gpt-4", api_key="test-key")
        provider = SimpleLLMProvider(config, "TestProvider")

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Response"))]
        mock_response.model = "gpt-4"

        # Create a mock usage object with model_dump method
        mock_usage = Mock()
        mock_usage.model_dump = Mock(
            return_value={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            }
        )
        mock_response.usage = mock_usage

        with (
            patch("chat_api.providers.litellm.acompletion", return_value=mock_response),
            patch("chat_api.providers.litellm.completion_cost", return_value=0.005),
        ):
            result = await provider.complete("Test")
            assert result.usage["total_tokens"] == 150


class TestProviderFactory:
    """Test provider factory function."""

    def test_create_provider_with_env(self):
        """Test creating provider from environment variables."""
        with patch.dict(
            os.environ,
            {"CHAT_LLM_PROVIDER": "openrouter", "CHAT_OPENROUTER_API_KEY": "test-key"},
        ):
            from chat_api.config import Settings

            test_settings = Settings()

            with patch("chat_api.providers.settings", test_settings):
                provider = create_llm_provider()
                assert provider.config.api_key == "test-key"

    def test_create_provider_no_keys(self):
        """Test creating provider with no API keys raises error."""
        with patch("chat_api.providers.settings") as mock_settings:
            mock_settings.gemini_api_key = None
            mock_settings.openrouter_api_key = None

            with pytest.raises(ConfigurationError, match="No LLM provider configured"):
                create_llm_provider()

    def test_create_provider_gemini(self):
        """Test creating Gemini provider."""
        with patch("chat_api.providers.settings") as mock_settings:
            mock_settings.gemini_api_key = "test-key"
            mock_settings.openrouter_api_key = None
            mock_settings.gemini_model = "gemini/gemini-1.5-flash"
            mock_settings.llm_timeout = 30

            provider = create_llm_provider()
            assert provider.config.api_key == "test-key"
            assert provider.config.model == "gemini/gemini-1.5-flash"

    def test_create_provider_openrouter(self):
        """Test creating OpenRouter provider."""
        with patch("chat_api.providers.settings") as mock_settings:
            mock_settings.gemini_api_key = None
            mock_settings.openrouter_api_key = "test-key"
            mock_settings.openrouter_model = "meta-llama/llama-3.2-1b"
            mock_settings.llm_timeout = 30

            provider = create_llm_provider()
            assert provider.config.api_key == "test-key"
            assert provider.config.model == "meta-llama/llama-3.2-1b"
