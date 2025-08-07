"""Unit tests for custom exceptions."""

import pytest

from src.shared.exceptions import (
    AuthenticationException,
    AuthorizationException,
    ChatAPIException,
    CircuitBreakerOpenException,
    ConfigurationException,
    DatabaseException,
    LLMProviderException,
    RateLimitException,
    ResourceNotFoundException,
    ValidationException,
)


class TestChatAPIException:
    """Test base ChatAPIException."""

    def test_should_create_exception_with_defaults(self):
        """Should create exception with default values."""
        exc = ChatAPIException("Test error")
        
        assert exc.message == "Test error"
        assert exc.status_code == 500
        assert exc.trace_id is None
        assert exc.details == {}

    def test_should_create_exception_with_all_params(self):
        """Should create exception with all parameters."""
        exc = ChatAPIException(
            message="Test error",
            status_code=400,
            trace_id="trace-123",
            details={"field": "value"},
        )
        
        assert exc.message == "Test error"
        assert exc.status_code == 400
        assert exc.trace_id == "trace-123"
        assert exc.details == {"field": "value"}

    def test_should_convert_to_dict(self):
        """Should convert exception to dictionary."""
        exc = ChatAPIException(
            message="Test error",
            status_code=400,
            trace_id="trace-123",
            details={"field": "value"},
        )
        
        result = exc.to_dict()
        
        assert result["error"] == "ChatAPIException"
        assert result["message"] == "Test error"
        assert result["status_code"] == 400
        assert result["trace_id"] == "trace-123"
        assert result["details"] == {"field": "value"}

    def test_should_exclude_none_values_from_dict(self):
        """Should exclude None values from dictionary."""
        exc = ChatAPIException("Test error")
        result = exc.to_dict()
        
        assert "trace_id" not in result
        assert "details" not in result


class TestSpecificExceptions:
    """Test specific exception types."""

    def test_validation_exception(self):
        """Test ValidationException."""
        exc = ValidationException("Invalid input", field="email")
        
        assert exc.status_code == 400
        assert exc.details == {"field": "email"}

    def test_authentication_exception(self):
        """Test AuthenticationException."""
        exc = AuthenticationException()
        
        assert exc.status_code == 401
        assert exc.message == "Authentication required"

    def test_authorization_exception(self):
        """Test AuthorizationException."""
        exc = AuthorizationException()
        
        assert exc.status_code == 403
        assert exc.message == "Insufficient permissions"

    def test_rate_limit_exception(self):
        """Test RateLimitException."""
        exc = RateLimitException(limit=60, window=60)
        
        assert exc.status_code == 429
        assert "60 requests per 60 seconds" in exc.message
        assert exc.details["limit"] == 60
        assert exc.details["window_seconds"] == 60

    def test_resource_not_found_exception(self):
        """Test ResourceNotFoundException."""
        exc = ResourceNotFoundException(
            resource_type="User",
            resource_id="123",
        )
        
        assert exc.status_code == 404
        assert "User with id '123' not found" in exc.message
        assert exc.details["resource_type"] == "User"
        assert exc.details["resource_id"] == "123"

    def test_llm_provider_exception(self):
        """Test LLMProviderException."""
        exc = LLMProviderException(
            provider="gemini",
            original_error="API key invalid",
        )
        
        assert exc.status_code == 503
        assert "LLM provider 'gemini' failed" in exc.message
        assert "API key invalid" in exc.message
        assert exc.details["provider"] == "gemini"
        assert exc.details["original_error"] == "API key invalid"

    def test_database_exception(self):
        """Test DatabaseException."""
        exc = DatabaseException(
            operation="insert",
            original_error="Connection lost",
        )
        
        assert exc.status_code == 503
        assert "Database operation 'insert' failed" in exc.message
        assert "Connection lost" in exc.message

    def test_circuit_breaker_open_exception(self):
        """Test CircuitBreakerOpenException."""
        exc = CircuitBreakerOpenException(
            service="LLM",
            retry_after=30,
        )
        
        assert exc.status_code == 503
        assert "Service 'LLM' is temporarily unavailable" in exc.message
        assert exc.details["retry_after_seconds"] == 30

    def test_configuration_exception(self):
        """Test ConfigurationException."""
        exc = ConfigurationException(
            config_key="API_KEY",
            message="Must be set in production",
        )
        
        assert exc.status_code == 500
        assert "Configuration error for 'API_KEY'" in exc.message
        assert "Must be set in production" in exc.message