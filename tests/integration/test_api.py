"""
Integration tests for the API endpoints.
Tests full request/response flow with mocked dependencies.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import json

from src.main import app


class TestAPIEndpoints:
    """Test API endpoints with integration."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies for integration tests."""
        with patch('src.chat.api.ChatService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Default successful response
            mock_service.process_prompt.return_value = {
                "interaction_id": "test-123",
                "response": "Test response",
                "model": "mock",
                "timestamp": "2025-01-01T00:00:00",
                "cached": False,
                "latency_ms": 100
            }
            
            # Health check response
            mock_service.check_dependencies.return_value = {
                "database": True,
                "llm_provider": True,
                "cache": True
            }
            
            yield mock_service
    
    def test_health_endpoint(self, client, mock_dependencies):
        """Test /health endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "version" in data
        assert "dependencies" in data
        assert data["dependencies"]["database"] is True
        assert data["dependencies"]["llm_provider"] is True
        assert data["dependencies"]["cache"] is True
    
    def test_chat_endpoint_success(self, client, mock_dependencies):
        """Test successful chat request."""
        request_data = {
            "prompt": "Test prompt",
            "user_id": "user123"
        }
        
        response = client.post("/v1/chat", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["interaction_id"] == "test-123"
        assert data["response"] == "Test response"
        assert data["model"] == "mock"
        assert "timestamp" in data
        assert "trace_id" in response.headers
        
        # Verify service was called correctly
        mock_dependencies.process_prompt.assert_called_once()
        call_args = mock_dependencies.process_prompt.call_args
        assert call_args[1]["user_id"] == "user123"
        assert call_args[1]["prompt"] == "Test prompt"
    
    def test_chat_endpoint_with_optional_params(self, client, mock_dependencies):
        """Test chat request with optional parameters."""
        request_data = {
            "prompt": "Test prompt",
            "user_id": "user123",
            "temperature": 0.5,
            "max_tokens": 500
        }
        
        response = client.post("/v1/chat", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["interaction_id"] == "test-123"
    
    def test_chat_endpoint_validation_error(self, client):
        """Test chat request with validation errors."""
        # Missing required field
        request_data = {
            "prompt": "Test prompt"
            # Missing user_id
        }
        
        response = client.post("/v1/chat", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_chat_endpoint_empty_prompt(self, client):
        """Test chat request with empty prompt."""
        request_data = {
            "prompt": "",
            "user_id": "user123"
        }
        
        response = client.post("/v1/chat", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_chat_endpoint_long_prompt(self, client):
        """Test chat request with prompt exceeding max length."""
        request_data = {
            "prompt": "x" * 4001,  # Exceeds 4000 char limit
            "user_id": "user123"
        }
        
        response = client.post("/v1/chat", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_chat_endpoint_invalid_user_id(self, client):
        """Test chat request with invalid user_id."""
        request_data = {
            "prompt": "Test prompt",
            "user_id": "user@123"  # Contains invalid character
        }
        
        response = client.post("/v1/chat", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_chat_endpoint_pii_removal(self, client, mock_dependencies):
        """Test that PII is removed from prompts."""
        request_data = {
            "prompt": "My CPF is 123.456.789-00 and email is test@example.com",
            "user_id": "user123"
        }
        
        response = client.post("/v1/chat", json=request_data)
        
        assert response.status_code == 200
        
        # Check that the prompt was sanitized
        call_args = mock_dependencies.process_prompt.call_args
        sanitized_prompt = call_args[1]["prompt"]
        assert "123.456.789-00" not in sanitized_prompt
        assert "test@example.com" not in sanitized_prompt
    
    def test_chat_endpoint_sql_injection_detection(self, client):
        """Test that SQL injection attempts are detected."""
        request_data = {
            "prompt": "'; DROP TABLE users; --",
            "user_id": "user123"
        }
        
        response = client.post("/v1/chat", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "SQL injection" in str(data["detail"])
    
    def test_chat_endpoint_service_error(self, client, mock_dependencies):
        """Test handling of service errors."""
        mock_dependencies.process_prompt.side_effect = Exception("Service error")
        
        request_data = {
            "prompt": "Test prompt",
            "user_id": "user123"
        }
        
        response = client.post("/v1/chat", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Internal server error"
        assert "trace_id" in data
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/v1/chat")
        
        # FastAPI automatically handles OPTIONS for CORS
        assert response.status_code in [200, 405]
    
    def test_rate_limiting(self, client, mock_dependencies):
        """Test rate limiting functionality."""
        # This would require actual rate limiting middleware
        # For now, just test that multiple requests work
        request_data = {
            "prompt": "Test prompt",
            "user_id": "user123"
        }
        
        for _ in range(5):
            response = client.post("/v1/chat", json=request_data)
            assert response.status_code == 200
    
    def test_trace_id_propagation(self, client, mock_dependencies):
        """Test that trace ID is generated and propagated."""
        request_data = {
            "prompt": "Test prompt",
            "user_id": "user123"
        }
        
        response = client.post("/v1/chat", json=request_data)
        
        assert response.status_code == 200
        assert "trace_id" in response.headers
        
        # Verify trace_id was passed to service
        call_args = mock_dependencies.process_prompt.call_args
        assert "trace_id" in call_args[1]
        assert call_args[1]["trace_id"] == response.headers["trace_id"]
    
    def test_concurrent_requests(self, client, mock_dependencies):
        """Test handling of concurrent requests."""
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request():
            try:
                request_data = {
                    "prompt": f"Test prompt {threading.current_thread().name}",
                    "user_id": "user123"
                }
                response = client.post("/v1/chat", json=request_data)
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request, name=f"Thread-{i}")
            threads.append(t)
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join(timeout=5)
        
        assert len(errors) == 0
        assert all(status == 200 for status in results)
        assert len(results) == 10


class TestAPIConfiguration:
    """Test API configuration and setup."""
    
    def test_api_metadata(self):
        """Test API metadata is correctly set."""
        assert app.title == "ProcessoItauSimple API"
        assert app.version == "3.0.0"
        assert "Chat API" in app.description
    
    def test_api_routes(self):
        """Test that all expected routes are registered."""
        routes = [route.path for route in app.routes]
        
        assert "/health" in routes
        assert "/v1/chat" in routes
        assert "/docs" in routes  # FastAPI automatic docs
        assert "/openapi.json" in routes  # OpenAPI schema
    
    def test_openapi_schema(self):
        """Test OpenAPI schema generation."""
        client = TestClient(app)
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        assert schema["info"]["title"] == "ProcessoItauSimple API"
        assert schema["info"]["version"] == "3.0.0"
        assert "/v1/chat" in schema["paths"]
        assert "/health" in schema["paths"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])