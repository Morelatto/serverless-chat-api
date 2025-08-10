"""Service factory for dependency injection - clean environment-based setup."""

from enum import Enum
from typing import Any

from loguru import logger

from .chat import ChatService
from .config import settings
from .providers import create_llm_provider


class Environment(Enum):
    """Explicit environment types - no magic detection."""

    DEVELOPMENT = "development"
    DOCKER = "docker"
    LAMBDA = "lambda"


def detect_environment() -> Environment:
    """Detect current environment with explicit logic."""
    if settings.is_lambda_environment:
        return Environment.LAMBDA
    if settings.redis_url and "docker" in settings.database_url:
        return Environment.DOCKER
    return Environment.DEVELOPMENT


class ServiceFactory:
    """Factory for creating configured ChatService instances."""

    @staticmethod
    async def create_for_environment() -> ChatService:
        """Create a fully configured ChatService for the current environment."""
        env = detect_environment()
        logger.info(f"Creating services for environment: {env.value}")

        # Create components based on environment
        repository = await ServiceFactory._create_repository(env)
        cache = await ServiceFactory._create_cache(env)
        llm_provider = ServiceFactory._create_llm_provider()

        # Initialize all components
        await repository.startup()
        await cache.startup()

        service = ChatService(
            repository=repository,
            cache=cache,
            llm_provider=llm_provider,
        )

        logger.info(f"ChatService created successfully for {env.value}")
        return service

    @staticmethod
    async def _create_repository(env: Environment) -> Any:
        """Create repository based on environment."""
        if env == Environment.LAMBDA:
            # Lambda always uses DynamoDB
            from .storage import DynamoDBRepository

            table_name = settings.dynamodb_table
            return DynamoDBRepository(f"dynamodb://{table_name}?region={settings.aws_region}")
        if env == Environment.DOCKER and "dynamodb" in settings.database_url:
            # Docker can use DynamoDB if configured
            from .storage import DynamoDBRepository

            return DynamoDBRepository(settings.database_url)
        # Development and Docker default to SQLite
        from .storage import SQLiteRepository

        return SQLiteRepository(settings.database_url)

    @staticmethod
    async def _create_cache(env: Environment) -> Any:
        """Create cache based on environment."""
        if env == Environment.LAMBDA:
            # Lambda uses in-memory cache only
            from .storage import InMemoryCache

            return InMemoryCache()
        if settings.redis_url:
            # Redis available - use it
            from .storage import RedisCache

            return RedisCache(settings.redis_url)
        # Fallback to in-memory
        from .storage import InMemoryCache

        return InMemoryCache()

    @staticmethod
    def _create_llm_provider() -> Any:
        """Create LLM provider based on configuration."""
        # Get API key based on provider
        api_key = None
        if settings.llm_provider == "gemini":
            api_key = settings.gemini_api_key
        elif settings.llm_provider == "openrouter":
            api_key = settings.openrouter_api_key

        return create_llm_provider(
            provider_type=settings.llm_provider,
            model=settings.llm_model,
            api_key=api_key,
        )

    @staticmethod
    async def shutdown_service(service: ChatService) -> None:
        """Clean shutdown of all service components."""
        logger.info("Shutting down ChatService components")

        try:
            await service.repository.shutdown()
            logger.debug("Repository shutdown complete")
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(f"Repository shutdown failed: {e}")

        try:
            await service.cache.shutdown()
            logger.debug("Cache shutdown complete")
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(f"Cache shutdown failed: {e}")

        logger.info("ChatService shutdown complete")


# Convenience function for simple usage
async def create_service() -> ChatService:
    """Create ChatService for current environment (convenience function)."""
    return await ServiceFactory.create_for_environment()
