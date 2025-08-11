"""Test service factory functionality."""

import os
from unittest.mock import AsyncMock, patch

import pytest

from chat_api.factory import Environment, ServiceFactory, create_service, detect_environment


class TestEnvironmentDetection:
    """Test environment detection logic."""

    def test_detect_development_environment(self) -> None:
        """Test detection of development environment."""
        with patch.dict(
            os.environ,
            {
                "CHAT_DATABASE_URL": "sqlite+aiosqlite:///./data/chat.db",
                "AWS_LAMBDA_FUNCTION_NAME": "",  # Not in Lambda
            },
            clear=True,
        ):
            # Force new settings instance in patched environment
            from chat_api.config import Settings

            # Create new settings with current env vars
            test_settings = Settings()

            # Mock the module-level settings
            with patch("chat_api.factory.settings", test_settings):
                env = detect_environment()
                assert env == Environment.DEVELOPMENT

    def test_detect_lambda_environment(self) -> None:
        """Test detection of Lambda environment."""
        with patch.dict(
            os.environ,
            {
                "AWS_LAMBDA_FUNCTION_NAME": "test-function",
                "CHAT_DATABASE_URL": "sqlite+aiosqlite:///./data/chat.db",
            },
            clear=True,
        ):
            # Force new settings instance in patched environment
            from chat_api.config import Settings

            # Create new settings with current env vars
            test_settings = Settings()

            # Mock the module-level settings
            with patch("chat_api.factory.settings", test_settings):
                env = detect_environment()
                assert env == Environment.LAMBDA

    def test_detect_docker_environment(self) -> None:
        """Test detection of Docker environment."""
        with patch.dict(
            os.environ,
            {
                "CHAT_DATABASE_URL": "sqlite+aiosqlite:///./data/docker/chat.db",
                "CHAT_REDIS_URL": "redis://redis:6379",
                "AWS_LAMBDA_FUNCTION_NAME": "",  # Not in Lambda
            },
            clear=True,
        ):
            # Force new settings instance in patched environment
            from chat_api.config import Settings

            # Create new settings with current env vars
            test_settings = Settings()

            # Mock the module-level settings
            with patch("chat_api.factory.settings", test_settings):
                env = detect_environment()
                assert env == Environment.DOCKER


class TestServiceFactory:
    """Test service factory functionality."""

    @pytest.mark.asyncio
    async def test_create_service_for_development(self) -> None:
        """Test service creation in development environment."""
        with patch.dict(
            os.environ,
            {
                "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
                "CHAT_GEMINI_API_KEY": "test-key",
                "CHAT_LLM_PROVIDER": "gemini",
                "AWS_LAMBDA_FUNCTION_NAME": "",  # Not in Lambda
            },
            clear=True,
        ):
            # Force new settings instance in patched environment
            from chat_api.config import Settings

            # Create new settings with current env vars
            test_settings = Settings()

            # Mock the module-level settings and database operations
            with (
                patch("chat_api.factory.settings", test_settings),
                patch("chat_api.storage.SQLiteRepository.startup") as mock_startup,
                patch("chat_api.storage.SQLiteRepository.shutdown") as mock_shutdown,
                patch("chat_api.storage.InMemoryCache.startup") as mock_cache_startup,
                patch("chat_api.storage.InMemoryCache.shutdown") as mock_cache_shutdown,
            ):
                mock_startup.return_value = None
                mock_shutdown.return_value = None
                mock_cache_startup.return_value = None
                mock_cache_shutdown.return_value = None

                service = await ServiceFactory.create_for_environment()

                assert service is not None
                assert hasattr(service, "repository")
                assert hasattr(service, "cache")
                assert hasattr(service, "llm_provider")

                # Clean shutdown
                await ServiceFactory.shutdown_service(service)

    @pytest.mark.asyncio
    async def test_service_shutdown_handles_errors(self) -> None:
        """Test that shutdown handles component errors gracefully."""
        with patch.dict(
            os.environ,
            {
                "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
                "CHAT_GEMINI_API_KEY": "test-key",
                "CHAT_LLM_PROVIDER": "gemini",
            },
            clear=True,
        ):
            # Force new settings instance in patched environment
            from chat_api.config import Settings

            # Create new settings with current env vars
            test_settings = Settings()

            # Mock the module-level settings and database operations
            with (
                patch("chat_api.factory.settings", test_settings),
                patch("chat_api.storage.SQLiteRepository.startup") as mock_startup,
                patch("chat_api.storage.InMemoryCache.startup") as mock_cache_startup,
            ):
                mock_startup.return_value = None
                mock_cache_startup.return_value = None

                service = await ServiceFactory.create_for_environment()

                # Mock a shutdown error
                service.repository.shutdown = AsyncMock(
                    side_effect=ConnectionError("Shutdown failed"),
                )
                service.cache.shutdown = AsyncMock()

                # Should not raise an exception
                await ServiceFactory.shutdown_service(service)


@pytest.mark.asyncio
async def test_create_service_convenience_function():
    """Test the convenience create_service function - covers line 133."""
    with (
        patch.dict(
            os.environ,
            {
                "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
                "CHAT_OPENROUTER_API_KEY": "test-key",
            },
            clear=True,
        ),
        patch("chat_api.storage.SQLiteRepository.startup"),
        patch("chat_api.storage.SQLiteRepository.shutdown"),
        patch("chat_api.storage.InMemoryCache.startup"),
        patch("chat_api.storage.InMemoryCache.shutdown"),
        patch("chat_api.providers.create_llm_provider") as mock_llm,
    ):
        mock_llm.return_value = AsyncMock()

        service = await create_service()
        assert service is not None

        # Clean up
        await ServiceFactory.shutdown_service(service)


