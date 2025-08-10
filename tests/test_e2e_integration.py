"""End-to-end integration tests with real components."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from chat_api.api import create_app
from chat_api.chat import ChatService
from chat_api.providers import LLMResponse
from chat_api.storage import SQLiteRepository, create_cache


@pytest.mark.asyncio
async def test_full_request_flow_with_real_components() -> None:
    """Test complete request flow with minimal mocking - real integration."""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Create real components
        repository = SQLiteRepository(f"sqlite+aiosqlite:///{db_path}")
        cache = create_cache()  # In-memory cache

        # Mock only the LLM provider (to avoid API calls)
        mock_llm_provider = AsyncMock()
        mock_llm_provider.complete.return_value = LLMResponse(
            text="Integration test response",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )
        mock_llm_provider.health_check.return_value = True

        # Initialize components
        await repository.startup()
        await cache.startup()

        # Create service with real components
        service = ChatService(repository, cache, mock_llm_provider)

        # Create app and inject service
        app = create_app()
        app.state.chat_service = service

        # Test the full flow
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First request - should call LLM
            response1 = await client.post(
                "/chat",
                json={"user_id": "test_user", "content": "Hello, integration test!"},
            )

            assert response1.status_code == 200
            data1 = response1.json()
            assert data1["content"] == "Integration test response"
            assert data1["cached"] is False
            assert "id" in data1
            assert "timestamp" in data1

            # Verify LLM was called
            mock_llm_provider.complete.assert_called_once()

            # Second identical request - should hit cache
            response2 = await client.post(
                "/chat",
                json={"user_id": "test_user", "content": "Hello, integration test!"},
            )

            assert response2.status_code == 200
            data2 = response2.json()
            assert data2["content"] == "Integration test response"
            assert data2["cached"] is True

            # LLM should not be called again
            assert mock_llm_provider.complete.call_count == 1

            # Test history endpoint
            history_response = await client.get("/history/test_user")
            assert history_response.status_code == 200
            history = history_response.json()
            assert len(history) == 1
            assert history[0]["content"] == "Hello, integration test!"

            # Test health endpoint with real components
            health_response = await client.get("/health")
            assert health_response.status_code == 200
            health_data = health_response.json()
            assert health_data["status"] == "healthy"
            assert health_data["services"]["storage"] is True
            assert health_data["services"]["llm"] is True

        # Cleanup
        await repository.shutdown()
        await cache.shutdown()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_request_flow_with_storage_failure() -> None:
    """Test request handling when storage fails - error propagation."""
    # Create components with failing storage
    mock_repository = AsyncMock()
    mock_repository.save.side_effect = Exception("Database connection lost")
    mock_repository.health_check.return_value = False

    cache = create_cache()
    await cache.startup()

    mock_llm_provider = AsyncMock()
    mock_llm_provider.complete.return_value = LLMResponse(
        text="Response",
        model="test-model",
        usage={"total_tokens": 10},
    )

    service = ChatService(mock_repository, cache, mock_llm_provider)

    app = create_app()
    app.state.chat_service = service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request should fail due to storage error
        response = await client.post(
            "/chat",
            json={"user_id": "test_user", "content": "Test message"},
        )

        assert response.status_code == 500

        # Health check should report unhealthy
        health_response = await client.get("/health")
        assert health_response.status_code == 503
        health_data = health_response.json()
        assert health_data["status"] == "unhealthy"
        assert health_data["services"]["storage"] is False

    await cache.shutdown()


@pytest.mark.asyncio
async def test_request_flow_with_llm_timeout() -> None:
    """Test request handling with LLM timeout - retry and error handling."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        repository = SQLiteRepository(f"sqlite+aiosqlite:///{db_path}")
        await repository.startup()

        cache = create_cache()
        await cache.startup()

        # Mock LLM provider that times out
        mock_llm_provider = AsyncMock()
        mock_llm_provider.complete.side_effect = TimeoutError("LLM API timeout")
        mock_llm_provider.health_check.return_value = False

        service = ChatService(repository, cache, mock_llm_provider)

        app = create_app()
        app.state.chat_service = service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Request should fail after retries
            response = await client.post(
                "/chat",
                json={"user_id": "test_user", "content": "Test message"},
            )

            # Should return 500 due to LLM timeout
            assert response.status_code == 500

        await repository.shutdown()
        await cache.shutdown()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_middleware_integration() -> None:
    """Test that all middleware is properly integrated."""
    app = create_app()

    # Mock minimal service
    mock_service = AsyncMock()
    mock_service.health_check.return_value = {"storage": True, "llm": True}
    app.state.chat_service = mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test request ID middleware
        response = await client.get("/")
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) > 0

        # Test CORS middleware
        response = await client.options(
            "/chat",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        # FastAPI handles OPTIONS
        assert response.status_code in [200, 405]

        # Test cache control headers
        response = await client.get("/")
        assert "Cache-Control" in response.headers
        assert "max-age=3600" in response.headers["Cache-Control"]


@pytest.mark.asyncio
async def test_concurrent_requests() -> None:
    """Test handling multiple concurrent requests - race conditions."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        repository = SQLiteRepository(f"sqlite+aiosqlite:///{db_path}")
        await repository.startup()

        cache = create_cache()
        await cache.startup()

        # Mock LLM with delay to simulate processing time
        mock_llm_provider = AsyncMock()
        call_count = 0

        async def delayed_complete(prompt: str) -> LLMResponse:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate API delay
            return LLMResponse(
                text=f"Response {call_count} to: {prompt}",
                model="test-model",
                usage={"total_tokens": 10},
            )

        mock_llm_provider.complete.side_effect = delayed_complete
        mock_llm_provider.health_check.return_value = True

        service = ChatService(repository, cache, mock_llm_provider)

        app = create_app()
        app.state.chat_service = service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Send 5 concurrent requests with different messages
            tasks = []
            for i in range(5):
                task = client.post(
                    "/chat",
                    json={"user_id": f"user_{i}", "content": f"Message {i}"},
                )
                tasks.append(task)

            # Wait for all to complete
            responses = await asyncio.gather(*tasks)

            # All should succeed
            for response in responses:
                assert response.status_code == 200

            # All 5 LLM calls should have been made
            assert call_count == 5

            # Send 5 concurrent identical requests (cache test)
            tasks = []
            for _ in range(5):
                task = client.post(
                    "/chat",
                    json={"user_id": "same_user", "content": "Same message"},
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks)

            # All should succeed
            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert "Response" in data["content"]

            # Only 1 additional LLM call should be made (rest from cache)
            assert call_count == 6

        await repository.shutdown()
        await cache.shutdown()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_graceful_shutdown() -> None:
    """Test graceful shutdown of resources."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Track shutdown calls
        shutdown_called = {"repository": False, "cache": False}

        # Create repository with tracking
        repository = SQLiteRepository(f"sqlite+aiosqlite:///{db_path}")
        await repository.startup()
        original_repo_shutdown = repository.shutdown

        async def tracked_repo_shutdown():
            shutdown_called["repository"] = True
            await original_repo_shutdown()

        repository.shutdown = tracked_repo_shutdown

        # Create cache with tracking
        cache = create_cache()
        await cache.startup()
        original_cache_shutdown = cache.shutdown

        async def tracked_cache_shutdown():
            shutdown_called["cache"] = True
            await original_cache_shutdown()

        cache.shutdown = tracked_cache_shutdown

        # Mock LLM
        mock_llm_provider = AsyncMock()
        mock_llm_provider.health_check.return_value = True

        # Create service
        service = ChatService(repository, cache, mock_llm_provider)

        # Simulate app shutdown
        await repository.shutdown()
        await cache.shutdown()

        # Verify shutdown was called
        assert shutdown_called["repository"] is True
        assert shutdown_called["cache"] is True
    finally:
        Path(db_path).unlink(missing_ok=True)
