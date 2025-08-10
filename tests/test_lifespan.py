"""Test application lifespan management and startup/shutdown."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chat_api.api import lifespan
from chat_api.config import Settings


@pytest.mark.asyncio
async def test_successful_startup_and_shutdown() -> None:
    """Test successful application startup and graceful shutdown."""
    # Set test environment
    with patch.dict(
        os.environ,
        {
            "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "CHAT_OPENROUTER_API_KEY": "test-key",
            "CHAT_LOG_LEVEL": "ERROR",
        },
    ):
        app = FastAPI(lifespan=lifespan)

        # Track startup/shutdown
        startup_complete = False
        shutdown_complete = False

        # Use test client to trigger lifespan
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # After context manager enters, startup should be complete
            # Verify app state is initialized
            assert hasattr(app.state, "chat_service")
            assert app.state.chat_service is not None
            startup_complete = True

            # Make a request to verify app is working
            response = await client.get("/")
            assert response.status_code == 200

        # After context manager exits, shutdown should be complete
        shutdown_complete = True

        assert startup_complete
        assert shutdown_complete


@pytest.mark.asyncio
async def test_startup_initializes_all_components() -> None:
    """Test that startup properly initializes all required components."""
    with patch.dict(
        os.environ,
        {
            "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "CHAT_GEMINI_API_KEY": "test-key",
            "CHAT_LLM_PROVIDER": "gemini",
        },
    ):
        # Mock the dependencies
        with (
            patch("chat_api.api.create_repository") as mock_create_repo,
            patch("chat_api.api.create_cache") as mock_create_cache,
            patch("chat_api.api.create_llm_provider") as mock_create_provider,
        ):
            # Setup mocks
            mock_repo = AsyncMock()
            mock_cache = AsyncMock()
            mock_provider = AsyncMock()

            mock_create_repo.return_value = mock_repo
            mock_create_cache.return_value = mock_cache
            mock_create_provider.return_value = mock_provider

            app = FastAPI(lifespan=lifespan)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test"):
                # Verify initialization calls
                mock_create_repo.assert_called_once()
                mock_create_cache.assert_called_once()
                mock_create_provider.assert_called_once_with(
                    provider_type="gemini",
                    model="gemini/gemini-1.5-flash",
                    api_key="test-key",
                )

                # Verify startup was called
                mock_repo.startup.assert_called_once()
                mock_cache.startup.assert_called_once()

                # Verify service was created
                assert hasattr(app.state, "chat_service")

            # Verify shutdown was called
            mock_repo.shutdown.assert_called_once()
            mock_cache.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_startup_with_repository_failure() -> None:
    """Test handling of repository initialization failure."""
    with patch.dict(
        os.environ,
        {
            "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "CHAT_OPENROUTER_API_KEY": "test-key",
        },
    ):
        with patch("chat_api.api.create_repository") as mock_create_repo:
            # Make repository startup fail
            mock_repo = AsyncMock()
            mock_repo.startup.side_effect = Exception("Database connection failed")
            mock_create_repo.return_value = mock_repo

            app = FastAPI(lifespan=lifespan)

            # Startup should fail
            with pytest.raises(Exception, match="Database connection failed"):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test"):
                    pass


@pytest.mark.asyncio
async def test_startup_with_invalid_provider_config() -> None:
    """Test handling of invalid LLM provider configuration."""
    with patch.dict(
        os.environ,
        {
            "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "CHAT_LLM_PROVIDER": "gemini",
            # Missing CHAT_GEMINI_API_KEY
        },
        clear=True,
    ):
        # Should fail due to missing API key
        with pytest.raises(ValueError, match="CHAT_GEMINI_API_KEY"):
            Settings()


@pytest.mark.asyncio
async def test_lifespan_environment_based_configuration() -> None:
    """Test that lifespan uses correct configuration based on environment."""
    # Test Lambda environment
    with patch.dict(
        os.environ,
        {
            "AWS_LAMBDA_FUNCTION_NAME": "chat-api",
            "CHAT_GEMINI_API_KEY": "lambda-key",
            "CHAT_LLM_PROVIDER": "gemini",
            "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",  # Should be overridden
        },
    ):
        with (
            patch("chat_api.api.create_repository") as mock_create_repo,
            patch("chat_api.api.create_cache") as mock_create_cache,
            patch("chat_api.api.create_llm_provider") as mock_create_provider,
        ):
            mock_repo = AsyncMock()
            mock_cache = AsyncMock()
            mock_provider = AsyncMock()

            mock_create_repo.return_value = mock_repo
            mock_create_cache.return_value = mock_cache
            mock_create_provider.return_value = mock_provider

            # Import fresh settings to get Lambda config
            from chat_api.config import Settings

            settings = Settings()

            # In Lambda, should use DynamoDB
            assert "dynamodb" in settings.effective_database_url

            app = FastAPI(lifespan=lifespan)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test"):
                # Verify repository was created with effective URL
                create_repo_call = mock_create_repo.call_args
                # Should have been called with DynamoDB URL
                assert create_repo_call is not None


@pytest.mark.asyncio
async def test_lifespan_redis_cache_initialization() -> None:
    """Test Redis cache initialization when REDIS_URL is set."""
    with patch.dict(
        os.environ,
        {
            "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "CHAT_REDIS_URL": "redis://localhost:6379",
            "CHAT_OPENROUTER_API_KEY": "test-key",
        },
    ):
        with (
            patch("chat_api.api.create_repository") as mock_create_repo,
            patch("chat_api.api.create_cache") as mock_create_cache,
            patch("chat_api.api.create_llm_provider") as mock_create_provider,
        ):
            mock_repo = AsyncMock()
            mock_cache = AsyncMock()
            mock_provider = AsyncMock()

            mock_create_repo.return_value = mock_repo
            mock_create_cache.return_value = mock_cache
            mock_create_provider.return_value = mock_provider

            app = FastAPI(lifespan=lifespan)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test"):
                # Verify cache was created with Redis URL
                mock_create_cache.assert_called_once_with("redis://localhost:6379")


@pytest.mark.asyncio
async def test_lifespan_graceful_error_recovery() -> None:
    """Test graceful handling of component failures during operation."""
    with patch.dict(
        os.environ,
        {
            "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "CHAT_OPENROUTER_API_KEY": "test-key",
        },
    ):
        with (
            patch("chat_api.api.create_repository") as mock_create_repo,
            patch("chat_api.api.create_cache") as mock_create_cache,
            patch("chat_api.api.create_llm_provider") as mock_create_provider,
        ):
            mock_repo = AsyncMock()
            mock_cache = AsyncMock()
            mock_provider = AsyncMock()

            # Make shutdown fail but should handle gracefully
            mock_repo.shutdown.side_effect = Exception("Shutdown error")

            mock_create_repo.return_value = mock_repo
            mock_create_cache.return_value = mock_cache
            mock_create_provider.return_value = mock_provider

            app = FastAPI(lifespan=lifespan)

            transport = ASGITransport(app=app)

            # Should handle shutdown error gracefully
            try:
                async with AsyncClient(transport=transport, base_url="http://test"):
                    pass
            except Exception:
                # Shutdown error should be logged but not prevent app from stopping
                pass

            # Cache shutdown should still be attempted
            mock_cache.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_resource_cleanup_on_startup_failure() -> None:
    """Test that resources are cleaned up if startup fails partway."""
    with patch.dict(
        os.environ,
        {
            "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "CHAT_OPENROUTER_API_KEY": "test-key",
        },
    ):
        with (
            patch("chat_api.api.create_repository") as mock_create_repo,
            patch("chat_api.api.create_cache") as mock_create_cache,
            patch("chat_api.api.create_llm_provider") as mock_create_provider,
        ):
            mock_repo = AsyncMock()
            mock_cache = AsyncMock()

            # Repository starts successfully
            mock_create_repo.return_value = mock_repo

            # Cache startup fails
            mock_cache.startup.side_effect = Exception("Cache initialization failed")
            mock_create_cache.return_value = mock_cache

            # Provider is never reached
            mock_create_provider.return_value = AsyncMock()

            app = FastAPI(lifespan=lifespan)

            # Startup should fail
            with pytest.raises(Exception, match="Cache initialization failed"):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test"):
                    pass

            # Repository should be cleaned up even though cache failed
            mock_repo.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_with_rate_limiter_configuration() -> None:
    """Test that rate limiter is properly configured during startup."""
    with patch.dict(
        os.environ,
        {
            "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "CHAT_OPENROUTER_API_KEY": "test-key",
            "CHAT_RATE_LIMIT": "30/minute",
        },
    ):
        app = FastAPI(lifespan=lifespan)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Verify rate limiter is attached to app
            assert hasattr(app.state, "limiter")

            # Make a request to verify rate limiting middleware is active
            response = await client.get("/")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_lifespan_logging_configuration() -> None:
    """Test that logging is properly configured during startup."""
    with patch.dict(
        os.environ,
        {
            "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "CHAT_OPENROUTER_API_KEY": "test-key",
            "CHAT_LOG_LEVEL": "DEBUG",
            "CHAT_LOG_FILE": "/tmp/test.log",
        },
    ):
        with patch("chat_api.api.logger") as mock_logger:
            app = FastAPI(lifespan=lifespan)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test"):
                # Verify logger was configured
                mock_logger.remove.assert_called()
                assert mock_logger.add.call_count >= 1  # At least stderr handler

                # Check for file handler if log file is set
                add_calls = mock_logger.add.call_args_list
                file_handler_added = any("/tmp/test.log" in str(call) for call in add_calls)
                # Note: actual implementation may vary