@pytest.mark.asyncio
async def test_factory_lambda_environment_paths():
    """Test factory creation in Lambda environment - covers lines 62-65, 81-83."""
    with patch.dict(
        os.environ,
        {
            "AWS_LAMBDA_FUNCTION_NAME": "test-function",
            "CHAT_GEMINI_API_KEY": "test-key",
            "CHAT_LLM_PROVIDER": "gemini",
            "CHAT_DYNAMODB_TABLE": "test-table",
            "CHAT_AWS_REGION": "us-east-1",
        },
        clear=True,
    ):
        # Force settings reload
        from chat_api.config import Settings

        test_settings = Settings(_env_file=None)

        with (
            patch("chat_api.factory.settings", test_settings),
            patch("chat_api.factory.detect_environment") as mock_detect,
            patch("chat_api.storage.DynamoDBRepository") as mock_dynamo_class,
            patch("chat_api.storage.InMemoryCache") as mock_cache_class,
            patch("chat_api.providers.create_llm_provider") as mock_llm,
        ):
            # Force Lambda environment detection
            mock_detect.return_value = Environment.LAMBDA

            # Mock DynamoDB repository
            mock_dynamo = AsyncMock()
            mock_dynamo_class.return_value = mock_dynamo

            # Mock cache
            mock_cache = AsyncMock()
            mock_cache_class.return_value = mock_cache

            # Mock LLM provider
            mock_llm.return_value = AsyncMock()

            service = await ServiceFactory.create_for_environment()

            # Verify DynamoDB was created for Lambda (lines 62-65)
            mock_dynamo_class.assert_called_once_with("dynamodb://test-table?region=us-east-1")

            # Verify InMemoryCache was created for Lambda (lines 81-83)
            mock_cache_class.assert_called_once()

            await ServiceFactory.shutdown_service(service)


@pytest.mark.asyncio
async def test_factory_docker_with_dynamodb():
    """Test factory creation in Docker with DynamoDB - covers lines 68-70."""
    with patch.dict(
        os.environ,
        {
            "CHAT_DATABASE_URL": "dynamodb://docker-table?region=us-east-1",
            "CHAT_REDIS_URL": "redis://redis:6379",
            "CHAT_OPENROUTER_API_KEY": "test-key",
        },
        clear=True,
    ):
        from chat_api.config import Settings

        test_settings = Settings(_env_file=None)

        with (
            patch("chat_api.factory.settings", test_settings),
            patch("chat_api.factory.detect_environment") as mock_detect,
            patch("chat_api.storage.DynamoDBRepository") as mock_dynamo_class,
            patch("chat_api.storage.RedisCache") as mock_redis_class,
            patch("chat_api.providers.create_llm_provider") as mock_llm,
        ):
            # Force Docker environment
            mock_detect.return_value = Environment.DOCKER

            # Mock DynamoDB
            mock_dynamo = AsyncMock()
            mock_dynamo_class.return_value = mock_dynamo

            # Mock Redis cache
            mock_redis = AsyncMock()
            mock_redis_class.return_value = mock_redis

            # Mock LLM
            mock_llm.return_value = AsyncMock()

            service = await ServiceFactory.create_for_environment()

            # Verify DynamoDB was created for Docker (lines 68-70)
            mock_dynamo_class.assert_called_once_with("dynamodb://docker-table?region=us-east-1")

            await ServiceFactory.shutdown_service(service)


@pytest.mark.asyncio
async def test_factory_redis_cache_creation():
    """Test factory with Redis cache - covers lines 86-88."""
    with patch.dict(
        os.environ,
        {
            "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "CHAT_REDIS_URL": "redis://localhost:6379",
            "CHAT_OPENROUTER_API_KEY": "test-key",
        },
        clear=True,
    ):
        from chat_api.config import Settings

        test_settings = Settings(_env_file=None)

        with (
            patch("chat_api.factory.settings", test_settings),
            patch("chat_api.factory.detect_environment") as mock_detect,
            patch("chat_api.storage.SQLiteRepository") as mock_sqlite_class,
            patch("chat_api.storage.RedisCache") as mock_redis_class,
            patch("chat_api.providers.create_llm_provider") as mock_llm,
        ):
            # Force development environment
            mock_detect.return_value = Environment.DEVELOPMENT

            # Mock SQLite
            mock_sqlite = AsyncMock()
            mock_sqlite_class.return_value = mock_sqlite

            # Mock Redis
            mock_redis = AsyncMock()
            mock_redis_class.return_value = mock_redis

            # Mock LLM
            mock_llm.return_value = AsyncMock()

            service = await ServiceFactory.create_for_environment()

            # Verify Redis cache was created (lines 86-88)
            mock_redis_class.assert_called_once_with("redis://localhost:6379")

            await ServiceFactory.shutdown_service(service)


@pytest.mark.asyncio
async def test_shutdown_service_cache_failure():
    """Test shutdown with cache failure - covers lines 124-125."""
    with (
        patch.dict(
            os.environ,
            {
                "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
                "CHAT_OPENROUTER_API_KEY": "test-key",
            },
            clear=True,
        ),
        patch("chat_api.storage.SQLiteRepository.startup"),
        patch("chat_api.storage.InMemoryCache.startup"),
        patch("chat_api.providers.create_llm_provider") as mock_llm,
    ):
        mock_llm.return_value = AsyncMock()

        service = await ServiceFactory.create_for_environment()

        # Make cache shutdown fail
        service.cache.shutdown = AsyncMock(side_effect=ConnectionError("Cache shutdown failed"))

        # Repository shutdown should succeed
        service.repository.shutdown = AsyncMock()

        # Should not raise exception despite cache failure
        await ServiceFactory.shutdown_service(service)

        # Repository should still be shut down
        service.repository.shutdown.assert_called_once()
