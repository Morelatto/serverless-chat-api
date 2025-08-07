"""Custom exceptions for Chat API with proper error handling."""

from typing import Any


class ChatAPIException(Exception):
    """Base exception for all Chat API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        trace_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the exception with context."""
        self.message = message
        self.status_code = status_code
        self.trace_id = trace_id
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API response."""
        result = {
            "error": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
        }
        if self.trace_id:
            result["trace_id"] = self.trace_id
        if self.details:
            result["details"] = self.details
        return result


class ValidationException(ChatAPIException):
    """Raised when request validation fails."""

    def __init__(self, message: str, field: str | None = None, trace_id: str | None = None) -> None:
        details = {"field": field} if field else {}
        super().__init__(message, status_code=400, trace_id=trace_id, details=details)


class AuthenticationException(ChatAPIException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication required", trace_id: str | None = None) -> None:
        super().__init__(message, status_code=401, trace_id=trace_id)


class AuthorizationException(ChatAPIException):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Insufficient permissions", trace_id: str | None = None) -> None:
        super().__init__(message, status_code=403, trace_id=trace_id)


class RateLimitException(ChatAPIException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        limit: int,
        window: int = 60,
        trace_id: str | None = None,
    ) -> None:
        message = f"Rate limit exceeded: {limit} requests per {window} seconds"
        details = {"limit": limit, "window_seconds": window}
        super().__init__(message, status_code=429, trace_id=trace_id, details=details)


class ResourceNotFoundException(ChatAPIException):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        trace_id: str | None = None,
    ) -> None:
        message = f"{resource_type} with id '{resource_id}' not found"
        details = {"resource_type": resource_type, "resource_id": resource_id}
        super().__init__(message, status_code=404, trace_id=trace_id, details=details)


class LLMProviderException(ChatAPIException):
    """Raised when LLM provider fails."""

    def __init__(
        self,
        provider: str,
        original_error: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        message = f"LLM provider '{provider}' failed"
        if original_error:
            message += f": {original_error}"
        details = {"provider": provider, "original_error": original_error}
        super().__init__(message, status_code=503, trace_id=trace_id, details=details)


class DatabaseException(ChatAPIException):
    """Raised when database operations fail."""

    def __init__(
        self,
        operation: str,
        original_error: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        message = f"Database operation '{operation}' failed"
        if original_error:
            message += f": {original_error}"
        details = {"operation": operation, "original_error": original_error}
        super().__init__(message, status_code=503, trace_id=trace_id, details=details)


class CircuitBreakerOpenException(ChatAPIException):
    """Raised when circuit breaker is open."""

    def __init__(
        self,
        service: str,
        retry_after: int | None = None,
        trace_id: str | None = None,
    ) -> None:
        message = f"Service '{service}' is temporarily unavailable (circuit breaker open)"
        details = {"service": service}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(message, status_code=503, trace_id=trace_id, details=details)


class ConfigurationException(ChatAPIException):
    """Raised when configuration is invalid or missing."""

    def __init__(
        self,
        config_key: str,
        message: str | None = None,
    ) -> None:
        error_message = f"Configuration error for '{config_key}'"
        if message:
            error_message += f": {message}"
        super().__init__(error_message, status_code=500, details={"config_key": config_key})