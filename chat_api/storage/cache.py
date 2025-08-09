"""Cache implementations."""

import asyncio
import hashlib
import json
import time
from datetime import UTC, datetime
from typing import Any

from loguru import logger


def cache_key(user_id: str, content: str) -> str:
    """Generate efficient cache key.

    For short content, hash the full text.
    For long content, use prefix + hash to avoid hashing large strings.
    """
    if len(content) <= 100:
        text = f"{user_id}:{content}"
    else:
        # Use first 100 chars + hash of full content for efficiency
        text = f"{user_id}:{content[:100]}:{hash(content)}"

    return hashlib.sha256(text.encode()).hexdigest()[:16]


class RedisCache:
    """Redis cache implementation."""

    def __init__(self, redis_url: str):
        """Initialize Redis cache.

        Args:
            redis_url: Redis connection URL.
        """
        self.redis_url = redis_url
        self.redis = None

    async def startup(self) -> None:
        """Initialize Redis connection."""
        try:
            import redis.asyncio as redis

            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            await self.redis.ping()
            logger.info("Redis cache connected")
        except (ConnectionError, TimeoutError, ImportError) as e:
            logger.warning(f"Redis connection failed: {e}. Cache disabled.")
            self.redis = None

    async def shutdown(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get cached value.

        Args:
            key: Cache key.

        Returns:
            Cached data if found, None otherwise.
        """
        if not self.redis:
            return None

        try:
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except (json.JSONDecodeError, ConnectionError, TimeoutError) as e:
            logger.debug(f"Cache get failed for key {key}: {e}")
            return None

    async def set(self, key: str, value: dict[str, Any], ttl: int = 3600) -> None:
        """Set cached value with TTL.

        Args:
            key: Cache key.
            value: Data to cache.
            ttl: Time to live in seconds.
        """
        if not self.redis:
            return

        try:
            await self.redis.setex(key, ttl, json.dumps(value))
        except (TypeError, ConnectionError, TimeoutError) as e:
            logger.debug(f"Cache set failed for key {key}: {e}")


class DynamoDBCache:
    """DynamoDB cache implementation (when Redis not available)."""

    def __init__(self, table_name: str, region: str | None = None):
        """Initialize DynamoDB cache.

        Args:
            table_name: DynamoDB table name.
            region: AWS region.
        """
        self.table_name = table_name
        self.region = region
        self.table = None

    async def startup(self) -> None:
        """Initialize DynamoDB table reference."""
        try:
            import boto3

            resource = boto3.resource("dynamodb", region_name=self.region)
            self.table = resource.Table(self.table_name)
            logger.info(f"DynamoDB cache using table: {self.table_name}")
        except ImportError:
            logger.warning("boto3 not available for DynamoDB cache")
            self.table = None

    async def shutdown(self) -> None:
        """No cleanup needed for DynamoDB."""
        pass

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get cached value.

        Args:
            key: Cache key.

        Returns:
            Cached data if found and not expired, None otherwise.
        """
        if not self.table:
            return None

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: self.table.get_item(Key={"pk": f"cache#{key}", "sk": "data"})
            )

            if "Item" in response and response["Item"].get("ttl", 0) > int(time.time()):
                cached_data = response["Item"].get("cached_data")
                return cached_data if isinstance(cached_data, dict) else None
        except (KeyError, TypeError, AttributeError) as e:
            logger.debug(f"DynamoDB cache get failed for key {key}: {e}")

        return None

    async def set(self, key: str, value: dict[str, Any], ttl: int = 3600) -> None:
        """Set cached value with TTL.

        Args:
            key: Cache key.
            value: Data to cache.
            ttl: Time to live in seconds.
        """
        if not self.table:
            return

        try:
            expire_time = int(time.time()) + ttl

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.table.put_item(
                    Item={
                        "pk": f"cache#{key}",
                        "sk": "data",
                        "cached_data": value,
                        "ttl": expire_time,
                        "created_at": datetime.now(UTC).isoformat(),
                    }
                ),
            )
        except (TypeError, AttributeError) as e:
            logger.debug(f"DynamoDB cache set failed for key {key}: {e}")


class NoOpCache:
    """No-op cache implementation when caching is disabled."""

    async def startup(self) -> None:
        """No initialization needed."""
        pass

    async def shutdown(self) -> None:
        """No cleanup needed."""
        pass

    async def get(self, key: str) -> dict[str, Any] | None:
        """Always returns None (no caching)."""
        return None

    async def set(self, key: str, value: dict[str, Any], ttl: int = 3600) -> None:
        """Does nothing (no caching)."""
        pass
