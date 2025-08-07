"""Test HTTP handlers."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    """Test health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "services" in data


@pytest.mark.asyncio
async def test_root(client: AsyncClient) -> None:
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Chat API"
    assert data["status"] == "running"


@pytest.mark.asyncio
@patch('chat_api.handlers.process_message')
async def test_chat(mock_process: AsyncMock, client: AsyncClient, sample_message: dict[str, str]) -> None:
    """Test chat endpoint."""
    mock_process.return_value = {
        "id": "test-123",
        "content": "Hello! How can I help you?",
        "model": "test-model",
        "cached": False
    }

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
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_invalid_content(client: AsyncClient) -> None:
    """Test chat with invalid content."""
    invalid_message = {"user_id": "test", "content": ""}
    response = await client.post("/chat", json=invalid_message)
    assert response.status_code == 422


@pytest.mark.asyncio
@patch('chat_api.handlers.get_user_history')
async def test_history(mock_get_history: AsyncMock, client: AsyncClient) -> None:
    """Test history endpoint."""
    mock_get_history.return_value = [
        {
            "id": "test-123",
            "user_id": "test_user",
            "content": "Hello",
            "response": "Hi there!",
            "timestamp": "2025-01-01T00:00:00Z"
        }
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
@patch('chat_api.handlers.process_message')
async def test_chat_error_handling(mock_process: AsyncMock, client: AsyncClient, sample_message: dict[str, str]) -> None:
    """Test chat endpoint error handling."""
    mock_process.side_effect = Exception("Processing error")

    response = await client.post("/chat", json=sample_message)
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Processing error" in data["detail"]


@pytest.mark.asyncio
@patch('chat_api.handlers.process_message')
async def test_chat_cached_response(mock_process: AsyncMock, client: AsyncClient, sample_message: dict[str, str]) -> None:
    """Test chat endpoint with cached response."""
    mock_process.return_value = {
        "id": "cached-123",
        "content": "Cached response",
        "model": "test-model",
        "cached": True
    }

    response = await client.post("/chat", json=sample_message)
    assert response.status_code == 200
    data = response.json()
    assert data["cached"] is True
    assert data["content"] == "Cached response"


@pytest.mark.asyncio
@patch('chat_api.handlers.get_user_history')
async def test_history_empty(mock_get_history: AsyncMock, client: AsyncClient) -> None:
    """Test history endpoint with no history."""
    mock_get_history.return_value = []

    response = await client.get("/history/test_user")
    assert response.status_code == 200
    data = response.json()
    assert data == []


@pytest.mark.asyncio
@patch('chat_api.handlers.get_user_history')
async def test_history_with_limit(mock_get_history: AsyncMock, client: AsyncClient) -> None:
    """Test history endpoint with custom limit."""
    mock_get_history.return_value = [
        {"id": f"test-{i}", "content": f"Message {i}"} for i in range(5)
    ]

    response = await client.get("/history/test_user?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    mock_get_history.assert_called_once_with("test_user", 5)


@pytest.mark.asyncio
@patch('chat_api.handlers.get_user_history')
async def test_history_default_limit(mock_get_history: AsyncMock, client: AsyncClient) -> None:
    """Test history endpoint with default limit."""
    mock_get_history.return_value = []

    response = await client.get("/history/test_user")
    assert response.status_code == 200
    mock_get_history.assert_called_once_with("test_user", 10)


@pytest.mark.asyncio
@patch('chat_api.handlers.core_health')
async def test_health_healthy(mock_health: AsyncMock, client: AsyncClient) -> None:
    """Test health endpoint when all services are healthy."""
    mock_health.return_value = {"storage": True, "llm": True}

    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["services"]["storage"] is True
    assert data["services"]["llm"] is True
    assert "timestamp" in data


@pytest.mark.asyncio
@patch('chat_api.handlers.core_health')
async def test_health_unhealthy(mock_health: AsyncMock, client: AsyncClient) -> None:
    """Test health endpoint when services are unhealthy."""
    mock_health.return_value = {"storage": False, "llm": True}

    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["services"]["storage"] is False
    assert data["services"]["llm"] is True


@pytest.mark.asyncio
async def test_chat_malformed_json(client: AsyncClient) -> None:
    """Test chat endpoint with malformed JSON."""
    response = await client.post("/chat", content="invalid json", headers={"content-type": "application/json"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_missing_fields(client: AsyncClient) -> None:
    """Test chat endpoint with missing required fields."""
    response = await client.post("/chat", json={"user_id": "test"})  # missing content
    assert response.status_code == 422

    response = await client.post("/chat", json={"content": "hello"})  # missing user_id
    assert response.status_code == 422


@pytest.mark.asyncio
@patch('chat_api.handlers.process_message')
async def test_chat_response_structure(mock_process: AsyncMock, client: AsyncClient, sample_message: dict[str, str]) -> None:
    """Test that chat response has correct structure."""
    mock_process.return_value = {
        "id": "test-123",
        "content": "Response content",
        "model": "gpt-4",
        "cached": False
    }

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
    assert data["id"] == "test-123"
    assert data["content"] == "Response content"
    assert data["model"] == "gpt-4"
    assert data["cached"] is False


@pytest.mark.asyncio
async def test_history_invalid_limit_types(client: AsyncClient) -> None:
    """Test history endpoint with invalid limit parameter types."""
    response = await client.get("/history/test_user?limit=abc")
    assert response.status_code == 422
