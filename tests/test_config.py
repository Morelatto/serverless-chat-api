"""Test configuration and environment detection."""

import os
from unittest.mock import patch

import pytest

from chat_api.config import Settings, settings


class TestSettings:
    """Test Settings configuration."""

    def test_default_settings(self) -> None:
        """Test default settings values."""
        with patch.dict(
            os.environ,
            {
                "CHAT_OPENROUTER_API_KEY": "test-key",
            },
            clear=True,
        ):
            settings = Settings()

            assert settings.host == "0.0.0.0"
            assert settings.port == 8000
            assert settings.log_level == "INFO"
            assert settings.llm_provider == "openrouter"
            assert settings.llm_model == "openrouter/google/gemma-2-9b-it:free"
            assert settings.database_url == "sqlite+aiosqlite:///./data/chat.db"
            assert settings.rate_limit == "60/minute"
            assert settings.redis_url is None
            assert settings.log_file is None

    def test_environment_variable_override(self) -> None:
        """Test that environment variables override defaults."""
        with patch.dict(
            os.environ,
            {
                "CHAT_HOST": "127.0.0.1",
                "CHAT_PORT": "9000",
                "CHAT_LOG_LEVEL": "DEBUG",
                "CHAT_LLM_PROVIDER": "openrouter",
                "CHAT_OPENROUTER_API_KEY": "or-key",
                "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
                "CHAT_RATE_LIMIT": "100/minute",
                "CHAT_REDIS_URL": "redis://localhost:6379",
            },
            clear=True,
        ):
            settings = Settings()

            assert settings.host == "127.0.0.1"
            assert settings.port == 9000
            assert settings.log_level == "DEBUG"
            assert settings.llm_provider == "openrouter"
            assert settings.database_url == "sqlite+aiosqlite:///:memory:"
            assert settings.rate_limit == "100/minute"
            assert settings.redis_url == "redis://localhost:6379"

    def test_openrouter_model_configuration(self) -> None:
        """Test OpenRouter model configuration."""
        with patch.dict(
            os.environ,
            {
                "CHAT_LLM_PROVIDER": "openrouter",
                "CHAT_OPENROUTER_API_KEY": "or-key",
                "CHAT_OPENROUTER_MODEL": "google/gemma-7b-it:free",
            },
            clear=True,
        ):
            settings = Settings()

            assert settings.llm_provider == "openrouter"
            assert settings.llm_model == "google/gemma-7b-it:free"

    def test_gemini_model_configuration(self) -> None:
        """Test Gemini model configuration."""
        with patch.dict(
            os.environ,
            {
                "CHAT_LLM_PROVIDER": "gemini",
                "CHAT_GEMINI_API_KEY": "gemini-key",
            },
            clear=True,
        ):
            settings = Settings()

            assert settings.llm_provider == "gemini"
            assert settings.llm_model == "gemini/gemini-1.5-flash"

    def test_aws_configuration(self) -> None:
        """Test AWS-specific configuration."""
        with patch.dict(
            os.environ,
            {
                "CHAT_AWS_REGION": "us-west-2",
                "CHAT_DYNAMODB_TABLE": "custom-chat-table",
                "CHAT_GEMINI_API_KEY": "key",
            },
            clear=True,
        ):
            settings = Settings()

            assert settings.aws_region == "us-west-2"
            assert settings.dynamodb_table == "custom-chat-table"

    def test_logging_configuration(self) -> None:
        """Test logging configuration options."""
        with patch.dict(
            os.environ,
            {
                "CHAT_LOG_LEVEL": "ERROR",
                "CHAT_LOG_FILE": "/var/log/chat-api.log",
                "CHAT_GEMINI_API_KEY": "key",
            },
            clear=True,
        ):
            settings = Settings()

            assert settings.log_level == "ERROR"
            assert settings.log_file == "/var/log/chat-api.log"

    def test_required_api_key_validation(self) -> None:
        """Test that API key is required based on provider."""
        # Test missing Gemini key
        test_env = {k: v for k, v in os.environ.items() if not k.startswith("CHAT_")}
        test_env["CHAT_LLM_PROVIDER"] = "gemini"
        with (
            patch.dict(os.environ, test_env, clear=True),
            pytest.raises(ValueError, match="CHAT_GEMINI_API_KEY not set"),
        ):
            Settings()

        # Test missing OpenRouter key
        test_env = {k: v for k, v in os.environ.items() if not k.startswith("CHAT_")}
        test_env["CHAT_LLM_PROVIDER"] = "openrouter"
        with (
            patch.dict(os.environ, test_env, clear=True),
            pytest.raises(ValueError, match="CHAT_OPENROUTER_API_KEY not set"),
        ):
            Settings()

    def test_valid_provider_validation(self) -> None:
        """Test provider validation."""
        with (
            patch.dict(
                os.environ,
                {
                    "CHAT_LLM_PROVIDER": "invalid_provider",
                    "CHAT_GEMINI_API_KEY": "key",
                },
                clear=True,
            ),
            pytest.raises(ValueError, match="Invalid LLM provider"),
        ):
            Settings()

    def test_log_level_validation(self) -> None:
        """Test log level validation - no validation in current implementation."""
        with patch.dict(
            os.environ,
            {
                "CHAT_LOG_LEVEL": "INVALID",
                "CHAT_OPENROUTER_API_KEY": "key",
            },
            clear=True,
        ):
            # Current implementation doesn't validate log levels
            settings = Settings()
            assert settings.log_level == "INVALID"

    def test_port_range_validation(self) -> None:
        """Test port range validation - no validation in current implementation."""
        with patch.dict(
            os.environ,
            {
                "CHAT_PORT": "70000",  # Invalid port
                "CHAT_OPENROUTER_API_KEY": "key",
            },
            clear=True,
        ):
            # Current implementation doesn't validate port ranges
            settings = Settings()
            assert settings.port == 70000


