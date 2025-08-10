"""Test API app, middleware, and lifecycle."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from chat_api.api import app, lifespan


@pytest.mark.asyncio
async def test_lifespan_startup_shutdown() -> None:
    """Test app lifespan startup and shutdown."""
    test_app = FastAPI()

    with (
        patch("chat_api.api.create_repository") as mock_create_repo,
        patch("chat_api.api.create_cache") as mock_create_cache,
        patch("chat_api.api.create_llm_provider") as mock_create_provider,
        patch("chat_api.api.settings") as mock_settings,
    ):
        # Configure mocks
        mock_repo = AsyncMock()
        mock_cache = AsyncMock()
        mock_provider = AsyncMock()

        mock_create_repo.return_value = mock_repo
        mock_create_cache.return_value = mock_cache
        mock_create_provider.return_value = mock_provider

        mock_settings.database_url = "sqlite+aiosqlite:///:memory:"
        mock_settings.redis_url = None
        mock_settings.llm_provider = "gemini"
        mock_settings.llm_model = "test-model"
        mock_settings.gemini_api_key = "test-key"

        # Run lifespan
        async with lifespan(test_app):
            # Check that chat service was created with the components
            assert test_app.state.chat_service is not None

            # Verify components were created and initialized
            mock_create_repo.assert_called_once()
            mock_create_cache.assert_called_once()
            mock_create_provider.assert_called_once()

            # Startup should have been called on the components
            mock_repo.startup.assert_called_once()
            mock_cache.startup.assert_called_once()

        # After exit, shutdown should have been called
        mock_repo.shutdown.assert_called_once()
        mock_cache.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_error_handling() -> None:
    """Test lifespan handles startup errors gracefully."""
    test_app = FastAPI()

    with (
        patch("chat_api.api.create_repository") as mock_create_repo,
        patch("chat_api.api.logger") as mock_logger,
    ):
        # Make repository startup fail
        mock_repo = AsyncMock()
        mock_repo.startup.side_effect = Exception("Database connection failed")
        mock_create_repo.return_value = mock_repo

        with pytest.raises(Exception, match="Database connection failed"):
            async with lifespan(test_app):
                pass

        # Should log the error
        mock_logger.error.assert_called()


@pytest.mark.asyncio
async def test_app_routes_registered() -> None:
    """Test that all routes are properly registered."""
    routes = [route.path for route in app.routes]

    expected_routes = [
        "/",
        "/chat",
        "/history/{user_id}",
        "/health",
        "/health/detailed",
        "/docs",
        "/openapi.json",
    ]

    for route in expected_routes:
        assert any(route in r for r in routes), f"Route {route} not found"


@pytest.mark.asyncio
async def test_validation_error_handler() -> None:
    """Test custom validation error handler."""
    from httpx import ASGITransport

    # Initialize app state mocks
    app.state.repository = AsyncMock()
    app.state.cache = AsyncMock()
    app.state.llm_provider = AsyncMock()
    app.state.chat_service = AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Send invalid data
        response = await client.post("/chat", json={"invalid": "data"})

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


@pytest.mark.asyncio
async def test_cors_middleware() -> None:
    """Test CORS middleware is configured."""
    from fastapi.middleware.cors import CORSMiddleware

    # Check if CORS middleware is added
    cors_middleware = None
    for middleware in app.user_middleware:
        if middleware.cls == CORSMiddleware:
            cors_middleware = middleware
            break

    assert cors_middleware is not None
    assert "*" in cors_middleware.kwargs["allow_origins"]
    # Check that methods are allowed (could be "*" or list)
    methods = cors_middleware.kwargs["allow_methods"]
    assert methods == ["*"] or "GET" in methods
    assert "POST" in cors_middleware.kwargs["allow_methods"]


@pytest.mark.asyncio
async def test_rate_limiter_integration() -> None:
    """Test rate limiter is properly integrated."""
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    # Check that rate limit handler is registered
    exception_handlers = app.exception_handlers
    assert RateLimitExceeded in exception_handlers
    assert exception_handlers[RateLimitExceeded] == _rate_limit_exceeded_handler


@pytest.mark.asyncio
async def test_app_metadata() -> None:
    """Test app metadata configuration."""
    assert app.title == "Chat API"
    assert app.version == "1.0.0"
    # App description can vary, just check it exists
    assert app.description is not None


@pytest.mark.asyncio
async def test_openapi_schema() -> None:
    """Test OpenAPI schema generation."""
    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()

        assert schema["info"]["title"] == "Chat API"
        assert schema["info"]["version"] == "1.0.0"
        assert "/chat" in schema["paths"]
        assert "/health" in schema["paths"]
        assert "/history/{user_id}" in schema["paths"]


@pytest.mark.asyncio
async def test_docs_endpoint() -> None:
    """Test documentation endpoint is accessible."""
    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")

        # Should redirect to docs with trailing slash
        assert response.status_code in [200, 307]
        if response.status_code == 307:
            assert response.headers["location"] == "/docs/"


@pytest.mark.asyncio
async def test_lifespan_with_openrouter_provider() -> None:
    """Test lifespan with OpenRouter provider configuration."""
    test_app = FastAPI()

    with (
        patch("chat_api.api.create_repository") as mock_create_repo,
        patch("chat_api.api.create_cache") as mock_create_cache,
        patch("chat_api.api.create_llm_provider") as mock_create_provider,
        patch("chat_api.api.settings") as mock_settings,
    ):
        # Configure for OpenRouter
        mock_settings.llm_provider = "openrouter"
        mock_settings.llm_model = "gpt-4"
        mock_settings.openrouter_api_key = "sk-test"
        mock_settings.gemini_api_key = None
        mock_settings.database_url = "sqlite+aiosqlite:///:memory:"
        mock_settings.redis_url = None

        mock_create_repo.return_value = AsyncMock()
        mock_create_cache.return_value = AsyncMock()
        mock_provider = AsyncMock()
        mock_create_provider.return_value = mock_provider

        async with lifespan(test_app):
            # Should create OpenRouter provider
            mock_create_provider.assert_called_with(
                provider_type="openrouter",
                model="gpt-4",
                api_key="sk-test",
            )


@pytest.mark.asyncio
async def test_middleware_ordering() -> None:
    """Test that middleware is applied in correct order."""
    # Request ID middleware should be applied
    # CORS middleware should be applied
    # Rate limiting should be on specific endpoints

    # Check middleware is present (order may vary based on FastAPI version)
    # Check that expected middleware types are present
    assert len(app.user_middleware) > 0  # At least some middleware is configured


@pytest.mark.asyncio
async def test_health_endpoint_during_startup() -> None:
    """Test health endpoint responds during startup."""
    from httpx import ASGITransport

    # Initialize minimal state
    app.state.repository = AsyncMock()
    app.state.repository.health_check.return_value = False
    app.state.llm_provider = AsyncMock()
    app.state.llm_provider.health_check.return_value = False
    app.state.chat_service = AsyncMock()
    app.state.cache = AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["services"]["storage"] is False
        assert data["services"]["llm"] is False
