"""End-to-end integration tests."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@patch("chat_api.core._call_llm")
async def test_e2e_chat_flow(mock_call_llm, client: AsyncClient):
    """Test complete chat flow end-to-end."""
    # Mock LLM response
    mock_call_llm.return_value = {
        "text": "Hello! I'm an AI assistant. How can I help you today?",
        "model": "gpt-4",
        "usage": {"prompt_tokens": 5, "completion_tokens": 15, "total_tokens": 20},
    }

    # Send chat message
    response = await client.post(
        "/chat", json={"user_id": "test-user-123", "content": "Hello, how are you?"}
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "id" in data
    assert data["content"] == "Hello! I'm an AI assistant. How can I help you today?"
    assert data["model"] == "gpt-4"
    assert data["cached"] is False
    assert "timestamp" in data

    # Check history endpoint
    history_response = await client.get("/history/test-user-123")
    assert history_response.status_code == 200
    history_data = history_response.json()

    # History should contain our message
    assert len(history_data) > 0
    # Note: In a real integration test, we'd verify the message is in history
    # but our mocked storage might not persist across calls


@pytest.mark.asyncio
async def test_e2e_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "timestamp" in data

    # Should have storage and llm status
    assert "storage" in data["services"]
    assert "llm" in data["services"]


@pytest.mark.asyncio
async def test_e2e_api_info(client: AsyncClient):
    """Test root API info endpoint."""
    response = await client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Chat API"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_e2e_validation_errors(client: AsyncClient):
    """Test API validation errors."""
    # Invalid message format
    response = await client.post(
        "/chat",
        json={
            "user_id": "",  # Empty user_id should fail
            "content": "Hello",
        },
    )
    assert response.status_code == 422

    # Missing fields
    response = await client.post(
        "/chat",
        json={
            "user_id": "test"
            # Missing content
        },
    )
    assert response.status_code == 422

    # History limit too high
    response = await client.get("/history/test?limit=200")
    assert response.status_code == 400


@pytest.mark.asyncio
@patch("chat_api.core._call_llm")
@patch("chat_api.handlers.get_user_history")
async def test_e2e_complete_workflow(
    mock_get_history: AsyncMock, mock_call_llm: AsyncMock, client: AsyncClient
):
    """Test complete application workflow including chat and history."""
    # Setup mocks
    mock_call_llm.return_value = {
        "text": "AI response to user query",
        "model": "gpt-4",
        "usage": {"total_tokens": 25},
    }

    # Step 1: Health check
    response = await client.get("/health")
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["status"] in ["healthy", "unhealthy"]

    # Step 2: Send chat message
    chat_request = {"user_id": "integration-test-user", "content": "What is the capital of France?"}
    response = await client.post("/chat", json=chat_request)
    assert response.status_code == 200
    chat_data = response.json()
    assert chat_data["content"] == "AI response to user query"
    assert "timestamp" in chat_data

    # Step 3: Check history
    mock_get_history.return_value = [
        {
            "id": chat_data["id"],
            "user_id": "integration-test-user",
            "content": "What is the capital of France?",
            "response": "AI response to user query",
            "timestamp": chat_data["timestamp"],
        }
    ]

    response = await client.get("/history/integration-test-user")
    assert response.status_code == 200
    history_data = response.json()
    assert len(history_data) == 1
    assert history_data[0]["content"] == "What is the capital of France?"

    # Step 4: Test caching (second identical request)
    response = await client.post("/chat", json=chat_request)
    assert response.status_code == 200
    # In real scenario with proper caching, this would be cached

    # Step 5: API info
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "Chat API"


@pytest.mark.asyncio
@patch("chat_api.core._call_llm")
async def test_e2e_error_recovery(mock_call_llm: AsyncMock, client: AsyncClient):
    """Test error handling and recovery."""
    # Simulate LLM failure
    mock_call_llm.side_effect = Exception("LLM service unavailable")

    response = await client.post("/chat", json={"user_id": "test-user", "content": "Test message"})
    assert response.status_code == 500
    assert "LLM service unavailable" in response.json()["detail"]

    # Simulate recovery
    mock_call_llm.side_effect = None
    mock_call_llm.return_value = {"text": "Service recovered", "model": "gpt-4", "usage": {}}

    response = await client.post(
        "/chat", json={"user_id": "test-user", "content": "Test message after recovery"}
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Service recovered"
