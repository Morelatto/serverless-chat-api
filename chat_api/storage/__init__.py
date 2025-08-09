"""Storage module with factory for creating repository and cache instances."""

from typing import Any
from urllib.parse import urlparse

from loguru import logger

from ..config import settings
from .cache import DynamoDBCache, NoOpCache, RedisCache, cache_key
from .dynamodb import DynamoDBRepository
from .protocols import Cache, Repository
from .sqlite import SQLiteRepository

# Global instances for backward compatibility
_repository: Repository | None = None
_cache: Cache | None = None


def create_repository(database_url: str | None = None) -> Repository:
    """Create repository instance based on database URL.

    Args:
        database_url: Database URL. Uses settings if not provided.

    Returns:
        Repository instance.
    """
    import os

    url = database_url or settings.database_url

    # Auto-detect AWS environment
    if not database_url and os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        # Running in Lambda - use DynamoDB
        url = f"dynamodb://{settings.dynamodb_table}?region={settings.aws_region}"
        logger.info(f"AWS Lambda detected, using DynamoDB: {settings.dynamodb_table}")

    parsed = urlparse(url)

    if parsed.scheme == "dynamodb":
        logger.info("Creating DynamoDB repository")
        return DynamoDBRepository(url)
    logger.info("Creating SQLite repository")
    return SQLiteRepository(url)


def create_cache(redis_url: str | None = None, database_url: str | None = None) -> Cache:
    """Create cache instance based on configuration.

    Args:
        redis_url: Redis URL for caching.
        database_url: Database URL (used for DynamoDB cache fallback).

    Returns:
        Cache instance.
    """
    import os

    # Try Redis first if explicitly configured
    if redis_url or settings.redis_url:
        logger.info("Creating Redis cache")
        return RedisCache(redis_url or settings.redis_url)

    # Check if we're in AWS Lambda
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        # In Lambda, use DynamoDB for cache
        logger.info(f"AWS Lambda detected, using DynamoDB cache: {settings.dynamodb_table}")
        return DynamoDBCache(settings.dynamodb_table, settings.aws_region)

    # Check if database is DynamoDB
    db_url = database_url or settings.database_url
    parsed = urlparse(db_url)

    if parsed.scheme == "dynamodb":
        logger.info("Creating DynamoDB cache (same as database)")
        table_name = parsed.netloc or parsed.path.lstrip("/")
        region = None
        if parsed.query:
            for param in parsed.query.split("&"):
                if param.startswith("region="):
                    region = param.split("=")[1]
        return DynamoDBCache(table_name, region)

    # Local development - use in-memory cache (NoOp)
    logger.info("Local environment detected, using in-memory cache")
    return NoOpCache()


# Backward compatibility functions (for tests)
async def startup() -> None:
    """Initialize storage (backward compatibility)."""
    global _repository, _cache
    if not _repository:
        _repository = create_repository()
        await _repository.startup()
    if not _cache:
        _cache = create_cache()
        await _cache.startup()


async def shutdown() -> None:
    """Cleanup storage (backward compatibility)."""
    global _repository, _cache
    if _repository:
        await _repository.shutdown()
    if _cache:
        await _cache.shutdown()


async def save_message(id: str, user_id: str, content: str, response: str, **metadata) -> None:
    """Save message (backward compatibility)."""
    if not _repository:
        await startup()
    await _repository.save(id, user_id, content, response, **metadata)  # type: ignore


async def get_user_history(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Get user history (backward compatibility)."""
    if not _repository:
        await startup()
    return await _repository.get_history(user_id, limit)  # type: ignore


async def get_cached(key: str) -> dict[str, Any] | None:
    """Get cached value (backward compatibility)."""
    if not _cache:
        await startup()
    return await _cache.get(key)  # type: ignore


async def set_cached(key: str, value: dict[str, Any], ttl: int = 3600) -> None:
    """Set cached value (backward compatibility)."""
    if not _cache:
        await startup()
    await _cache.set(key, value, ttl)  # type: ignore


async def health_check() -> bool:
    """Health check (backward compatibility)."""
    if not _repository:
        await startup()
    return await _repository.health_check()  # type: ignore


# Export for backward compatibility
__all__ = [
    "Cache",
    "Repository",
    "cache_key",
    "create_cache",
    "create_repository",
    "get_cached",
    "get_user_history",
    "health_check",
    "save_message",
    "set_cached",
    "shutdown",
    "startup",
]
