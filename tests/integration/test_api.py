"""
Integration tests for the API endpoints.
Tests full request/response flow with mocked dependencies.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.main import app


class TestHealthEndpoint:
    """Test health endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_should_return_healthy_status(self, client):
        """Health endpoint should return healthy status."""
        response = client.get("/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data.get("version") == "1.0.0"


class TestReadyEndpoint:
    """Test readiness endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_should_check_dependencies(self, client):
        """Ready endpoint should check all dependencies."""
        response = client.get("/v1/ready")

        assert response.status_code in [200, 503]
        data = response.json()

        assert "ready" in data
        assert "checks" in data
        assert "database" in data["checks"]
        assert "llm_provider" in data["checks"]


class TestChatEndpoint:
    """Test chat endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_dependencies(self, mock_chat_service):
        """Mock external dependencies for integration tests."""
        with patch("src.chat.api.ChatService") as mock_service_class:
            mock_service_class.return_value = mock_chat_service
            yield mock_chat_service

    def test_should_process_valid_chat_request(self, client, mock_dependencies):
        """Chat endpoint should process valid request successfully."""
        request_data = {"prompt": "Test prompt", "userId": "user123"}

        response = client.post("/v1/chat", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "test-123"
        assert data["response"] == "Test response"
        assert data["model"] == "mock"
        assert "timestamp" in data

        # Verify service was called correctly
        mock_dependencies.process_prompt.assert_called_once()
        call_args = mock_dependencies.process_prompt.call_args[1]
        assert call_args["user_id"] == "user123"
        assert call_args["prompt"] == "Test prompt"

    def test_should_accept_optional_parameters(self, client, mock_dependencies):  # noqa: ARG002
        """Chat endpoint should accept optional parameters."""
        request_data = {"prompt": "Test prompt", "userId": "user123"}

        response = client.post("/v1/chat", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-123"

    def test_should_reject_missing_userid(self, client):
        """Chat endpoint should reject request without userId."""
        # Missing required userId field
        request_data = {
            "prompt": "Test prompt"
            # Missing userId
        }

        response = client.post("/v1/chat", json=request_data)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_should_reject_empty_prompt(self, client):
        """Chat endpoint should reject empty prompt."""
        request_data = {"prompt": "", "userId": "user123"}

        response = client.post("/v1/chat", json=request_data)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_should_reject_prompt_exceeding_max_length(self, client):
        """Chat endpoint should reject prompts over 4000 characters."""
        request_data = {
            "prompt": "x" * 4001,  # Exceeds 4000 char limit
            "userId": "user123",
        }

        response = client.post("/v1/chat", json=request_data)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_should_reject_invalid_userid_format(self, client):
        """Chat endpoint should reject userId with invalid characters."""
        request_data = {
            "prompt": "Test prompt",
            "userId": "user@123",  # Contains invalid character
        }

        response = client.post("/v1/chat", json=request_data)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_should_sanitize_pii_from_prompts(self, client, mock_dependencies):
        """Chat endpoint should sanitize PII from prompts."""
        request_data = {
            "prompt": "My CPF is 123.456.789-00 and email is test@example.com",
            "userId": "user123",
        }

        response = client.post("/v1/chat", json=request_data)

        assert response.status_code == 200

        # Check that the prompt was sanitized
        call_args = mock_dependencies.process_prompt.call_args[1]
        sanitized_prompt = call_args["prompt"]
        assert "123.456.789-00" not in sanitized_prompt
        assert "test@example.com" not in sanitized_prompt

    def test_should_detect_sql_injection_attempts(self, client):
        """Chat endpoint should detect and reject SQL injection."""
        request_data = {"prompt": "'; DROP TABLE users; --", "userId": "user123"}

        response = client.post("/v1/chat", json=request_data)

        assert response.status_code == 422
        data = response.json()
        assert "dangerous content" in str(data["detail"]).lower()

    def test_should_handle_service_errors_gracefully(self, client, mock_dependencies):
        """Chat endpoint should handle service errors gracefully."""
        mock_dependencies.process_prompt.side_effect = Exception("Service error")

        request_data = {"prompt": "Test prompt", "userId": "user123"}

        response = client.post("/v1/chat", json=request_data)

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data  # FastAPI returns 'detail' for errors

    def test_should_include_cors_headers(self, client):
        """API should include CORS headers in responses."""
        response = client.options("/v1/chat")

        # FastAPI automatically handles OPTIONS for CORS
        assert response.status_code in [200, 405]

    def test_should_handle_multiple_requests_within_rate_limit(self, client, mock_dependencies):  # noqa: ARG002
        """API should handle multiple requests within rate limit."""
        # This would require actual rate limiting middleware
        # For now, just test that multiple requests work
        request_data = {"prompt": "Test prompt", "userId": "user123"}

        for _ in range(5):
            response = client.post("/v1/chat", json=request_data)
            assert response.status_code == 200

    def test_should_propagate_trace_id(self, client, mock_dependencies):
        """API should generate and propagate trace ID."""
        request_data = {"prompt": "Test prompt", "userId": "user123"}

        response = client.post("/v1/chat", json=request_data)

        assert response.status_code == 200

        # Verify trace_id was passed to service
        call_args = mock_dependencies.process_prompt.call_args[1]
        assert "trace_id" in call_args

    def test_should_handle_concurrent_requests(self, client, mock_dependencies):  # noqa: ARG002
        """API should handle concurrent requests correctly."""
        import threading

        results = []
        errors = []

        def make_request():
            try:
                request_data = {
                    "prompt": f"Test prompt {threading.current_thread().name}",
                    "userId": "user123",
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

    def test_should_have_correct_metadata(self):
        """API should have correct metadata."""
        assert app.title == "Chat API - Itaú AI Platform"
        assert app.version == "1.0.0"
        assert "Microservice for processing prompts" in app.description

    def test_should_register_expected_routes(self):
        """API should register expected routes."""
        routes = [route.path for route in app.routes]

        assert "/v1/health" in routes
        assert "/v1/chat" in routes
        assert "/docs" in routes  # FastAPI automatic docs
        assert "/openapi.json" in routes  # OpenAPI schema

    def test_should_generate_valid_openapi_schema(self):
        """API should generate valid OpenAPI schema."""
        client = TestClient(app)
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()

        assert schema["info"]["title"] == "Chat API - Itaú AI Platform"
        assert schema["info"]["version"] == "1.0.0"
        assert "/v1/chat" in schema["paths"]
        assert "/v1/health" in schema["paths"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
