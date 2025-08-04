"""Unit tests for data models"""
import pytest
from datetime import datetime
from pydantic import ValidationError
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.chat.models import ChatRequest, ChatResponse, HealthResponse, ErrorResponse


class TestChatRequest:
    """Test ChatRequest model validation"""
    
    def test_valid_request(self):
        """Test creating a valid chat request"""
        request = ChatRequest(
            prompt="Hello, world!",
            userId="user123"
        )
        assert request.prompt == "Hello, world!"
        assert request.userId == "user123"
    
    def test_invalid_user_id(self):
        """Test request with invalid user_id characters"""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(prompt="Test prompt", userId="user@123")
    
    def test_empty_prompt_validation(self):
        """Test that empty prompt raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(prompt="", userId="user123")
        
        errors = exc_info.value.errors()
        assert any('at least 1 character' in str(error) for error in errors)
    
    def test_pii_removal(self):
        """Test that PII is removed from prompts"""
        request = ChatRequest(
            prompt="My CPF is 123.456.789-00 and email is test@example.com",
            userId="user123"
        )
        assert "[CPF_REMOVED]" in request.prompt
        assert "[EMAIL_REMOVED]" in request.prompt
        assert "123.456.789-00" not in request.prompt
        assert "test@example.com" not in request.prompt
    
    def test_long_prompt(self):
        """Test handling of long prompts"""
        long_prompt = "x" * 4000  # Max is 4000
        request = ChatRequest(prompt=long_prompt, userId="user123")
        assert len(request.prompt) == 4000
    
    def test_prompt_too_long(self):
        """Test that prompts over 4000 chars are rejected"""
        with pytest.raises(ValidationError):
            ChatRequest(prompt="x" * 4001, userId="user123")
    
    def test_special_characters_in_prompt(self):
        """Test prompts with special characters"""
        special_prompt = "Hello! 😊 How are you? #test @user"
        request = ChatRequest(prompt=special_prompt, userId="user123")
        assert request.prompt == special_prompt
    
    def test_sql_injection_detection(self):
        """Test that SQL injection patterns are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(
                prompt="DROP TABLE users; SELECT * FROM data",
                userId="user123"
            )
        assert "dangerous content" in str(exc_info.value).lower()


class TestChatResponse:
    """Test ChatResponse model"""
    
    def test_valid_response(self):
        """Test creating a valid chat response"""
        response = ChatResponse(
            id="int123",
            userId="user123",
            prompt="Test prompt",
            response="Test response",
            model="gemini-pro",
            timestamp=datetime.utcnow().isoformat(),
            cached=False
        )
        
        assert response.id == "int123"
        assert response.userId == "user123"
        assert response.prompt == "Test prompt"
        assert response.response == "Test response"
        assert response.model == "gemini-pro"
        assert response.cached is False
    
    def test_cached_response(self):
        """Test response from cache"""
        response = ChatResponse(
            id="int456",
            userId="user123",
            prompt="Test prompt",
            response="Cached response",
            model="cache",
            timestamp=datetime.utcnow().isoformat(),
            cached=True
        )
        
        assert response.cached is True
        assert response.model == "cache"
    
    def test_response_serialization(self):
        """Test response can be serialized to dict"""
        response = ChatResponse(
            id="int789",
            userId="user123",
            prompt="Test prompt",
            response="Test",
            model="mock",
            timestamp=datetime.utcnow().isoformat(),
            cached=False
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
    
    def test_healthy_response(self):
        """Test creating a healthy status response"""
        response = HealthResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.utcnow().isoformat()
        )
        
        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert response.timestamp is not None
    
    def test_health_response_serialization(self):
        """Test health response serialization"""
        response = HealthResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.utcnow().isoformat()
        )
        
        data = response.model_dump()
        assert isinstance(data, dict)
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data


class TestErrorResponse:
    """Test ErrorResponse model"""
    
    def test_error_response(self):
        """Test creating an error response"""
        response = ErrorResponse(
            error="Something went wrong",
            detail="Database connection failed",
            trace_id="trace-123"
        )
        
        assert response.error == "Something went wrong"
        assert response.detail == "Database connection failed"
        assert response.trace_id == "trace-123"
        assert response.timestamp is not None


def test_all_models():
    """Run all model tests"""
    test_request = TestChatRequest()
    test_request.test_valid_request()
    test_request.test_invalid_user_id()
    test_request.test_pii_removal()
    test_request.test_long_prompt()
    test_request.test_prompt_too_long()
    test_request.test_special_characters_in_prompt()
    test_request.test_sql_injection_detection()
    
    test_response = TestChatResponse()
    test_response.test_valid_response()
    test_response.test_cached_response()
    test_response.test_response_serialization()
    
    test_health = TestHealthResponse()
    test_health.test_healthy_response()
    test_health.test_health_response_serialization()
    
    test_error = TestErrorResponse()
    test_error.test_error_response()
    
    print("✅ All model tests passed!")


if __name__ == "__main__":
    test_all_models()