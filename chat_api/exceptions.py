"""Domain-specific exceptions for the Chat API.

Simple, flat hierarchy with clear error messages.
Uses dataclasses for errors that need to carry context.
"""

from dataclasses import dataclass


class ChatAPIError(Exception):
    """Base exception for all Chat API errors."""

    pass


class LLMProviderError(ChatAPIError):
    """Error related to LLM provider operations."""

    pass


class StorageError(ChatAPIError):
    """Error related to storage operations."""

    pass


class CacheError(ChatAPIError):
    """Error related to cache operations."""

    pass


class ValidationError(ChatAPIError):
    """Error related to input validation (not Pydantic)."""

    pass


class ConfigurationError(ChatAPIError):
    """Error related to configuration issues."""

    pass


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
