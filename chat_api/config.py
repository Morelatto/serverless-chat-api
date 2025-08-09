"""Configuration using pydantic-settings."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation."""

    # API Settings
    host: str = "0.0.0.0"  # nosec B104 - Intentional for containerized deployment
    port: int = 8000
    log_level: str = "INFO"
    log_file: str | None = None  # Optional log file path

    # LLM Settings
    llm_provider: str = "openrouter"  # openrouter or gemini
    gemini_api_key: str | None = None
    openrouter_api_key: str | None = None
    openrouter_model: str = "google/gemma-2-9b-it:free"  # Default free model for openrouter

    # Storage
    database_url: str = "sqlite+aiosqlite:///./data/chat.db"
    redis_url: str | None = None

    # AWS Configuration (for production)
    aws_region: str = "us-east-1"
    dynamodb_table: str = "chat-interactions"

    # Rate Limiting
    rate_limit: str = "60/minute"

    @model_validator(mode="after")
    def validate_api_keys(self) -> "Settings":
        """Validate that required API keys are present for the configured provider."""
        if self.llm_provider == "gemini" and not self.gemini_api_key:
            raise ValueError(
                "Gemini provider selected but CHAT_GEMINI_API_KEY not set. "
                "Please set the CHAT_GEMINI_API_KEY environment variable."
            )
        if self.llm_provider == "openrouter" and not self.openrouter_api_key:
            raise ValueError(
                "OpenRouter provider selected but CHAT_OPENROUTER_API_KEY not set. "
                "Please set the CHAT_OPENROUTER_API_KEY environment variable."
            )
        if self.llm_provider not in ("gemini", "openrouter"):
            raise ValueError(
                f"Invalid LLM provider: {self.llm_provider}. " "Must be one of: gemini, openrouter"
            )
        return self

    @property
    def llm_model(self) -> str:
        """Get the full model identifier for litellm based on provider."""
        if self.llm_provider == "gemini":
            return "gemini/gemini-1.5-flash"
        # openrouter
        return f"openrouter/{self.openrouter_model}"

    class Config:
        env_file = ".env"
        env_prefix = "CHAT_"  # CHAT_PORT=8000


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Module-level instance
settings = get_settings()