class TestEnvironmentDetection:
    """Test environment detection functions."""

    def test_is_lambda_environment_true(self) -> None:
        """Test Lambda environment detection returns True in Lambda."""
        with patch.dict(
            os.environ,
            {
                "AWS_LAMBDA_FUNCTION_NAME": "chat-api-function",
                "CHAT_OPENROUTER_API_KEY": "key",
            },
        ):
            settings = Settings()
            assert settings.is_lambda_environment is True

    def test_is_lambda_environment_false(self) -> None:
        """Test Lambda environment detection returns False locally."""
        with patch.dict(
            os.environ,
            {
                "CHAT_OPENROUTER_API_KEY": "key",
            },
            clear=True,
        ):
            settings = Settings()
            assert settings.is_lambda_environment is False

    def test_lambda_database_url_override(self) -> None:
        """Test that Lambda environment uses DynamoDB."""
        with patch.dict(
            os.environ,
            {
                "AWS_LAMBDA_FUNCTION_NAME": "chat-api-function",
                "CHAT_OPENROUTER_API_KEY": "key",
                "CHAT_DATABASE_URL": "sqlite+aiosqlite:///./local.db",  # Should be overridden
            },
        ):
            settings = Settings()

            # Should use DynamoDB in Lambda environment
            assert "dynamodb" in settings.effective_database_url

    def test_local_database_url_preserved(self) -> None:
        """Test that local environment preserves database URL."""
        with patch.dict(
            os.environ,
            {
                "CHAT_OPENROUTER_API_KEY": "key",
                "CHAT_DATABASE_URL": "sqlite+aiosqlite:///./local.db",
            },
            clear=True,
        ):
            settings = Settings()

            # Should preserve local database URL
            assert settings.effective_database_url == "sqlite+aiosqlite:///./local.db"


