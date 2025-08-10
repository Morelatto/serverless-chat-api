"""Test LLM provider implementations."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chat_api.exceptions import ConfigurationError, LLMProviderError
from chat_api.providers import GeminiProvider, LLMConfig, OpenRouterProvider, create_llm_provider


class TestLLMConfig:
    """Test LLM configuration."""

    def test_llm_config_defaults(self) -> None:
        """Test LLM config with defaults."""
        config = LLMConfig(model="test-model", api_key="test-key")

        assert config.model == "test-model"
        assert config.api_key == "test-key"
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.temperature == 0.1
        assert config.seed == 42

    def test_llm_config_custom_values(self) -> None:
        """Test LLM config with custom values."""
        config = LLMConfig(
            model="custom-model",
            api_key="custom-key",
            timeout=60,
            max_retries=5,
            temperature=0.7,
            seed=123,
        )

        assert config.model == "custom-model"
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.temperature == 0.7
        assert config.seed == 123


class TestGeminiProvider:
    """Test Gemini provider implementation."""

    def test_initialization_with_api_key(self) -> None:
        """Test Gemini provider initialization with API key."""
        config = LLMConfig(model="gemini-1.5-flash", api_key="test-key")
        provider = GeminiProvider(config)
        assert provider.config.api_key == "test-key"

    def test_initialization_without_api_key(self) -> None:
        """Test Gemini provider initialization fails without API key."""
        config = LLMConfig(model="gemini-1.5-flash", api_key=None)

        with pytest.raises(ConfigurationError, match="Gemini API key is required"):
            GeminiProvider(config)

    @pytest.mark.asyncio
    @patch("chat_api.providers.litellm.acompletion")
    async def test_complete_success(self, mock_acompletion: AsyncMock) -> None:
        """Test successful completion call."""
        # Mock litellm response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello! How can I help you?"
        mock_response.model = "gemini-1.5-flash"
        mock_response.usage.model_dump.return_value = {
            "prompt_tokens": 5,
            "completion_tokens": 10,
            "total_tokens": 15,
        }
        mock_acompletion.return_value = mock_response

        # Mock cost calculation
        with patch("chat_api.providers.litellm.completion_cost", return_value=0.0012):
            config = LLMConfig(model="gemini-1.5-flash", api_key="test-key")
            provider = GeminiProvider(config)

            result = await provider.complete("Hello")

        # Verify result
        assert result.text == "Hello! How can I help you?"
        assert result.model == "gemini-1.5-flash"
        assert result.usage["prompt_tokens"] == 5
        assert result.usage["completion_tokens"] == 10
        assert result.usage["total_tokens"] == 15
        assert result.usage["cost_usd"] == Decimal("0.0012")

        # Verify litellm call
        mock_acompletion.assert_called_once_with(
            model="gemini-1.5-flash",
            messages=[{"role": "user", "content": "Hello"}],
            timeout=30,
            api_key="test-key",
            temperature=0.1,
            seed=42,
        )

    @pytest.mark.asyncio
    @patch("chat_api.providers.litellm.acompletion")
    async def test_complete_without_usage(self, mock_acompletion: AsyncMock) -> None:
        """Test completion when no usage data is available."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response text"
        mock_response.model = "gemini-1.5-flash"
        mock_response.usage = None  # No usage data

        mock_acompletion.return_value = mock_response

        config = LLMConfig(model="gemini-1.5-flash", api_key="test-key")
        provider = GeminiProvider(config)

        result = await provider.complete("Hello")

        assert result.text == "Response text"
        assert result.model == "gemini-1.5-flash"
        assert result.usage == {}

    @pytest.mark.asyncio
    @patch("chat_api.providers.litellm.acompletion")
    async def test_complete_cost_calculation_error(self, mock_acompletion: AsyncMock) -> None:
        """Test completion when cost calculation fails."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response text"
        mock_response.model = "gemini-1.5-flash"
        mock_response.usage.model_dump.return_value = {"total_tokens": 10}
        mock_acompletion.return_value = mock_response

        # Mock cost calculation failure
        with patch(
            "chat_api.providers.litellm.completion_cost", side_effect=ValueError("No pricing data")
        ):
            config = LLMConfig(model="gemini-1.5-flash", api_key="test-key")
            provider = GeminiProvider(config)

            result = await provider.complete("Hello")

        # Should succeed without cost data
        assert result.text == "Response text"
        assert result.usage["total_tokens"] == 10
        assert "cost_usd" not in result.usage

    @pytest.mark.asyncio
    async def test_health_check_with_api_key(self) -> None:
        """Test health check with API key."""
        config = LLMConfig(model="gemini-1.5-flash", api_key="test-key")
        provider = GeminiProvider(config)

        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_without_api_key(self) -> None:
        """Test health check without API key."""
        config = LLMConfig(model="gemini-1.5-flash", api_key="")
        # This should fail at initialization, but let's test the logic
        with pytest.raises(ConfigurationError):
            GeminiProvider(config)

    @patch("chat_api.providers.litellm")
    def test_setup_litellm_configuration(self, mock_litellm: MagicMock) -> None:
        """Test litellm setup configuration."""
        config = LLMConfig(model="gemini-1.5-flash", api_key="test-key")

        with patch.dict("os.environ", {}, clear=False):
            GeminiProvider(config)

        # Verify litellm configuration
        assert mock_litellm.set_verbose is False
        assert mock_litellm.drop_params is True
        assert mock_litellm.suppress_debug_info is True


class TestOpenRouterProvider:
    """Test OpenRouter provider implementation."""

    def test_initialization_with_api_key(self) -> None:
        """Test OpenRouter provider initialization with API key."""
        config = LLMConfig(model="openrouter/auto", api_key="test-key")
        provider = OpenRouterProvider(config)
        assert provider.config.api_key == "test-key"

    def test_initialization_without_api_key(self) -> None:
        """Test OpenRouter provider initialization fails without API key."""
        config = LLMConfig(model="openrouter/auto", api_key=None)

        with pytest.raises(ConfigurationError, match="OpenRouter API key is required"):
            OpenRouterProvider(config)

    @pytest.mark.asyncio
    @patch("chat_api.providers.litellm.acompletion")
    async def test_complete_success(self, mock_acompletion: AsyncMock) -> None:
        """Test successful OpenRouter completion call."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "OpenRouter response"
        mock_response.model = "openrouter/auto"
        mock_response.usage.model_dump.return_value = {"total_tokens": 20}
        mock_acompletion.return_value = mock_response

        config = LLMConfig(model="openrouter/auto", api_key="test-key")
        provider = OpenRouterProvider(config)

        result = await provider.complete("Test prompt")

        assert result.text == "OpenRouter response"
        assert result.model == "openrouter/auto"
        assert result.usage["total_tokens"] == 20

        # Verify call parameters
        mock_acompletion.assert_called_once_with(
            model="openrouter/auto",
            messages=[{"role": "user", "content": "Test prompt"}],
            timeout=30,
            api_key="test-key",
            temperature=0.1,
            seed=42,
        )

    @pytest.mark.asyncio
    async def test_openrouter_health_check(self) -> None:
        """Test OpenRouter health check."""
        config = LLMConfig(model="openrouter/auto", api_key="test-key")
        provider = OpenRouterProvider(config)

        assert await provider.health_check() is True


