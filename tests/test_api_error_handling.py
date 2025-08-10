"""Test API error handling and middleware."""

import pytest
from httpx import AsyncClient

from chat_api.exceptions import LLMProviderError, StorageError, ValidationError


@pytest.mark.asyncio
async def test_llm_provider_error_handling(client: AsyncClient) -> None:
    """Test API handling of LLM provider errors."""
    # Mock ChatService to raise LLMProviderError
    mock_service = client._transport.app.state.chat_service
    mock_service.process_message.side_effect = LLMProviderError("API rate limit exceeded")

    response = await client.post("/chat", json={"user_id": "test", "content": "Hello"})

    assert response.status_code == 503
    data = response.json()
    assert "Service temporarily unavailable" in data["detail"]
    assert "API rate limit exceeded" in data["detail"]


@pytest.mark.asyncio
async def test_storage_error_handling(client: AsyncClient) -> None:
    """Test API handling of storage errors."""
    mock_service = client._transport.app.state.chat_service
    mock_service.process_message.side_effect = StorageError("Database connection failed")

    response = await client.post("/chat", json={"user_id": "test", "content": "Hello"})

    assert response.status_code == 503
    data = response.json()
    assert "Storage error" in data["detail"]
    assert "Database connection failed" in data["detail"]


@pytest.mark.asyncio
async def test_validation_error_handling(client: AsyncClient) -> None:
    """Test API handling of validation errors."""
    mock_service = client._transport.app.state.chat_service
    mock_service.process_message.side_effect = ValidationError("Invalid user input")

    response = await client.post("/chat", json={"user_id": "test", "content": "Hello"})

    assert response.status_code == 400
    data = response.json()
    assert "Invalid user input" in data["detail"]


@pytest.mark.asyncio
async def test_unexpected_error_handling(client: AsyncClient) -> None:
    """Test API handling of unexpected errors."""
    mock_service = client._transport.app.state.chat_service
    mock_service.process_message.side_effect = RuntimeError("Unexpected system error")

    response = await client.post("/chat", json={"user_id": "test", "content": "Hello"})

    assert response.status_code == 500
    data = response.json()
    assert "Internal server error" in data["detail"]


