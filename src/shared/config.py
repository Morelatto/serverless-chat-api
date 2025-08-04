"""
Configuration management with support for environment variables and AWS Secrets Manager.
Provides centralized configuration for all application settings.
"""
import os
import json
import logging
from typing import Optional, Any
from functools import lru_cache

logger = logging.getLogger(__name__)


class Settings:
    """Application settings with environment variable support."""
    
    def __init__(self):
        """Initialize settings from environment variables."""
        # API Configuration
        self.API_PORT = int(os.getenv("API_PORT", "8000"))
        self.API_HOST = os.getenv("API_HOST", "0.0.0.0")
        self.API_KEYS = os.getenv("API_KEYS", "dev-key-123")
        self.REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "false").lower() == "true"
        
        # LLM Configuration
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
        self.LLM_FALLBACK = os.getenv("LLM_FALLBACK", "true")
        self.GEMINI_API_KEY = self._get_secret("GEMINI_API_KEY")
        self.OPENROUTER_API_KEY = self._get_secret("OPENROUTER_API_KEY")
        self.OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-pro")
        
        # Database Configuration
        self.DATABASE_PATH = os.getenv("DATABASE_PATH", "chat_history.db")
        self.DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "chat-interactions")
        
        # Rate Limiting
        self.RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        
        # Cache Configuration
        self.ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() == "true"
        self.CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
        
        # Circuit Breaker
        self.CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
        self.CIRCUIT_BREAKER_TIMEOUT = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60"))
        
        # AWS Configuration
        self.AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
        self.AWS_LAMBDA_FUNCTION_NAME = os.getenv("AWS_LAMBDA_FUNCTION_NAME")
        
        # Logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FORMAT = os.getenv("LOG_FORMAT", "json")
        
        # Feature Flags
        self.ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        self.ENABLE_TRACING = os.getenv("ENABLE_TRACING", "false").lower() == "true"
        
        self._configure_logging()
    
    def _get_secret(self, key: str) -> Optional[str]:
        """
        Get secret from environment or AWS Secrets Manager.
        First tries environment variable, then AWS SSM if in Lambda.
        """
        # Try environment variable first
        value = os.getenv(key)
        if value:
            return value
        
        # Try AWS Systems Manager Parameter Store if in Lambda
        if self.AWS_LAMBDA_FUNCTION_NAME:
            try:
                import boto3
                ssm = boto3.client('ssm', region_name=self.AWS_REGION)
                
                parameter_name = f"/chatapi/{key}"
                response = ssm.get_parameter(
                    Name=parameter_name,
                    WithDecryption=True
                )
                
                value = response['Parameter']['Value']
                logger.info(f"Retrieved secret {key} from SSM")
                return value
                
            except Exception as e:
                logger.warning(f"Failed to get secret {key} from SSM: {e}")
        
        return None
    
    def _configure_logging(self):
        """Configure application logging based on settings."""
        log_level = getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)
        
        if self.LOG_FORMAT == "json":
            # JSON logging for production
            import json
            
            class JsonFormatter(logging.Formatter):
                def format(self, record):
                    log_obj = {
                        "timestamp": self.formatTime(record),
                        "level": record.levelname,
                        "logger": record.name,
                        "message": record.getMessage(),
                    }
                    if hasattr(record, 'extra'):
                        log_obj.update(record.extra)
                    return json.dumps(log_obj)
            
            handler = logging.StreamHandler()
            handler.setFormatter(JsonFormatter())
            logging.root.handlers = [handler]
            
        else:
            # Simple format for development
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        logging.root.setLevel(log_level)
        logger.info(f"Logging configured: level={self.LOG_LEVEL}, format={self.LOG_FORMAT}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        return getattr(self, key, default)
    
    def to_dict(self) -> dict:
        """Export settings as dictionary (excluding secrets)."""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_') and 'KEY' not in k and 'SECRET' not in k
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance (singleton pattern)."""
    return Settings()


# Global settings instance
settings = get_settings()