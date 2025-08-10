"""Test HTTP handlers."""

import pytest
from httpx import AsyncClient

from chat_api.exceptions import LLMProviderError
from chat_api.providers import LLMResponse


@pytest.mark.asyncio
async def test_root(client: AsyncClient) -> None:
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Chat API"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_chat(client: AsyncClient, sample_message: dict[str, str]) -> None:
    """Test chat endpoint."""
    # Mock cache miss and successful LLM call
    client._transport.app.state.cache.get.return_value = None
    client._transport.app.state.llm_provider.complete.return_value = LLMResponse(
        text="Hello! How can I help you?",
        model="test-model",
        usage={"total_tokens": 10},
    )

    response = await client.post("/chat", json=sample_message)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "content" in data
    assert data["cached"] is False


@pytest.mark.asyncio
async def test_chat_invalid_user_id(client: AsyncClient) -> None:
    """Test chat with invalid user_id."""
    invalid_message = {"user_id": "", "content": "Hello"}
    response = await client.post("/chat", json=invalid_message)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chat_invalid_content(client: AsyncClient) -> None:
    """Test chat with invalid content."""
    invalid_message = {"user_id": "test", "content": ""}
    response = await client.post("/chat", json=invalid_message)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_history(client: AsyncClient) -> None:
    """Test history endpoint."""
    client._transport.app.state.repository.get_history.return_value = [
        {
            "id": "test-123",
            "user_id": "test_user",
            "content": "Hello",
            "response": "Hi there!",
            "timestamp": "2025-01-01T00:00:00Z",
        },
    ]

    response = await client.get("/history/test_user")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["user_id"] == "test_user"


@pytest.mark.asyncio
async def test_history_limit_exceeded(client: AsyncClient) -> None:
    """Test history with excessive limit."""
    response = await client.get("/history/test_user?limit=101")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chat_error_handling(client: AsyncClient, sample_message: dict[str, str]) -> None:
    """Test chat endpoint error handling."""
    # Mock LLM to raise an error
    client._transport.app.state.llm_provider.complete.side_effect = LLMProviderError(
        "LLM service error"
    )
    client._transport.app.state.cache.get.return_value = None

    response = await client.post("/chat", json=sample_message)
    assert response.status_code == 503  # Service unavailable for LLM errors
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_chat_cached_response(client: AsyncClient, sample_message: dict[str, str]) -> None:
    """Test chat endpoint with cached response."""
    # Mock cache to return cached response
    client._transport.app.state.cache.get.return_value = {
        "id": "cached-123",
        "content": "Cached response",
        "model": "test-model",
        "cached": False,
    }

    response = await client.post("/chat", json=sample_message)
    assert response.status_code == 200
    data = response.json()
    assert data["cached"] is True
    assert data["content"] == "Cached response"
    # LLM should not be called when cached
    client._transport.app.state.llm_provider.complete.assert_not_called()


@pytest.mark.asyncio
async def test_history_empty(client: AsyncClient) -> None:
    """Test history endpoint with no history."""
    client._transport.app.state.repository.get_history.return_value = []

    response = await client.get("/history/test_user")
    assert response.status_code == 200
    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_history_with_limit(client: AsyncClient) -> None:
    """Test history endpoint with custom limit."""
    client._transport.app.state.repository.get_history.return_value = [
        {"id": f"test-{i}", "content": f"Message {i}"} for i in range(5)
    ]

    response = await client.get("/history/test_user?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    client._transport.app.state.repository.get_history.assert_called_with("test_user", 5)


@pytest.mark.asyncio
async def test_history_default_limit(client: AsyncClient) -> None:
    """Test history endpoint with default limit."""
    client._transport.app.state.repository.get_history.return_value = []

    response = await client.get("/history/test_user")
    assert response.status_code == 200
    client._transport.app.state.repository.get_history.assert_called_with("test_user", 10)


@pytest.mark.asyncio
async def test_health_healthy(client: AsyncClient) -> None:
    """Test health endpoint when all services are healthy."""
    client._transport.app.state.repository.health_check.return_value = True
    client._transport.app.state.llm_provider.health_check.return_value = True

    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["services"]["storage"] is True
    assert data["services"]["llm"] is True
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_unhealthy(client: AsyncClient) -> None:
    """Test health endpoint when services are unhealthy."""
    client._transport.app.state.repository.health_check.return_value = False
    client._transport.app.state.llm_provider.health_check.return_value = True

    response = await client.get("/health")
    assert response.status_code == 503  # Unhealthy service returns 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["services"]["storage"] is False
    assert data["services"]["llm"] is True


@pytest.mark.asyncio
async def test_health_detailed(client: AsyncClient) -> None:
    """Test detailed health endpoint."""
    client._transport.app.state.repository.health_check.return_value = True
    client._transport.app.state.llm_provider.health_check.return_value = True

    response = await client.get("/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "version" in data
    assert "environment" in data
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_chat_malformed_json(client: AsyncClient) -> None:
    """Test chat endpoint with malformed JSON."""
    response = await client.post(
        "/chat",
        content="invalid json",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chat_missing_fields(client: AsyncClient) -> None:
    """Test chat endpoint with missing required fields."""
    response = await client.post("/chat", json={"user_id": "test"})  # missing content
    assert response.status_code == 400

    response = await client.post("/chat", json={"content": "hello"})  # missing user_id
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chat_response_structure(client: AsyncClient, sample_message: dict[str, str]) -> None:
    """Test that chat response has correct structure."""
    # Mock successful LLM call
    client._transport.app.state.cache.get.return_value = None
    client._transport.app.state.llm_provider.complete.return_value = LLMResponse(
        text="Response content",
        model="gpt-4",
        usage={"total_tokens": 10},
    )

    response = await client.post("/chat", json=sample_message)
    assert response.status_code == 200
    data = response.json()

    # Check required fields
    assert "id" in data
    assert "content" in data
    assert "timestamp" in data
    assert "cached" in data

    # Check optional fields
    assert "model" in data

    # Validate values
    assert data["content"] == "Response content"
    assert data["model"] == "gpt-4"
    assert data["cached"] is False


@pytest.mark.asyncio
async def test_history_invalid_limit_types(client: AsyncClient) -> None:
    """Test history endpoint with invalid limit parameter types."""
    response = await client.get("/history/test_user?limit=abc")
    assert response.status_code in [400, 422]  # Can return 400 or 422 for validation errors