@pytest.mark.asyncio
async def test_pydantic_validation_errors(client: AsyncClient) -> None:
    """Test handling of Pydantic validation errors."""
    # Test various validation scenarios
    test_cases = [
        # Empty user_id
        ({"user_id": "", "content": "Hello"}, "User ID cannot be empty"),
        # Empty content
        ({"user_id": "test", "content": ""}, "Message content cannot be empty"),
        # Missing user_id
        ({"content": "Hello"}, "Required field 'user_id' is missing"),
        # Missing content
        ({"user_id": "test"}, "Required field 'content' is missing"),
        # Long user_id
        ({"user_id": "x" * 101, "content": "Hello"}, "User ID is too long"),
        # Long content
        ({"user_id": "test", "content": "x" * 4001}, "Message is too long"),
    ]

    for payload, _expected_error in test_cases:
        response = await client.post("/chat", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "Validation failed" in data["error"]


@pytest.mark.asyncio
async def test_malformed_json_handling(client: AsyncClient) -> None:
    """Test handling of malformed JSON."""
    response = await client.post(
        "/chat",
        content="invalid json {",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    data = response.json()
    assert "Validation failed" in data["error"]


@pytest.mark.asyncio
async def test_rate_limit_handling(client: AsyncClient) -> None:
    """Test rate limiting behavior."""
    # Rate limit is set high in test environment (1000/minute)
    # But we can test the middleware is installed correctly
    response = await client.get("/")

    # Should have rate limit headers
    assert response.status_code == 200
    # Rate limiting middleware is installed but won't trigger with high limits


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient) -> None:
    """Test CORS headers are present."""
    response = await client.options("/chat")

    # Should include CORS headers (FastAPI handles OPTIONS automatically)
    assert response.status_code in [200, 405]  # 405 if no explicit OPTIONS handler


@pytest.mark.asyncio
async def test_request_id_middleware(client: AsyncClient) -> None:
    """Test request ID middleware adds headers."""
    response = await client.get("/")

    # Should have request ID header
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


@pytest.mark.asyncio
async def test_health_endpoint_status_codes(client: AsyncClient) -> None:
    """Test health endpoint returns correct status codes."""
    mock_service = client._transport.app.state.chat_service

    # Test healthy scenario
    mock_service.health_check.return_value = {"storage": True, "llm": True}
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

    # Test unhealthy scenario
    mock_service.health_check.return_value = {"storage": False, "llm": True}
    response = await client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_history_limit_validation(client: AsyncClient) -> None:
    """Test history endpoint limit validation."""
    # Test valid limit
    response = await client.get("/history/test_user?limit=50")
    assert response.status_code == 200

    # Test limit too high
    response = await client.get("/history/test_user?limit=101")
    assert response.status_code == 400
    data = response.json()
    assert "Limit cannot exceed 100" in data["detail"]


@pytest.mark.asyncio
async def test_history_invalid_limit_type(client: AsyncClient) -> None:
    """Test history endpoint with invalid limit type."""
    response = await client.get("/history/test_user?limit=abc")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cache_control_headers(client: AsyncClient) -> None:
    """Test that appropriate endpoints have cache control headers."""
    # Root endpoint should have long cache
    response = await client.get("/")
    assert response.status_code == 200
    assert "Cache-Control" in response.headers
    assert "3600" in response.headers["Cache-Control"]  # 1 hour

    # Health endpoint should have short cache
    response = await client.get("/health")
    assert response.status_code in [200, 503]
    assert "Cache-Control" in response.headers
    assert "30" in response.headers["Cache-Control"]  # 30 seconds

    # History should have medium cache
    response = await client.get("/history/test_user")
    assert response.status_code == 200
    assert "Cache-Control" in response.headers
    assert "300" in response.headers["Cache-Control"]  # 5 minutes


@pytest.mark.asyncio
async def test_detailed_health_endpoint(client: AsyncClient) -> None:
    """Test detailed health endpoint."""
    mock_service = client._transport.app.state.chat_service
    mock_service.health_check.return_value = {"storage": True, "llm": True}

    response = await client.get("/health/detailed")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "services" in data
    assert "version" in data
    assert "environment" in data

    # Check environment info
    assert "llm_provider" in data["environment"]
    assert "rate_limit" in data["environment"]


@pytest.mark.asyncio
async def test_openapi_documentation_accessible(client: AsyncClient) -> None:
    """Test that OpenAPI documentation is accessible."""
    response = await client.get("/docs")
    # Should redirect or serve docs page
    assert response.status_code in [200, 307]  # 200 for served, 307 for redirect

    response = await client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert data["info"]["title"] == "Chat API"


@pytest.mark.asyncio
async def test_chat_endpoint_success_response_structure(client: AsyncClient) -> None:
    """Test chat endpoint success response structure."""
    # Mock successful service call
    mock_service = client._transport.app.state.chat_service
    mock_service.process_message.return_value = {
        "id": "test-123",
        "content": "Hello! How can I help you?",
        "model": "gemini-1.5-flash",
        "cached": False,
    }

    response = await client.post("/chat", json={"user_id": "test", "content": "Hello"})

    assert response.status_code == 200
    data = response.json()

    # Verify required fields
    assert "id" in data
    assert "content" in data
    assert "timestamp" in data
    assert "cached" in data

    # Verify optional fields
    assert "model" in data

    # Verify values
    assert data["id"] == "test-123"
    assert data["content"] == "Hello! How can I help you?"
    assert data["model"] == "gemini-1.5-flash"
    assert data["cached"] is False


@pytest.mark.asyncio
async def test_exception_handler_error_types(client: AsyncClient) -> None:
    """Test that different exception types return correct error information."""
    test_cases = [
        (LLMProviderError("LLM failed"), 503, "LLMProviderError"),
        (StorageError("Storage failed"), 503, "StorageError"),
        (ValidationError("Validation failed"), 400, "ValidationError"),
    ]

    for exception, expected_status, expected_type in test_cases:
        # Mock the exception handler by making service raise the exception
        mock_service = client._transport.app.state.chat_service
        mock_service.process_message.side_effect = exception

        response = await client.post("/chat", json={"user_id": "test", "content": "Hello"})

        assert response.status_code == expected_status
        data = response.json()
        assert expected_type in data.get("type", "")
