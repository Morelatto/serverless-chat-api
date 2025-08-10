This file is a merged representation of a subset of the codebase, containing files not matching ignore patterns, combined into a single document by Repomix.

# File Summary

## Purpose
This file contains a packed representation of a subset of the repository's contents that is considered the most important context.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.

## File Format
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  a. A header with the file path (## File: path/to/file)
  b. The full contents of the file in a code block

## Usage Guidelines
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.

## Notes
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Files matching these patterns are excluded: **/*.csv, **/*.xlsx, **/*.parquet, **/*.pkl, **/*.bin, **/*.pt, **/*.h5, **/*.hdf5, **/*.pdf, **/*.mp4, **/*.mp3, **/*.wav, **/*.bak, **/*.backup, **/*.old, **/archive/**, **/phases/**
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Long base64 data strings (e.g., data:image/png;base64,...) have been truncated to reduce token count
- Files are sorted by Git change count (files with more changes are at the bottom)

# Directory Structure
```
__init__.py
__main__.py
api.py
aws.py
chat.py
config.py
exceptions.py
middleware.py
providers.py
retry.py
storage.py
types.py
```

# Files

## File: __init__.py
```python
"""Chat API - A simple LLM chat service with Pythonic design (Python 2025 style).

Public API exports for clean imports:
    from chat_api import create_app, ChatService, ChatMessage
"""

from .api import app, create_app
from .chat import ChatMessage, ChatResponse, ChatService
from .providers import create_llm_provider

__version__ = "1.0.0"

__all__ = [
    "ChatMessage",
    "ChatResponse",
    "ChatService",
    "app",
    "create_app",
    "create_llm_provider",
]
```

## File: __main__.py
```python
"""Entry point for python -m chat_api."""

import uvicorn

from .api import app
from .config import settings


def main() -> None:
    """Run the chat API server."""
    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level.lower())


if __name__ == "__main__":
    main()
```

## File: api.py
```python
"""FastAPI application - All routes and middleware in one place (Python 2025 style)."""

import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .chat import ChatMessage, ChatResponse, ChatService
from .config import settings
from .exceptions import ChatAPIError, LLMProviderError, StorageError, ValidationError
from .middleware import add_request_id
from .providers import create_llm_provider
from .storage import create_cache, create_repository
from .types import MessageRecord

# Configure loguru
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level,
    serialize=False,
)
if settings.log_file:
    logger.add(
        settings.log_file,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        level=settings.log_level,
    )

# Rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url or "memory://",
    default_limits=[settings.rate_limit],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Create dependencies
    repository = create_repository(settings.database_url)
    cache = create_cache(settings.redis_url)

    # Create LLM provider
    api_key = (
        settings.gemini_api_key
        if settings.llm_provider == "gemini"
        else settings.openrouter_api_key
    )
    llm_provider = create_llm_provider(
        provider_type=settings.llm_provider,
        model=settings.llm_model,
        api_key=api_key,
    )

    # Initialize resources
    await repository.startup()
    await cache.startup()

    # Create service and store in app.state
    app.state.chat_service = ChatService(repository, cache, llm_provider)

    logger.info("Application started successfully")
    yield

    # Cleanup
    await repository.shutdown()
    await cache.shutdown()
    logger.info("Application shutdown complete")


# Create app
app = FastAPI(
    title="Chat API",
    version="1.0.0",
    description="A simple LLM chat service with Pythonic design",
    lifespan=lifespan,
)

# Add middleware
app.middleware("http")(add_request_id)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Validation error handler
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle validation errors with clean messages."""
    error_messages = []

    for error in exc.errors():  # type: ignore[attr-defined]
        field = error["loc"][-1] if error["loc"] else "field"
        message = error.get("msg", f"Invalid {field}")

        match error["type"]:
            case "missing":
                message = f"Required field '{field}' is missing"
            case "json_invalid":
                message = "Invalid JSON format"

        error_messages.append(message)

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Validation failed",
            "message": "; ".join(error_messages),
            "details": error_messages,
        },
    )


app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]


@app.exception_handler(ChatAPIError)
async def chat_api_exception_handler(request: Request, exc: ChatAPIError) -> JSONResponse:
    """Handle domain-specific errors."""
    logger.error(f"Chat API error: {exc}")

    # Map exception types to status codes
    status_map = {
        LLMProviderError: 503,
        StorageError: 503,
        ValidationError: 400,
    }

    status_code = 500
    for exc_type, code in status_map.items():
        if isinstance(exc, exc_type):
            status_code = code
            break

    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc), "type": exc.__class__.__name__},
    )


# ============== Routes ==============
# ============== Dependencies ==============
async def get_chat_service(request: Request) -> ChatService:
    """Get chat service from app state."""
    service: ChatService = request.app.state.chat_service
    return service


# ============== Routes ==============
@app.post("/chat", tags=["chat"])
@limiter.limit(settings.rate_limit)
async def chat_endpoint(
    request: Request,
    message: ChatMessage,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """Process a chat message."""
    try:
        result = await service.process_message(message.user_id, message.content)

        return ChatResponse(
            id=result["id"],
            content=result["content"],
            timestamp=datetime.now(UTC),
            cached=result.get("cached", False),
            model=result.get("model"),
        )
    except LLMProviderError as e:
        logger.error(f"LLM provider error: {e}")
        raise HTTPException(status_code=503, detail=f"Service temporarily unavailable: {e}") from e
    except StorageError as e:
        logger.error(f"Storage error: {e}")
        raise HTTPException(status_code=503, detail=f"Storage error: {e}") from e
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Unexpected error in chat handler: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/history/{user_id}", tags=["chat"])
async def history_endpoint(
    response: Response,
    user_id: str,
    limit: int = 10,
    service: ChatService = Depends(get_chat_service),
) -> list[MessageRecord]:
    """Retrieve chat history for a user."""
    if limit > 100:
        raise HTTPException(400, "Limit cannot exceed 100")

    return await service.get_history(user_id, limit)


@app.get("/health", tags=["health"])
async def health_endpoint(
    response: Response,
    service: ChatService = Depends(get_chat_service),
) -> dict[str, Any]:
    """Check health status of all components."""
    status = await service.health_check()
    all_healthy = all(status.values())

    # Set status code based on health
    if not all_healthy:
        response.status_code = 503

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "services": status,
    }


@app.get("/health/detailed", tags=["health"])
async def detailed_health_endpoint(
    service: ChatService = Depends(get_chat_service),
) -> dict[str, Any]:
    """Get detailed health information."""
    status = await service.health_check()

    return {
        "status": "healthy" if all(status.values()) else "unhealthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "services": status,
        "version": "1.0.0",
        "environment": {
            "llm_provider": settings.llm_provider,
            "rate_limit": settings.rate_limit,
        },
    }


@app.get("/", tags=["health"])
async def root_endpoint(response: Response) -> dict[str, str]:
    """API information endpoint."""
    return {
        "name": "Chat API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


# OpenAPI customization
app.openapi_tags = [
    {"name": "chat", "description": "Chat operations"},
    {"name": "health", "description": "Health checks"},
]


# Export for use in other modules
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    return app
```

## File: aws.py
```python
"""AWS Lambda handler for the Chat API."""

from typing import Any

from loguru import logger
from mangum import Mangum

from chat_api import app

# Configure loguru for Lambda
logger.add(lambda msg: print(msg, end=""))  # Lambda logs to stdout

# Create the Lambda handler using Mangum
handler = Mangum(app, lifespan="off")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point.

    Args:
        event: Lambda event dictionary containing request information.
        context: Lambda context object with runtime information.

    Returns:
        Response dictionary with statusCode, headers, and body.

    """
    # Log the incoming event for debugging
    logger.info("Lambda event: {}", event)

    # Process the request through Mangum/FastAPI
    response = handler(event, context)

    # Log the response for debugging
    logger.info("Lambda response status: {}", response.get("statusCode"))

    return response  # type: ignore[no-any-return]
```

## File: chat.py
```python
"""Chat service - Core business logic and models (Python 2025 style)."""

import uuid
from datetime import datetime

from loguru import logger
from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from .exceptions import LLMProviderError, StorageError
from .providers import LLMProvider
from .storage import Cache, Repository, cache_key
from .types import ChatResult, HealthStatus, MessageRecord

# Constants
USER_ID_LOG_LENGTH = 8  # Characters to show in logs for privacy


# ============== Models ==============
class ChatMessage(BaseModel):
    """Input message from user."""

    user_id: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=4000)

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id(cls, value: str) -> str:
        if not value or not value.strip():
            msg = "empty_user_id"
            raise PydanticCustomError(msg, "User ID cannot be empty", {"input": value})
        if len(value.strip()) > 100:
            msg = "user_id_too_long"
            raise PydanticCustomError(
                msg,
                "User ID is too long (max 100 characters)",
                {"length": len(value), "max_length": 100},
            )
        return value.strip()

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not value or not value.strip():
            msg = "empty_content"
            raise PydanticCustomError(
                msg,
                "Message content cannot be empty",
                {"input": value},
            )
        if len(value.strip()) > 4000:
            msg = "content_too_long"
            raise PydanticCustomError(
                msg,
                "Message is too long (max 4000 characters)",
                {"length": len(value), "max_length": 4000},
            )
        return value.strip()


class ChatResponse(BaseModel):
    """Response from the API."""

    id: str
    content: str
    timestamp: datetime
    cached: bool = False
    model: str | None = None


# ============== Core Service ==============
class ChatService:
    """Chat service handling message processing with injected dependencies."""

    def __init__(
        self,
        repository: Repository,
        cache: Cache,
        llm_provider: LLMProvider,
    ) -> None:
        """Initialize chat service with dependencies.

        Args:
            repository: Storage repository for persistence.
            cache: Cache instance for response caching.
            llm_provider: LLM provider for generating responses.

        """
        self.repository = repository
        self.cache = cache
        self.llm_provider = llm_provider

    async def process_message(
        self,
        user_id: str,
        content: str,
    ) -> ChatResult:
        """Process a chat message.

        Args:
            user_id: User identifier.
            content: Message content to process.

        Returns:
            Dictionary with message ID, response content, model, and cache status.

        """
        # Check cache
        key = cache_key(user_id, content)
        cached = await self.cache.get(key)
        if cached:
            logger.debug(f"Cache hit for user {user_id[:USER_ID_LOG_LENGTH]}")
            # Return as ChatResult with usage from cache if available
            cached_result: ChatResult = {
                "id": cached.get("id", ""),
                "content": cached.get("content", ""),
                "model": cached.get("model", "unknown"),
                "cached": True,
                "usage": cached.get("usage", {}),
            }
            return cached_result

        logger.debug(f"Cache miss for user {user_id[:USER_ID_LOG_LENGTH]}")

        # Generate response
        try:
            llm_response = await self.llm_provider.complete(content)
        except LLMProviderError:
            # Re-raise known provider errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error during LLM completion: {e}")
            raise LLMProviderError(f"Failed to generate response: {e}") from e

        # Save to database with usage tracking
        message_id = str(uuid.uuid4())
        try:
            await self.repository.save(
                id=message_id,
                user_id=user_id,
                content=content,
                response=llm_response.text,
                model=llm_response.model,
                usage=llm_response.usage,
            )
        except Exception as e:
            logger.error(f"Failed to save message {message_id}: {e}")
            raise StorageError(f"Failed to save chat message: {e}") from e

        # Log token usage for monitoring (structured logging for modern observability tools)
        if llm_response.usage:
            logger.info(
                "Token usage",
                user_id=user_id,
                model=llm_response.model,
                **llm_response.usage,
            )

        # Prepare response
        result: ChatResult = {
            "id": message_id,
            "content": llm_response.text,
            "model": llm_response.model,
            "cached": False,
            "usage": llm_response.usage,
        }

        # Cache it (exclude usage from cache)
        cache_data = {
            "id": message_id,
            "content": llm_response.text,
            "model": llm_response.model,
            "cached": False,
        }
        await self.cache.set(key, cache_data)

        return result

    async def get_history(self, user_id: str, limit: int = 10) -> list[MessageRecord]:
        """Get chat history for a user.

        Args:
            user_id: User identifier.
            limit: Maximum number of messages to return.

        Returns:
            List of message dictionaries.

        """
        return await self.repository.get_history(user_id, limit)  # type: ignore

    async def health_check(self) -> HealthStatus:
        """Check health of all system components.

        Returns:
            Dictionary with health status of each component.

        """
        logger.debug("Performing health checks")
        storage_ok = await self.repository.health_check()

        llm_ok = False
        try:
            llm_ok = await self.llm_provider.health_check()
            logger.debug(f"LLM health check: ok={llm_ok}")
        except Exception as e:  # noqa: BLE001
            logger.warning("LLM health check failed: {}", e)
            llm_ok = False

        result: HealthStatus = {"storage": storage_ok, "llm": llm_ok}
        return result
```

## File: config.py
```python
"""Configuration using pydantic-settings."""

import os

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
            msg = (
                "Gemini provider selected but CHAT_GEMINI_API_KEY not set. "
                "Please set the CHAT_GEMINI_API_KEY environment variable."
            )
            raise ValueError(
                msg,
            )
        if self.llm_provider == "openrouter" and not self.openrouter_api_key:
            msg = (
                "OpenRouter provider selected but CHAT_OPENROUTER_API_KEY not set. "
                "Please set the CHAT_OPENROUTER_API_KEY environment variable."
            )
            raise ValueError(
                msg,
            )
        if self.llm_provider not in ("gemini", "openrouter"):
            msg = f"Invalid LLM provider: {self.llm_provider}. Must be one of: gemini, openrouter"
            raise ValueError(
                msg,
            )
        return self

    @property
    def is_lambda_environment(self) -> bool:
        """Check if running in AWS Lambda."""
        return bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

    @property
    def effective_database_url(self) -> str:
        """Get the effective database URL based on environment."""
        if self.is_lambda_environment and not self.database_url.startswith("dynamodb"):
            return f"dynamodb://{self.dynamodb_table}?region={self.aws_region}"
        return self.database_url

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


# Module-level instance (for backward compatibility)
# New code should use dependency injection instead
settings = Settings()
```

## File: exceptions.py
```python
"""Domain-specific exceptions for the Chat API.

Simple, flat hierarchy with clear error messages.
Uses dataclasses for errors that need to carry context.
"""

from dataclasses import dataclass


class ChatAPIError(Exception):
    """Base exception for all Chat API errors."""


class LLMProviderError(ChatAPIError):
    """Error related to LLM provider operations."""


class StorageError(ChatAPIError):
    """Error related to storage operations."""


class CacheError(ChatAPIError):
    """Error related to cache operations."""


class ValidationError(ChatAPIError):
    """Error related to input validation (not Pydantic)."""


class ConfigurationError(ChatAPIError):
    """Error related to configuration issues."""


@dataclass
class RateLimitError(ChatAPIError):
    """Rate limit exceeded error with context."""

    user_id: str
    limit: str
    retry_after: int | None = None

    def __str__(self) -> str:
        msg = f"Rate limit exceeded for user {self.user_id} (limit: {self.limit})"
        if self.retry_after:
            msg += f". Retry after {self.retry_after} seconds"
        return msg


@dataclass
class RetryableError(ChatAPIError):
    """Error that can be retried with context."""

    operation: str
    attempts: int
    max_attempts: int
    last_error: Exception | None = None

    def __str__(self) -> str:
        msg = f"Operation '{self.operation}' failed after {self.attempts}/{self.max_attempts} attempts"
        if self.last_error:
            msg += f": {self.last_error}"
        return msg


@dataclass
class ResourceNotFoundError(StorageError):
    """Resource not found error with context."""

    resource_type: str
    resource_id: str

    def __str__(self) -> str:
        return f"{self.resource_type} with id '{self.resource_id}' not found"


@dataclass
class ConnectionFailureError(ChatAPIError):
    """Connection failure error with context."""

    service: str
    host: str | None = None
    port: int | None = None
    original_error: Exception | None = None

    def __str__(self) -> str:
        msg = f"Failed to connect to {self.service}"
        if self.host:
            msg += f" at {self.host}"
            if self.port:
                msg += f":{self.port}"
        if self.original_error:
            msg += f": {self.original_error}"
        return msg
```

## File: middleware.py
```python
"""Request tracking middleware."""

import uuid

from fastapi import Request
from loguru import logger


async def add_request_id(request: Request, call_next):
    """Add request ID to context for tracking.

    Args:
        request: Incoming FastAPI request.
        call_next: Next middleware or handler in chain.

    Returns:
        Response with X-Request-ID header.

    """
    # Generate or use existing request ID
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # Add to request state for access in handlers
    request.state.request_id = request_id

    # Add context for structured logging
    with logger.contextualize(request_id=request_id):
        logger.debug(
            "Request started",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        logger.debug(
            "Request completed",
            status_code=response.status_code,
        )

        return response
```

## File: providers.py
```python
"""LLM Provider abstractions using Strategy Pattern."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

import litellm
from loguru import logger

from .exceptions import ConfigurationError
from .retry import with_llm_retry
from .types import TokenUsage


def setup_litellm() -> None:
    """Setup litellm configuration."""
    import os

    litellm.set_verbose = False
    litellm.drop_params = True
    litellm.suppress_debug_info = True

    # Enable observability features
    os.environ["LITELLM_LOG"] = "INFO"  # Enable for metrics


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""

    model: str
    api_key: str | None = None
    timeout: int = 30
    temperature: float = 0.1  # Low temperature for consistent responses
    seed: int = 42  # Fixed seed for reproducibility


@dataclass
class LLMResponse:
    """Standard response from LLM providers."""

    text: str
    model: str
    usage: TokenUsage


class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    async def complete(self, prompt: str) -> LLMResponse:
        """Generate completion for the given prompt."""
        ...

    async def health_check(self) -> bool:
        """Check if the provider is configured and accessible."""
        ...


class GeminiProvider:
    """Gemini LLM provider implementation."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        if not config.api_key:
            raise ConfigurationError("Gemini API key is required")

        # Configure litellm
        setup_litellm()

    @with_llm_retry(
        provider_name="Gemini",
        max_retries=3,
        min_wait=1,
        max_wait=10,
    )
    async def complete(self, prompt: str) -> LLMResponse:
        """Generate completion using Gemini."""
        response = await litellm.acompletion(
            model=self.config.model,
            messages=[{"role": "user", "content": prompt}],
            timeout=self.config.timeout,
            api_key=self.config.api_key,
            temperature=self.config.temperature,
            seed=self.config.seed,
        )

        # Extract usage and calculate cost if available
        from .types import TokenUsage

        # Build properly typed usage dict
        typed_usage: TokenUsage = {}
        if response.usage:
            usage_data = response.usage.model_dump()
            if "prompt_tokens" in usage_data:
                typed_usage["prompt_tokens"] = usage_data["prompt_tokens"]
            if "completion_tokens" in usage_data:
                typed_usage["completion_tokens"] = usage_data["completion_tokens"]
            if "total_tokens" in usage_data:
                typed_usage["total_tokens"] = usage_data["total_tokens"]

            # Try to calculate cost
            try:
                cost = litellm.completion_cost(completion_response=response)
                if cost is not None:
                    typed_usage["cost_usd"] = Decimal(str(cost))
            except (ValueError, KeyError, TypeError, Exception) as e:
                logger.debug(f"Cost calculation not available for {response.model}: {e}")

        return LLMResponse(
            text=response.choices[0].message.content,
            model=response.model,
            usage=typed_usage,
        )

    async def health_check(self) -> bool:
        """Check Gemini provider health."""
        return bool(self.config.api_key)


class OpenRouterProvider:
    """OpenRouter LLM provider implementation."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        if not config.api_key:
            raise ConfigurationError("OpenRouter API key is required")

        # Configure litellm
        setup_litellm()

    @with_llm_retry(
        provider_name="OpenRouter",
        max_retries=3,
        min_wait=1,
        max_wait=10,
    )
    async def complete(self, prompt: str) -> LLMResponse:
        """Generate completion using OpenRouter."""
        response = await litellm.acompletion(
            model=self.config.model,
            messages=[{"role": "user", "content": prompt}],
            timeout=self.config.timeout,
            api_key=self.config.api_key,
            temperature=self.config.temperature,
            seed=self.config.seed,
        )

        # Extract usage and calculate cost if available
        from .types import TokenUsage

        # Build properly typed usage dict
        typed_usage: TokenUsage = {}
        if response.usage:
            usage_data = response.usage.model_dump()
            if "prompt_tokens" in usage_data:
                typed_usage["prompt_tokens"] = usage_data["prompt_tokens"]
            if "completion_tokens" in usage_data:
                typed_usage["completion_tokens"] = usage_data["completion_tokens"]
            if "total_tokens" in usage_data:
                typed_usage["total_tokens"] = usage_data["total_tokens"]

            # Try to calculate cost
            try:
                cost = litellm.completion_cost(completion_response=response)
                if cost is not None:
                    typed_usage["cost_usd"] = Decimal(str(cost))
            except (ValueError, KeyError, TypeError, Exception) as e:
                logger.debug(f"Cost calculation not available for {response.model}: {e}")

        return LLMResponse(
            text=response.choices[0].message.content,
            model=response.model,
            usage=typed_usage,
        )

    async def health_check(self) -> bool:
        """Check OpenRouter provider health."""
        return bool(self.config.api_key)


def create_llm_provider(
    provider_type: str,
    model: str,
    api_key: str | None = None,
    **kwargs: Any,
) -> LLMProvider:
    """Factory function to create LLM provider instances.

    Args:
        provider_type: Type of provider ('gemini', 'openrouter').
        model: Model identifier.
        api_key: API key for the provider.
        **kwargs: Additional configuration options.

    Returns:
        LLMProvider instance.

    Raises:
        ConfigurationError: If provider type is unknown or configuration is invalid.

    """
    config = LLMConfig(
        model=model,
        api_key=api_key,
        timeout=kwargs.get("timeout", 30),
    )

    providers = {
        "gemini": GeminiProvider,
        "openrouter": OpenRouterProvider,
    }

    provider_class = providers.get(provider_type.lower())
    if not provider_class:
        raise ConfigurationError(
            f"Unknown provider type: {provider_type}. Must be 'gemini' or 'openrouter'",
        )

    return provider_class(config)  # type: ignore
```

## File: retry.py
```python
"""Retry logic for the Chat API using stamina."""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import stamina
from loguru import logger

from .exceptions import LLMProviderError

F = TypeVar("F", bound=Callable[..., Any])


def with_llm_retry(
    provider_name: str,
    max_retries: int = 3,
    min_wait: int = 1,
    max_wait: int = 10,
) -> Callable[[F], F]:
    """Decorator to add retry logic to LLM provider methods using stamina.

    Args:
        provider_name: Name of the provider for error messages
        max_retries: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorated function with retry logic

    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Configure stamina for this specific call
            retrying = stamina.retry_context(
                on=(TimeoutError, ConnectionError, LLMProviderError),
                attempts=max_retries,
                wait_initial=min_wait,
                wait_max=max_wait,
                wait_jitter=True,  # Add jitter to prevent thundering herd
            )

            async for attempt in retrying:
                with attempt:
                    try:
                        return await func(*args, **kwargs)
                    except TimeoutError as e:
                        logger.warning(f"{provider_name} attempt {attempt.num}: Timeout - {e}")
                        if attempt.num == max_retries:
                            raise LLMProviderError(f"{provider_name} request timed out") from e
                        raise
                    except ConnectionError as e:
                        logger.warning(
                            f"{provider_name} attempt {attempt.num}: Connection failed - {e}"
                        )
                        if attempt.num == max_retries:
                            raise LLMProviderError(
                                f"Failed to connect to {provider_name} API"
                            ) from e
                        raise
                    except Exception as e:
                        logger.error(f"{provider_name} attempt {attempt.num}: Failed - {e}")
                        if attempt.num == max_retries:
                            raise LLMProviderError(f"{provider_name} API error: {e}") from e
                        raise

            # This should never be reached due to stamina's retry_context behavior
            # but ruff requires an explicit return or raise
            raise LLMProviderError(f"{provider_name} retry logic failed unexpectedly")

        return wrapper  # type: ignore[return-value,no-any-return]

    return decorator
```

## File: storage.py
```python
"""Unified storage layer - SQLite, DynamoDB, and caching (Python 2025 style)."""

import hashlib
import json
import time
from typing import Any, Protocol
from urllib.parse import parse_qs, urlparse

from cachetools import TTLCache  # type: ignore[import-untyped]
from databases import Database
from loguru import logger

from .exceptions import StorageError
from .types import MessageRecord

# Constants
CACHE_TTL_SECONDS = 3600  # 1 hour default cache TTL
TTL_DAYS = 30  # DynamoDB TTL in days
CACHE_KEY_LENGTH = 32  # Blake2b hash output length
DEFAULT_CACHE_SIZE = 1000  # Default max cache size


# ============== Protocols ==============
class Repository(Protocol):
    """Storage repository protocol."""

    async def startup(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def save(self, **kwargs) -> None: ...
    async def get_history(self, user_id: str, limit: int) -> list[MessageRecord]: ...
    async def health_check(self) -> bool: ...


class Cache(Protocol):
    """Cache protocol."""

    async def startup(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def get(self, key: str) -> dict[str, Any] | None: ...
    async def set(self, key: str, value: dict[str, Any], ttl: int = CACHE_TTL_SECONDS) -> None: ...


# ============== Cache Implementations ==============
def cache_key(user_id: str, content: str) -> str:
    """Generate secure cache key from user ID and content."""
    combined = f"{user_id}:{content}"
    return hashlib.blake2b(combined.encode(), digest_size=16, salt=b"chat-cache-v1").hexdigest()


class InMemoryCache:
    """In-memory cache using cachetools TTLCache."""

    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE, ttl: int = CACHE_TTL_SECONDS) -> None:
        self.cache: TTLCache[str, dict[str, Any]] = TTLCache(maxsize=max_size, ttl=ttl)
        self.default_ttl = ttl
        logger.info(f"Using TTLCache with max size {max_size} and TTL {ttl}s")

    async def startup(self) -> None:
        """Initialize cache."""
        pass  # TTLCache doesn't need initialization

    async def shutdown(self) -> None:
        """Cleanup cache."""
        self.cache.clear()

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get value from cache."""
        try:
            value = self.cache[key]
        except KeyError:
            logger.debug(f"Cache miss: {key}")
            return None
        else:
            logger.debug(f"Cache hit: {key}")
            return value  # type: ignore[no-any-return]

    async def set(self, key: str, value: dict[str, Any], ttl: int = CACHE_TTL_SECONDS) -> None:
        """Set value in cache."""
        # Note: cachetools TTLCache uses a global TTL, not per-item
        # If we need per-item TTL, we'd need to store expiry time with the value
        self.cache[key] = value
        logger.debug(f"Cached: {key} (size: {len(self.cache)}/{self.cache.maxsize})")


class RedisCache:
    """Redis cache implementation."""

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self.client: Any = None
        logger.info(f"Redis cache configured: {redis_url}")

    async def startup(self) -> None:
        """Initialize Redis connection."""
        import redis.asyncio as redis

        try:
            self.client = await redis.from_url(self.redis_url)
            await self.client.ping()
            logger.info("Redis cache connected")
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to in-memory cache.")
            # Fallback to in-memory with cachetools
            self._fallback = InMemoryCache()
            await self._fallback.startup()

    async def shutdown(self) -> None:
        """Close Redis connection."""
        if self.client:
            await self.client.close()

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get value from Redis."""
        if hasattr(self, "_fallback"):
            return await self._fallback.get(key)

        if not self.client:
            return None

        try:
            data = await self.client.get(key)
            if data:
                return json.loads(data)  # type: ignore[no-any-return]
        except (json.JSONDecodeError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis get error: {e}")
        return None

    async def set(self, key: str, value: dict[str, Any], ttl: int = 3600) -> None:
        """Set value in Redis with TTL."""
        if hasattr(self, "_fallback"):
            return await self._fallback.set(key, value, ttl)

        if not self.client:
            return None

        try:
            await self.client.setex(key, ttl, json.dumps(value))
        except (json.JSONDecodeError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis set error: {e}")


# ============== Repository Implementations ==============
class SQLiteRepository:
    """SQLite repository with connection pooling for production use."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        # SQLite doesn't support connection pooling parameters like PostgreSQL
        # The databases library handles SQLite connections appropriately
        self.database = Database(database_url)
        logger.info(f"SQLite repository configured: {database_url}")

    async def startup(self) -> None:
        """Initialize database connection and create tables."""
        await self.database.connect()

        # Create table if not exists
        await self.database.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                response TEXT NOT NULL,
                model TEXT,
                usage TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index for user_id
        await self.database.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id
            ON chat_history(user_id, timestamp DESC)
        """)

        logger.info("SQLite repository initialized")

    async def shutdown(self) -> None:
        """Close database connection."""
        await self.database.disconnect()

    async def save(self, **kwargs) -> None:
        """Save message to database."""
        usage_json = json.dumps(kwargs.get("usage", {})) if kwargs.get("usage") else None

        await self.database.execute(
            """
            INSERT INTO chat_history (id, user_id, content, response, model, usage)
            VALUES (:id, :user_id, :content, :response, :model, :usage)
            """,
            {
                "id": kwargs["id"],
                "user_id": kwargs["user_id"],
                "content": kwargs["content"],
                "response": kwargs["response"],
                "model": kwargs.get("model"),
                "usage": usage_json,
            },
        )

    async def get_history(self, user_id: str, limit: int = 10) -> list[MessageRecord]:
        """Get chat history for a user."""
        rows = await self.database.fetch_all(
            """
            SELECT id, user_id, content, response, model, usage, timestamp
            FROM chat_history
            WHERE user_id = :user_id
            ORDER BY timestamp DESC
            LIMIT :limit
            """,
            {"user_id": user_id, "limit": limit},
        )

        results: list[MessageRecord] = []
        for row in rows:
            record: MessageRecord = {
                "id": row["id"],
                "user_id": row["user_id"],
                "content": row["content"],
                "response": row["response"],
                "model": row["model"],
                "usage": json.loads(row["usage"]) if row["usage"] else None,
                "timestamp": row["timestamp"].isoformat()
                if hasattr(row["timestamp"], "isoformat")
                else str(row["timestamp"])
                if row["timestamp"]
                else "",
            }
            results.append(record)
        return results

    async def health_check(self) -> bool:
        """Check database health."""
        try:
            await self.database.execute("SELECT 1")
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error(f"Database health check failed: {e}")
            return False
        else:
            return True


class DynamoDBRepository:
    """DynamoDB repository for production."""

    def __init__(self, database_url: str) -> None:
        parsed = urlparse(database_url)
        self.table_name = parsed.netloc or parsed.path.lstrip("/")

        # Parse query parameters
        params = parse_qs(parsed.query) if parsed.query else {}
        self.region = params.get("region", ["us-east-1"])[0]

        self.session: Any = None
        logger.info(f"DynamoDB repository configured: {self.table_name} in {self.region}")

    async def startup(self) -> None:
        """Initialize DynamoDB session."""
        import aioboto3

        self.session = aioboto3.Session()

        # Check if table exists, create if not
        try:
            async with self.session.client("dynamodb", region_name=self.region) as client:
                await client.describe_table(TableName=self.table_name)
                logger.info(f"DynamoDB table {self.table_name} exists")
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.info(f"Table {self.table_name} does not exist, creating: {e}")
            await self._create_table()

    async def _create_table(self) -> None:
        """Create DynamoDB table."""
        async with self.session.client("dynamodb", region_name=self.region) as client:
            await client.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "timestamp", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "timestamp", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            # Wait for table to be active
            waiter = client.get_waiter("table_exists")
            await waiter.wait(TableName=self.table_name)

    async def shutdown(self) -> None:
        """Clean up DynamoDB session."""
        # Session doesn't need explicit cleanup in aioboto3

    async def save(self, **kwargs) -> None:
        """Save message to DynamoDB."""
        from datetime import UTC, datetime

        item = {
            "user_id": kwargs["user_id"],
            "timestamp": datetime.now(UTC).isoformat(),
            "id": kwargs["id"],
            "content": kwargs["content"],
            "response": kwargs["response"],
            "model": kwargs.get("model"),
            "usage": kwargs.get("usage"),
            "ttl": int(time.time()) + 86400 * TTL_DAYS,  # TTL in seconds
        }

        async with self.session.client("dynamodb", region_name=self.region) as client:
            await client.put_item(TableName=self.table_name, Item=self._serialize(item))

    async def get_history(self, user_id: str, limit: int = 10) -> list[MessageRecord]:
        """Get chat history from DynamoDB."""
        async with self.session.client("dynamodb", region_name=self.region) as client:
            response = await client.query(
                TableName=self.table_name,
                KeyConditionExpression="user_id = :user_id",
                ExpressionAttributeValues={":user_id": {"S": user_id}},
                Limit=limit,
                ScanIndexForward=False,  # Descending order
            )

        results: list[MessageRecord] = []
        for item in response.get("Items", []):
            record: MessageRecord = self._deserialize(item)  # type: ignore
            results.append(record)
        return results

    async def health_check(self) -> bool:
        """Check DynamoDB health."""
        try:
            async with self.session.client("dynamodb", region_name=self.region) as client:
                await client.describe_table(TableName=self.table_name)
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error(f"DynamoDB health check failed: {e}")
            return False
        else:
            return True

    def _serialize(self, item: dict) -> dict:
        """Convert Python dict to DynamoDB format."""
        result = {}
        for key, value in item.items():
            if value is None:
                continue
            if isinstance(value, str):
                result[key] = {"S": value}
            elif isinstance(value, int | float):
                result[key] = {"N": str(value)}
            elif isinstance(value, dict):
                result[key] = {"M": self._serialize(value)}  # type: ignore[dict-item]
            elif isinstance(value, list):
                result[key] = {"L": [self._serialize_value(v) for v in value]}  # type: ignore[dict-item]
        return result

    def _serialize_value(self, value) -> dict:
        """Serialize a single value."""
        if isinstance(value, str):
            return {"S": value}
        if isinstance(value, int | float):
            return {"N": str(value)}
        if isinstance(value, dict):
            return {"M": self._serialize(value)}
        return {"NULL": True}

    def _deserialize(self, item: dict) -> dict:
        """Convert DynamoDB format to Python dict."""
        result = {}
        for key, value in item.items():
            if "S" in value:
                result[key] = value["S"]
            elif "N" in value:
                result[key] = float(value["N"])
            elif "M" in value:
                result[key] = self._deserialize(value["M"])
            elif "L" in value:
                result[key] = [self._deserialize_value(v) for v in value["L"]]
        return result

    def _deserialize_value(self, value: dict) -> Any:
        """Deserialize a single value."""
        if "S" in value:
            return value["S"]
        if "N" in value:
            return float(value["N"])
        if "M" in value:
            return self._deserialize(value["M"])
        return None


# ============== Factory Functions ==============
def create_repository(database_url: str | None = None) -> Repository:
    """Create repository instance based on database URL."""
    from .config import settings

    # Use provided URL or get effective URL from settings
    if database_url is None:
        url = settings.effective_database_url
        if settings.is_lambda_environment:
            logger.info(f"AWS Lambda detected, using DynamoDB: {settings.dynamodb_table}")
    else:
        url = database_url

    parsed = urlparse(url)

    if parsed.scheme == "dynamodb":
        logger.info("Creating DynamoDB repository")
        return DynamoDBRepository(url)
    if parsed.scheme in ("sqlite", "sqlite+aiosqlite") or url.startswith("sqlite"):
        logger.info("Creating SQLite repository")
        return SQLiteRepository(url)
    raise StorageError(f"Unsupported database URL scheme: {url}. Must be 'sqlite' or 'dynamodb://'")


def create_cache(redis_url: str | None = None) -> Cache:
    """Create cache instance based on configuration."""
    from .config import settings

    # Try Redis if configured
    url = redis_url or settings.redis_url
    if url:
        logger.info("Creating Redis cache")
        return RedisCache(url)

    # Default to in-memory cache
    logger.info("Using in-memory cache")
    return InMemoryCache()


# Export public API
__all__ = [
    "Cache",
    "DynamoDBRepository",
    "InMemoryCache",
    "RedisCache",
    "Repository",
    "SQLiteRepository",
    "cache_key",
    "create_cache",
    "create_repository",
]
```

## File: types.py
```python
"""Type definitions for the Chat API."""

from decimal import Decimal
from typing import TypedDict


class TokenUsage(TypedDict, total=False):
    """Token usage information from LLM API."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: Decimal


class HealthStatus(TypedDict):
    """Health status of system components."""

    storage: bool
    llm: bool


class ChatResult(TypedDict):
    """Result from chat processing."""

    id: str
    content: str
    model: str
    cached: bool
    usage: TokenUsage


class MessageRecord(TypedDict, total=False):
    """Database record for a chat message."""

    id: str
    user_id: str
    content: str
    response: str
    model: str | None
    usage: TokenUsage | None
    timestamp: str
```
