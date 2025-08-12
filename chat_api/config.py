"""Configuration using pydantic-settings."""

import os
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation and constants."""

    host: str = "0.0.0.0"  # nosec B104 - Required for container deployment
    port: int = 8000
    log_level: str = "INFO"
    log_file: str | None = None

    environment: Literal["development", "docker", "lambda"] = "development"

    llm_provider: str = "openrouter"
    gemini_api_key: str | None = None
    openrouter_api_key: str | None = None
    openrouter_model: str = "google/gemma-2-9b-it:free"
    llm_timeout: int = 30

    database_url: str = "sqlite+aiosqlite:///./data/chat.db"
    redis_url: str | None = None

    aws_region: str = "us-east-1"
    dynamodb_table: str = "chat-interactions"

    rate_limit: str = "60/minute"

    # JWT settings
    secret_key: str = "your-secret-key-change-in-production"  # noqa: S105
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30

    # Cache settings
    cache_ttl_seconds: int = 3600
    cache_max_size: int = 1000

    # Model settings
    gemini_model: str = "gemini/gemini-1.5-flash-latest"
    openrouter_default_model: str = "openrouter/meta-llama/llama-3.2-1b-instruct"

    # DynamoDB settings
    dynamodb_ttl_days: int = 30

    @property
    def is_lambda_environment(self) -> bool:
        """Check if running in AWS Lambda."""
        return self.environment == "lambda" or bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

    @property
    def effective_database_url(self) -> str:
        """Get the effective database URL based on environment."""
        if self.is_lambda_environment:
            return f"dynamodb://{self.dynamodb_table}?region={self.aws_region}"
        return self.database_url

    @model_validator(mode="after")
    def validate_api_keys(self) -> "Settings":
        """Validate that required API keys are present."""
        if self.llm_provider == "gemini" and not self.gemini_api_key:
            raise ValueError(
                "Gemini provider selected but GEMINI_API_KEY not set. "
                "Please set the GEMINI_API_KEY environment variable."
            )
        if self.llm_provider == "openrouter" and not self.openrouter_api_key:
            raise ValueError(
                "OpenRouter provider selected but OPENROUTER_API_KEY not set. "
                "Please set the OPENROUTER_API_KEY environment variable."
            )
        return self

    @model_validator(mode="after")
    def validate_environment(self) -> "Settings":
        """Set environment based on CHAT_ENV or AWS Lambda detection."""
        env = os.getenv("CHAT_ENV", "").lower()
        if env == "lambda":
            self.environment = "lambda"
        elif env == "docker":
            self.environment = "docker"
        elif env == "development":
            self.environment = "development"
        elif os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            self.environment = "lambda"
        return self

    class Config:
        """Pydantic config."""

        env_prefix = "CHAT_"
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def get_settings() -> Settings:
    """Get settings instance (for dependency injection)."""
    return settings
