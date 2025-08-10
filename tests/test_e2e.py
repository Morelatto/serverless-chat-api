"""End-to-end integration tests focusing on complete workflows."""

import pytest
from httpx import AsyncClient

from chat_api.providers import LLMResponse


@pytest.mark.asyncio
async def test_e2e_chat_flow(client: AsyncClient) -> None:
    """Test complete chat flow end-to-end."""
    # Mock LLM provider response
    client._transport.app.state.llm_provider.complete.return_value = LLMResponse(
        text="Hello! I'm an AI assistant. How can I help you today?",
        model="gpt-4",
        usage={"prompt_tokens": 5, "completion_tokens": 15, "total_tokens": 20},
    )

    # Mock cache miss
    client._transport.app.state.cache.get.return_value = None

    # Send chat message
    response = await client.post(
        "/chat",
        json={"user_id": "test-user-123", "content": "Hello, how are you?"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "id" in data
    assert data["content"] == "Hello! I'm an AI assistant. How can I help you today?"
    assert data["model"] == "gpt-4"
    assert data["cached"] is False
    assert "timestamp" in data

    # Mock history for the history endpoint
    client._transport.app.state.repository.get_history.return_value = [
        {
            "id": data["id"],
            "user_id": "test-user-123",
            "content": "Hello, how are you?",
            "response": "Hello! I'm an AI assistant. How can I help you today?",
            "timestamp": data["timestamp"],
        },
    ]

    # Check history endpoint
    history_response = await client.get("/history/test-user-123")
    assert history_response.status_code == 200
    history_data = history_response.json()

    # History should contain our message
    assert len(history_data) == 1
    assert history_data[0]["content"] == "Hello, how are you?"


@pytest.mark.asyncio
async def test_e2e_validation_errors(client: AsyncClient) -> None:
    """Test API validation errors."""
    # Invalid message format
    response = await client.post(
        "/chat",
        json={
            "user_id": "",  # Empty user_id should fail
            "content": "Hello",
        },
    )
    assert response.status_code == 400

    # Missing fields
    response = await client.post(
        "/chat",
        json={
            "user_id": "test",
            # Missing content
        },
    )
    assert response.status_code == 400

    # History limit too high
    response = await client.get("/history/test?limit=200")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_e2e_complete_workflow(client: AsyncClient) -> None:
    """Test complete application workflow including chat and history."""
    # Setup mocks
    client._transport.app.state.llm_provider.complete.return_value = LLMResponse(
        text="AI response to user query",
        model="gpt-4",
        usage={"total_tokens": 25},
    )
    client._transport.app.state.llm_provider.health_check.return_value = True

    # Mock cache miss initially
    client._transport.app.state.cache.get.return_value = None

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
    client._transport.app.state.repository.get_history.return_value = [
        {
            "id": chat_data["id"],
            "user_id": "integration-test-user",
            "content": "What is the capital of France?",
            "response": "AI response to user query",
            "timestamp": chat_data["timestamp"],
        },
    ]

    response = await client.get("/history/integration-test-user")
    assert response.status_code == 200
    history_data = response.json()
    assert len(history_data) == 1
    assert history_data[0]["content"] == "What is the capital of France?"

    # Step 4: Test caching (second identical request)
    # Mock cache hit
    client._transport.app.state.cache.get.return_value = {
        "id": "cached-id",
        "content": "AI response to user query",
        "model": "gpt-4",
        "cached": False,
    }

    response = await client.post("/chat", json=chat_request)
    assert response.status_code == 200
    cached_data = response.json()
    assert cached_data["cached"] is True

    # Step 5: API info
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "Chat API"


@pytest.mark.asyncio
async def test_e2e_error_recovery(client: AsyncClient) -> None:
    """Test error handling and recovery."""
    # Simulate LLM failure
    client._transport.app.state.llm_provider.complete.side_effect = Exception(
        "LLM service unavailable"
    )

    response = await client.post("/chat", json={"user_id": "test-user", "content": "Test message"})
    assert response.status_code == 500
    assert "LLM service unavailable" in response.json()["detail"]

    # Simulate recovery
    client._transport.app.state.llm_provider.complete.side_effect = None
    client._transport.app.state.llm_provider.complete.return_value = LLMResponse(
        text="Service recovered",
        model="gpt-4",
        usage={},
    )

    response = await client.post(
        "/chat",
        json={"user_id": "test-user", "content": "Test message after recovery"},
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Service recovered"