class TestProviderFactory:
    """Test provider factory function."""

    def test_create_gemini_provider(self) -> None:
        """Test creating Gemini provider via factory."""
        provider = create_llm_provider(
            provider_type="gemini",
            model="gemini-1.5-flash",
            api_key="test-key",
        )

        assert isinstance(provider, GeminiProvider)
        assert provider.config.model == "gemini-1.5-flash"
        assert provider.config.api_key == "test-key"

    def test_create_openrouter_provider(self) -> None:
        """Test creating OpenRouter provider via factory."""
        provider = create_llm_provider(
            provider_type="openrouter",
            model="openrouter/auto",
            api_key="test-key",
        )

        assert isinstance(provider, OpenRouterProvider)
        assert provider.config.model == "openrouter/auto"

    def test_create_provider_with_custom_config(self) -> None:
        """Test creating provider with custom configuration."""
        provider = create_llm_provider(
            provider_type="gemini",
            model="gemini-1.5-flash",
            api_key="test-key",
            timeout=60,
            max_retries=5,
        )

        assert provider.config.timeout == 60
        assert provider.config.max_retries == 5

    def test_create_unknown_provider(self) -> None:
        """Test creating unknown provider type."""
        with pytest.raises(ConfigurationError, match="Unknown provider type: unknown"):
            create_llm_provider(
                provider_type="unknown",
                model="test-model",
                api_key="test-key",
            )

    def test_case_insensitive_provider_type(self) -> None:
        """Test provider type is case insensitive."""
        provider = create_llm_provider(
            provider_type="GEMINI",
            model="gemini-1.5-flash",
            api_key="test-key",
        )

        assert isinstance(provider, GeminiProvider)


class TestProviderRetryLogic:
    """Test retry logic integration with providers."""

    @pytest.mark.asyncio
    @patch("chat_api.providers.litellm.acompletion")
    async def test_gemini_retry_on_timeout(self, mock_acompletion: AsyncMock) -> None:
        """Test that Gemini provider retries on timeout."""
        # First call times out, second succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success after retry"
        mock_response.model = "gemini-1.5-flash"
        mock_response.usage.model_dump.return_value = {"total_tokens": 10}

        mock_acompletion.side_effect = [TimeoutError("Request timeout"), mock_response]

        config = LLMConfig(model="gemini-1.5-flash", api_key="test-key")
        provider = GeminiProvider(config)

        # Should retry and succeed
        result = await provider.complete("Test message")
        assert result.text == "Success after retry"

        # Should have been called twice (initial + retry)
        assert mock_acompletion.call_count == 2

    @pytest.mark.asyncio
    @patch("chat_api.providers.litellm.acompletion")
    async def test_provider_retry_exhausted(self, mock_acompletion: AsyncMock) -> None:
        """Test provider when all retries are exhausted."""
        # All calls fail
        mock_acompletion.side_effect = TimeoutError("Persistent timeout")

        config = LLMConfig(model="gemini-1.5-flash", api_key="test-key", max_retries=2)
        provider = GeminiProvider(config)

        # Should raise LLMProviderError after retries
        with pytest.raises(LLMProviderError, match="Gemini request timed out"):
            await provider.complete("Test message")

        # Should have tried max_retries times
        assert mock_acompletion.call_count == 2
