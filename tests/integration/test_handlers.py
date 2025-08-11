"""Test HTTP endpoints - core functionality only."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient) -> None:
    """Test root endpoint returns basic info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Chat API"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    """Test health endpoint."""
    response = await client.get("/health")
    assert response.status_code in [200, 503]  # Either healthy or unhealthy is valid
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_chat_validation(client: AsyncClient) -> None:
    """Test chat endpoint validates input."""
    # Empty user_id should fail
    response = await client.post("/chat", json={"user_id": "", "content": "Hello"})
    assert response.status_code == 400

    # Empty content should fail
    response = await client.post("/chat", json={"user_id": "test", "content": ""})
    assert response.status_code == 400

    # Missing fields should fail
    response = await client.post("/chat", json={"user_id": "test"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_history_endpoint(client: AsyncClient) -> None:
    """Test history endpoint."""
    response = await client.get("/history/test_user")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Test limit validation
    response = await client.get("/history/test_user?limit=101")
    assert response.status_code == 400
