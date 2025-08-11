"""Tests for configuration settings."""

import os
from unittest.mock import patch

import pytest

from chat_api.config import Settings, get_settings


class TestSettings:
    """Test Settings configuration."""

    def test_default_settings(self):
        """Test default settings values."""
        # Need to provide required API key for testing
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.dict(os.environ, {"CHAT_OPENROUTER_API_KEY": "test-key"}),
        ):
            settings = Settings()

            assert settings.host == "0.0.0.0"
            assert settings.port == 8000
            assert settings.log_level == "INFO"
            assert settings.environment == "development"
            assert settings.llm_provider == "openrouter"
            assert settings.database_url == "sqlite+aiosqlite:///./data/chat.db"

    def test_lambda_environment_detection(self):
        """Test AWS Lambda environment detection."""
        with (
            patch.dict(os.environ, {"AWS_LAMBDA_FUNCTION_NAME": "my-function"}, clear=True),
            patch.dict(os.environ, {"CHAT_OPENROUTER_API_KEY": "test-key"}),
        ):
            settings = Settings()
            assert settings.is_lambda_environment is True
            assert settings.effective_database_url.startswith("dynamodb://")

    def test_effective_database_url_lambda(self):
        """Test effective database URL in Lambda environment."""
        with patch.dict(
            os.environ,
            {
                "CHAT_ENVIRONMENT": "lambda",
                "CHAT_OPENROUTER_API_KEY": "test-key",
            },
        ):
            settings = Settings()
            settings.environment = "lambda"
            assert (
                settings.effective_database_url
                == f"dynamodb://{settings.dynamodb_table}?region={settings.aws_region}"
            )

    def test_effective_database_url_non_lambda(self):
        """Test effective database URL in non-Lambda environment."""
        with patch.dict(os.environ, {"CHAT_OPENROUTER_API_KEY": "test-key"}):
            settings = Settings()
            assert settings.effective_database_url == settings.database_url

    def test_api_key_validation_gemini_missing(self):
        """Test validation error when Gemini API key is missing."""
        with (
            patch.dict(
                os.environ,
                {"CHAT_LLM_PROVIDER": "gemini"},
                clear=True,
            ),
            pytest.raises(ValueError, match="GEMINI_API_KEY not set"),
        ):
            Settings()

    def test_api_key_validation_openrouter_missing(self):
        """Test validation error when OpenRouter API key is missing."""
        with (
            patch.dict(
                os.environ,
                {"CHAT_LLM_PROVIDER": "openrouter", "CHAT_OPENROUTER_API_KEY": ""},
                clear=True,
            ),
            pytest.raises(ValueError, match="OPENROUTER_API_KEY not set"),
        ):
            Settings()

    def test_api_key_validation_gemini_provided(self):
        """Test successful validation when Gemini API key is provided."""
        with patch.dict(
            os.environ,
            {
                "CHAT_LLM_PROVIDER": "gemini",
                "CHAT_GEMINI_API_KEY": "test-gemini-key",
            },
        ):
            settings = Settings()
            assert settings.gemini_api_key == "test-gemini-key"
            assert settings.llm_provider == "gemini"

    def test_environment_from_chat_env(self):
        """Test environment detection from CHAT_ENV variable."""
        test_cases = [
            ("lambda", "lambda"),
            ("docker", "docker"),
            ("development", "development"),
            ("", "development"),  # Default
        ]

        for env_value, expected in test_cases:
            with patch.dict(
                os.environ,
                {"CHAT_ENV": env_value, "CHAT_OPENROUTER_API_KEY": "test-key"},
                clear=True,
            ):
                settings = Settings()
                assert settings.environment == expected

    def test_get_settings_returns_singleton(self):
        """Test get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_cache_settings(self):
        """Test cache-related settings."""
        with patch.dict(os.environ, {"CHAT_OPENROUTER_API_KEY": "test-key"}):
            settings = Settings()
            assert settings.cache_ttl_seconds == 3600
            assert settings.cache_max_size == 1000

    def test_rate_limit_setting(self):
        """Test rate limit configuration."""
        with patch.dict(
            os.environ,
            {
                "CHAT_RATE_LIMIT": "100/minute",
                "CHAT_OPENROUTER_API_KEY": "test-key",
            },
        ):
            settings = Settings()
            assert settings.rate_limit == "100/minute"

    def test_model_settings(self):
        """Test model configuration settings."""
        with patch.dict(os.environ, {"CHAT_OPENROUTER_API_KEY": "test-key"}):
            settings = Settings()
            assert settings.gemini_model == "gemini/gemini-1.5-flash-latest"
            assert (
                settings.openrouter_default_model == "openrouter/meta-llama/llama-3.2-1b-instruct"
            )
            assert settings.openrouter_model == "google/gemma-2-9b-it:free"