class TestSettingsSingleton:
    """Test settings module-level instance."""

    def test_module_level_settings_available(self) -> None:
        """Test that module-level settings instance is available."""
        # Module level settings should be available
        assert settings is not None
        assert isinstance(settings, Settings)


class TestConfigurationIntegration:
    """Test configuration integration scenarios."""

    def test_production_like_configuration(self) -> None:
        """Test production-like configuration setup."""
        with patch.dict(
            os.environ,
            {
                "CHAT_HOST": "0.0.0.0",
                "CHAT_PORT": "8000",
                "CHAT_LOG_LEVEL": "INFO",
                "CHAT_LLM_PROVIDER": "gemini",
                "CHAT_GEMINI_API_KEY": "prod-gemini-key",
                "CHAT_DATABASE_URL": "dynamodb://chat-interactions?region=us-east-1",
                "CHAT_REDIS_URL": "redis://prod-redis:6379",
                "CHAT_RATE_LIMIT": "30/minute",
                "CHAT_AWS_REGION": "us-east-1",
                "CHAT_DYNAMODB_TABLE": "chat-interactions",
            },
            clear=True,
        ):
            settings = Settings()

            assert settings.host == "0.0.0.0"
            assert settings.llm_provider == "gemini"
            assert settings.gemini_api_key == "prod-gemini-key"
            assert "dynamodb" in settings.database_url
            assert settings.redis_url == "redis://prod-redis:6379"
            assert settings.rate_limit == "30/minute"

    def test_development_configuration(self) -> None:
        """Test development configuration setup."""
        with patch.dict(
            os.environ,
            {
                "CHAT_HOST": "127.0.0.1",
                "CHAT_LOG_LEVEL": "DEBUG",
                "CHAT_LLM_PROVIDER": "openrouter",
                "CHAT_OPENROUTER_API_KEY": "dev-or-key",
                "CHAT_OPENROUTER_MODEL": "google/gemma-7b-it:free",
                "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
                "CHAT_RATE_LIMIT": "1000/minute",
            },
            clear=True,
        ):
            settings = Settings()

            assert settings.host == "127.0.0.1"
            assert settings.log_level == "DEBUG"
            assert settings.llm_provider == "openrouter"
            assert settings.llm_model == "google/gemma-7b-it:free"
            assert settings.database_url == "sqlite+aiosqlite:///:memory:"
            assert settings.rate_limit == "1000/minute"
            assert settings.redis_url is None  # No Redis in dev

    def test_lambda_configuration(self) -> None:
        """Test Lambda-specific configuration."""
        with patch.dict(
            os.environ,
            {
                "AWS_LAMBDA_FUNCTION_NAME": "chat-api",
                "LAMBDA_RUNTIME_DIR": "/var/runtime",
                "CHAT_LLM_PROVIDER": "gemini",
                "CHAT_GEMINI_API_KEY": "lambda-gemini-key",
                "CHAT_AWS_REGION": "us-east-1",
                "CHAT_DYNAMODB_TABLE": "lambda-chat-table",
            },
            clear=True,
        ):
            settings = Settings()

            # Should auto-configure for Lambda
            assert "dynamodb" in settings.database_url
            assert settings.aws_region == "us-east-1"
            assert settings.dynamodb_table == "lambda-chat-table"

    def test_docker_configuration(self) -> None:
        """Test Docker-like configuration."""
        with patch.dict(
            os.environ,
            {
                "CHAT_HOST": "0.0.0.0",
                "CHAT_PORT": "8000",
                "CHAT_LLM_PROVIDER": "openrouter",
                "CHAT_OPENROUTER_API_KEY": "docker-key",
                "CHAT_DATABASE_URL": "sqlite+aiosqlite:///./data/chat.db",
                "CHAT_RATE_LIMIT": "60/minute",
            },
            clear=True,
        ):
            settings = Settings()

            assert settings.host == "0.0.0.0"  # Bind to all interfaces
            assert settings.port == 8000
            assert settings.database_url == "sqlite+aiosqlite:///./data/chat.db"
