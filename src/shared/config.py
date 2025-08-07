"""Configuration management with environment variables and AWS Secrets Manager."""

import logging
import os
from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Configuration
    API_PORT: int = Field(default=8000, env="API_PORT")
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_KEYS: str = Field(default="dev-key-123", env=["API_KEY", "API_KEYS"])
    REQUIRE_API_KEY: bool = Field(default=False, env="REQUIRE_API_KEY")
    
    # AWS Configuration  
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")
    AWS_LAMBDA_FUNCTION_NAME: str | None = Field(default=None, env="AWS_LAMBDA_FUNCTION_NAME")
    
    # LLM Configuration
    LLM_PROVIDER: str = Field(default="gemini", env="LLM_PROVIDER")
    LLM_FALLBACK: str = Field(default="true", env="LLM_FALLBACK")
    GEMINI_API_KEY: str | None = Field(default=None, env="GEMINI_API_KEY")
    OPENROUTER_API_KEY: str | None = Field(default=None, env="OPENROUTER_API_KEY")
    OPENROUTER_MODEL: str = Field(default="google/gemini-pro", env="OPENROUTER_MODEL")
    
    # Database Configuration
    DATABASE_PATH: str = Field(default="chat_history.db", env="DATABASE_PATH")
    DYNAMODB_TABLE: str = Field(default="chat-interactions", env=["TABLE_NAME", "DYNAMODB_TABLE"])
    
    # Rate Limiting & Performance
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    ENABLE_CACHE: bool = Field(default=True, env="ENABLE_CACHE")
    CACHE_TTL_SECONDS: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    CIRCUIT_BREAKER_THRESHOLD: int = Field(default=5, env="CIRCUIT_BREAKER_THRESHOLD")
    CIRCUIT_BREAKER_TIMEOUT: int = Field(default=60, env="CIRCUIT_BREAKER_TIMEOUT")
    
    # Logging & Monitoring
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    ENABLE_TRACING: bool = Field(default=False, env="ENABLE_TRACING")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    def __init__(self, **kwargs) -> None:
        """Initialize settings and configure logging."""
        super().__init__(**kwargs)
        self._configure_logging()
    
    def get_gemini_key(self) -> str | None:
        """Get Gemini API key with SSM fallback if needed."""
        return self._get_secret_with_fallback("GEMINI_API_KEY", self.GEMINI_API_KEY)
    
    def get_openrouter_key(self) -> str | None:
        """Get OpenRouter API key with SSM fallback if needed."""
        return self._get_secret_with_fallback("OPENROUTER_API_KEY", self.OPENROUTER_API_KEY)

    def _get_secret_with_fallback(self, key: str, env_value: str | None) -> str | None:
        """Get secret with SSM fallback if in Lambda and env value is missing."""
        if env_value:
            return env_value
        
        if self.AWS_LAMBDA_FUNCTION_NAME:
            try:
                import boto3

                ssm = boto3.client("ssm", region_name=self.AWS_REGION)

                parameter_name = f"/chatapi/{key}"
                response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)

                value = response["Parameter"]["Value"]
                logger.info(f"Retrieved secret {key} from SSM")
                return str(value)

            except Exception as e:
                logger.warning(f"Failed to get secret {key} from SSM: {e}")

        return None
    
    def _get_secret(self, key: str) -> str | None:
        """Get secret from environment or AWS SSM if in Lambda."""
        value = os.getenv(key)
        if value:
            return value

        if self.AWS_LAMBDA_FUNCTION_NAME:
            try:
                import boto3

                ssm = boto3.client("ssm", region_name=self.AWS_REGION)

                parameter_name = f"/chatapi/{key}"
                response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)

                value = response["Parameter"]["Value"]
                logger.info(f"Retrieved secret {key} from SSM")
                return str(value)

            except Exception as e:
                logger.warning(f"Failed to get secret {key} from SSM: {e}")

        return None

    def _configure_logging(self) -> None:
        """Configure application logging based on settings."""
        log_level = getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)

        if self.LOG_FORMAT == "json":
            import json

            class JsonFormatter(logging.Formatter):
                def format(self, record: logging.LogRecord) -> str:
                    log_obj = {
                        "timestamp": self.formatTime(record),
                        "level": record.levelname,
                        "logger": record.name,
                        "message": record.getMessage(),
                    }
                    if hasattr(record, "extra"):
                        log_obj.update(record.extra)
                    return json.dumps(log_obj)

            handler = logging.StreamHandler()
            handler.setFormatter(JsonFormatter())
            logging.root.handlers = [handler]

        else:
            # Simple format for development
            logging.basicConfig(
                level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        logging.root.setLevel(log_level)
        logger.info(f"Logging configured: level={self.LOG_LEVEL}, format={self.LOG_FORMAT}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        return getattr(self, key, default)

    def to_dict(self) -> dict[str, Any]:
        """Export settings as dictionary (excluding secrets)."""
        data = self.dict()
        return {
            k: v
            for k, v in data.items()
            if not k.startswith("_") and "KEY" not in k and "SECRET" not in k
        }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance (singleton pattern)."""
    return Settings()


# Global settings instance
settings = get_settings()
