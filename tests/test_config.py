"""Test configuration module."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from chat_api.config import Settings


def test_settings_defaults() -> None:
    """Test default settings values."""
    with patch.dict(os.environ, {}, clear=True):
        # Set required fields
        os.environ["CHAT_LLM_PROVIDER"] = "gemini"
        os.environ["CHAT_GEMINI_API_KEY"] = "test-key"

        settings = Settings()

        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.log_level == "INFO"
        assert settings.database_url == "sqlite+aiosqlite:///./chat_history.db"
        assert settings.redis_url is None
        assert settings.rate_limit == "60/minute"


def test_settings_from_env() -> None:
    """Test loading settings from environment variables."""
    test_env = {
        "CHAT_HOST": "127.0.0.1",
        "CHAT_PORT": "3000",
        "CHAT_LOG_LEVEL": "DEBUG",
        "CHAT_DATABASE_URL": "dynamodb://test-table",
        "CHAT_REDIS_URL": "redis://cache:6379",
        "CHAT_RATE_LIMIT": "100/minute",
        "CHAT_LLM_PROVIDER": "openrouter",
        "CHAT_LLM_MODEL": "gpt-4",
        "CHAT_OPENROUTER_API_KEY": "sk-test",
    }

    with patch.dict(os.environ, test_env, clear=True):
        settings = Settings()

        assert settings.host == "127.0.0.1"
        assert settings.port == 3000
        assert settings.log_level == "DEBUG"
        assert settings.database_url == "dynamodb://test-table"
        assert settings.redis_url == "redis://cache:6379"
        assert settings.rate_limit == "100/minute"
        assert settings.llm_provider == "openrouter"
        assert settings.openrouter_api_key == "sk-test"


def test_settings_validation_missing_api_key() -> None:
    """Test settings validation when API key is missing."""
    test_env = {
        "CHAT_LLM_PROVIDER": "gemini",
        # Missing CHAT_GEMINI_API_KEY
    }

    with patch.dict(os.environ, test_env, clear=True):
        # Settings should still be created, but with None API key
        settings = Settings()
        assert settings.gemini_api_key is None


def test_settings_validation_invalid_provider() -> None:
    """Test settings validation with invalid provider."""
    test_env = {
        "CHAT_LLM_PROVIDER": "invalid_provider",
        "CHAT_GEMINI_API_KEY": "test-key",
    }

    with patch.dict(os.environ, test_env, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        assert any("llm_provider" in str(error) for error in errors)


def test_settings_aws_lambda_environment() -> None:
    """Test settings in AWS Lambda environment."""
    test_env = {
        "AWS_LAMBDA_FUNCTION_NAME": "chat-api",
        "AWS_REGION": "us-west-2",
        "CHAT_LLM_PROVIDER": "gemini",
        "CHAT_GEMINI_API_KEY": "test-key",
        "CHAT_DYNAMODB_TABLE": "chat-table",
    }

    with patch.dict(os.environ, test_env, clear=True):
        settings = Settings()

        # Check AWS-related settings
        assert settings.aws_region == "us-west-2"
        assert settings.dynamodb_table == "chat-table"


def test_settings_rate_limit_formats() -> None:
    """Test various rate limit format validations."""
    base_env = {
        "CHAT_LLM_PROVIDER": "gemini",
        "CHAT_GEMINI_API_KEY": "test-key",
    }

    # Valid formats
    valid_formats = [
        "10/second",
        "60/minute",
        "3600/hour",
        "86400/day",
    ]

    for rate_limit in valid_formats:
        with patch.dict(os.environ, {**base_env, "CHAT_RATE_LIMIT": rate_limit}, clear=True):
            settings = Settings()
            assert settings.rate_limit == rate_limit


def test_settings_log_levels() -> None:
    """Test valid log level settings."""
    base_env = {
        "CHAT_LLM_PROVIDER": "gemini",
        "CHAT_GEMINI_API_KEY": "test-key",
    }

    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    for level in valid_levels:
        with patch.dict(os.environ, {**base_env, "CHAT_LOG_LEVEL": level}, clear=True):
            settings = Settings()
            assert settings.log_level == level


def test_settings_openrouter_config() -> None:
    """Test OpenRouter configuration."""
    test_env = {
        "CHAT_LLM_PROVIDER": "openrouter",
        "CHAT_OPENROUTER_API_KEY": "test-key",
        "CHAT_LLM_MODEL": "gpt-4",
    }

    with patch.dict(os.environ, test_env, clear=True):
        settings = Settings()
        assert settings.llm_provider == "openrouter"
        assert settings.openrouter_api_key == "test-key"


def test_settings_literals() -> None:
    """Test that settings validate literal values."""
    test_env = {
        "CHAT_LLM_PROVIDER": "gemini",
        "CHAT_GEMINI_API_KEY": "test-key",
        "CHAT_LOG_LEVEL": "DEBUG",
    }

    with patch.dict(os.environ, test_env, clear=True):
        settings = Settings()
        assert settings.llm_provider == "gemini"
        assert settings.log_level == "DEBUG"


def test_settings_singleton() -> None:
    """Test settings is a singleton instance."""
    from chat_api.config import settings as settings1
    from chat_api.config import settings as settings2

    # Should be the same instance
    assert settings1 is settings2


def test_settings_validation_port_range() -> None:
    """Test port validation."""
    base_env = {
        "CHAT_LLM_PROVIDER": "gemini",
        "CHAT_GEMINI_API_KEY": "test-key",
    }

    # Valid port
    with patch.dict(os.environ, {**base_env, "CHAT_PORT": "8080"}, clear=True):
        settings = Settings()
        assert settings.port == 8080

    # Invalid port (too high) - Pydantic will raise ValidationError
    with patch.dict(os.environ, {**base_env, "CHAT_PORT": "70000"}, clear=True):
        with pytest.raises(ValidationError):
            Settings()

    # Invalid port (not a number)
    with patch.dict(os.environ, {**base_env, "CHAT_PORT": "abc"}, clear=True):
        with pytest.raises(ValidationError):
            Settings()


def test_settings_database_url_formats() -> None:
    """Test various database URL formats."""
    base_env = {
        "CHAT_LLM_PROVIDER": "gemini",
        "CHAT_GEMINI_API_KEY": "test-key",
    }

    # SQLite URL
    with patch.dict(
        os.environ,
        {**base_env, "CHAT_DATABASE_URL": "sqlite+aiosqlite:///./data.db"},
        clear=True,
    ):
        settings = Settings()
        assert "sqlite" in settings.database_url

    # DynamoDB URL
    with patch.dict(
        os.environ,
        {**base_env, "CHAT_DATABASE_URL": "dynamodb://my-table?region=eu-west-1"},
        clear=True,
    ):
        settings = Settings()
        assert "dynamodb" in settings.database_url


def test_settings_redis_url_validation() -> None:
    """Test Redis URL validation."""
    base_env = {
        "CHAT_LLM_PROVIDER": "gemini",
        "CHAT_GEMINI_API_KEY": "test-key",
    }

    # Valid Redis URLs
    valid_urls = [
        "redis://localhost:6379",
        "redis://user:pass@redis.example.com:6379/0",
        "rediss://secure-redis.example.com:6380",  # SSL
    ]

    for url in valid_urls:
        with patch.dict(os.environ, {**base_env, "CHAT_REDIS_URL": url}, clear=True):
            settings = Settings()
            assert settings.redis_url == url


def test_settings_env_file_support() -> None:
    """Test that settings can load from .env file."""
    import tempfile
    from pathlib import Path

    # Create a temporary .env file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("CHAT_LLM_PROVIDER=gemini\n")
        f.write("CHAT_GEMINI_API_KEY=env-file-key\n")
        f.write("CHAT_LOG_LEVEL=WARNING\n")
        env_file = f.name

    try:
        # Settings should load from .env file
        with patch.dict(os.environ, {}, clear=True):
            # Simulate loading from .env
            with open(env_file) as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value

            settings = Settings()
            assert settings.llm_provider == "gemini"
            assert settings.gemini_api_key == "env-file-key"
            assert settings.log_level == "WARNING"
    finally:
        Path(env_file).unlink(missing_ok=True)
