"""Unit tests for data models"""

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from pydantic import ValidationError

from src.chat.models import ChatRequest, ChatResponse, ErrorResponse, HealthResponse


class TestChatRequest:
    """Test ChatRequest model validation"""

    def test_should_create_valid_request(self):
        """Should create valid chat request with required fields."""
        request = ChatRequest(prompt="Hello, world!", userId="user123")
        assert request.prompt == "Hello, world!"
        assert request.userId == "user123"

    def test_should_reject_userid_with_special_characters(self):
        """Should reject userId containing special characters."""
        with pytest.raises(ValidationError):
            ChatRequest(prompt="Test prompt", userId="user@123")

    def test_should_reject_empty_prompt(self):
        """Should reject empty prompt with validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(prompt="", userId="user123")

        errors = exc_info.value.errors()
        assert any("at least 1 character" in str(error) for error in errors)

    def test_should_sanitize_pii_data(self):
        """Should sanitize PII data from prompts."""
        request = ChatRequest(
            prompt="My CPF is 123.456.789-00 and email is test@example.com", userId="user123"
        )
        assert "[CPF_REMOVED]" in request.prompt
        assert "[EMAIL_REMOVED]" in request.prompt
        assert "123.456.789-00" not in request.prompt
        assert "test@example.com" not in request.prompt

    def test_should_accept_maximum_length_prompt(self):
        """Should accept prompts up to 4000 characters."""
        long_prompt = "x" * 4000  # Max is 4000
        request = ChatRequest(prompt=long_prompt, userId="user123")
        assert len(request.prompt) == 4000

    def test_should_reject_prompt_exceeding_limit(self):
        """Should reject prompts exceeding 4000 characters."""
        with pytest.raises(ValidationError):
            ChatRequest(prompt="x" * 4001, userId="user123")

    def test_should_accept_special_characters_in_prompt(self):
        """Should accept prompts with emojis and special characters."""
        special_prompt = "Hello! 😊 How are you? #test @user"
        request = ChatRequest(prompt=special_prompt, userId="user123")
        assert request.prompt == special_prompt

    def test_should_detect_sql_injection_patterns(self):
        """Should detect and reject SQL injection patterns."""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(prompt="DROP TABLE users; SELECT * FROM data", userId="user123")
        assert "dangerous content" in str(exc_info.value).lower()


class TestChatResponse:
    """Test ChatResponse model"""

    def test_should_create_valid_response(self):
        """Should create valid chat response with required fields."""
        response = ChatResponse(
            id="int123",
            userId="user123",
            prompt="Test prompt",
            response="Test response",
            model="gemini-pro",
            timestamp=datetime.now(UTC).isoformat(),
            cached=False,
        )

        assert response.id == "int123"
        assert response.userId == "user123"
        assert response.prompt == "Test prompt"
        assert response.response == "Test response"
        assert response.model == "gemini-pro"
        assert response.cached is False

    def test_should_handle_cached_response(self):
        """Should handle response marked as cached."""
        response = ChatResponse(
            id="int456",
            userId="user123",
            prompt="Test prompt",
            response="Cached response",
            model="cache",
            timestamp=datetime.now(UTC).isoformat(),
            cached=True,
        )

        assert response.cached is True
        assert response.model == "cache"

    def test_should_serialize_to_dict(self):
        """Should serialize response to dictionary."""
        response = ChatResponse(
            id="int789",
            userId="user123",
            prompt="Test prompt",
            response="Test",
            model="mock",
            timestamp=datetime.now(UTC).isoformat(),
            cached=False,
        )

        data = response.model_dump()
        assert isinstance(data, dict)
        assert data["id"] == "int789"
        assert data["userId"] == "user123"
        assert data["prompt"] == "Test prompt"
        assert data["response"] == "Test"
        assert data["model"] == "mock"
        assert "timestamp" in data
        assert data["cached"] is False


class TestHealthResponse:
    """Test HealthResponse model"""

    def test_should_create_healthy_status(self):
        """Should create healthy status response."""
        response = HealthResponse(
            status="healthy", version="1.0.0", timestamp=datetime.now(UTC).isoformat()
        )

        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert response.timestamp is not None

    def test_should_serialize_health_response(self):
        """Should serialize health response to dictionary."""
        response = HealthResponse(
            status="healthy", version="1.0.0", timestamp=datetime.now(UTC).isoformat()
        )

        data = response.model_dump()
        assert isinstance(data, dict)
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data


class TestErrorResponse:
    """Test ErrorResponse model"""

    def test_should_create_error_response(self):
        """Should create error response with details."""
        response = ErrorResponse(
            error="Something went wrong", detail="Database connection failed", trace_id="trace-123"
        )

        assert response.error == "Something went wrong"
        assert response.detail == "Database connection failed"
        assert response.trace_id == "trace-123"
        assert response.timestamp is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
