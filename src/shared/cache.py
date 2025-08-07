"""Distributed cache implementation with Redis and in-memory fallback."""

import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class CacheBackend(Protocol):
    """Protocol for cache backend implementations."""

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        ...

    async def set(self, key: str, value: str, ttl: int) -> None:
        """Set value in cache with TTL."""
        ...

    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        ...

    async def health_check(self) -> bool:
        """Check cache backend health."""
        ...


class InMemoryCacheBackend:
    """In-memory cache backend for development and fallback."""

    def __init__(self, max_size: int = 1000) -> None:
        """Initialize in-memory cache."""
        self.cache: dict[str, dict[str, Any]] = {}
        self.max_size = max_size
        logger.info("In-memory cache backend initialized")

    async def get(self, key: str) -> str | None:
        """Get value from memory cache."""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now(UTC).replace(tzinfo=None) < entry["expires_at"]:
                logger.debug(f"Cache hit for key {key[:8]}...")
                return str(entry["value"])
            else:
                del self.cache[key]
                logger.debug(f"Cache expired for key {key[:8]}...")
        return None

    async def set(self, key: str, value: str, ttl: int) -> None:
        """Set value in memory cache."""
        expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=ttl)
        self.cache[key] = {"value": value, "expires_at": expires_at}
        
        # Implement simple LRU eviction
        if len(self.cache) > self.max_size:
            oldest_key = min(self.cache.items(), key=lambda x: x[1]["expires_at"])[0]
            del self.cache[oldest_key]
            logger.debug(f"Evicted oldest key {oldest_key[:8]}... from cache")

    async def delete(self, key: str) -> None:
        """Delete value from memory cache."""
        self.cache.pop(key, None)

    async def exists(self, key: str) -> bool:
        """Check if key exists in memory cache."""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now(UTC).replace(tzinfo=None) < entry["expires_at"]:
                return True
            else:
                del self.cache[key]
        return False

    async def health_check(self) -> bool:
        """Health check always returns True for in-memory."""
        return True


class RedisCacheBackend:
    """Redis cache backend for production."""

    def __init__(self, redis_url: str) -> None:
        """Initialize Redis cache backend."""
        self.redis_url = redis_url
        self.redis_client = None
        self._initialized = False

    async def _ensure_connected(self) -> None:
        """Ensure Redis client is connected."""
        if not self._initialized:
            try:
                import redis.asyncio as aioredis
                
                self.redis_client = await aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                await self.redis_client.ping()
                self._initialized = True
                logger.info("Redis cache backend initialized")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

    async def get(self, key: str) -> str | None:
        """Get value from Redis."""
        await self._ensure_connected()
        try:
            value = await self.redis_client.get(key)
            if value:
                logger.debug(f"Redis cache hit for key {key[:8]}...")
            return value
        except Exception as e:
            logger.error(f"Redis get failed: {e}")
            raise

    async def set(self, key: str, value: str, ttl: int) -> None:
        """Set value in Redis with TTL."""
        await self._ensure_connected()
        try:
            await self.redis_client.setex(key, ttl, value)
            logger.debug(f"Set key {key[:8]}... in Redis with TTL {ttl}s")
        except Exception as e:
            logger.error(f"Redis set failed: {e}")
            raise

    async def delete(self, key: str) -> None:
        """Delete value from Redis."""
        await self._ensure_connected()
        try:
            await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete failed: {e}")
            raise

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        await self._ensure_connected()
        try:
            return bool(await self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Redis exists check failed: {e}")
            raise

    async def health_check(self) -> bool:
        """Check Redis connectivity."""
        try:
            await self._ensure_connected()
            await self.redis_client.ping()
            return True
        except Exception:
            return False


class CacheService:
    """High-level cache service with automatic fallback."""

    def __init__(
        self,
        backend: CacheBackend | None = None,
        ttl_seconds: int = 3600,
        enable_cache: bool = True,
    ) -> None:
        """Initialize cache service."""
        self.backend = backend or InMemoryCacheBackend()
        self.ttl_seconds = ttl_seconds
        self.enable_cache = enable_cache
        self.fallback_backend: CacheBackend | None = None
        
        # Setup fallback if primary is Redis
        if isinstance(self.backend, RedisCacheBackend):
            self.fallback_backend = InMemoryCacheBackend()
            logger.info("Configured in-memory fallback for Redis cache")

    def _generate_key(self, prompt: str, prefix: str = "chat") -> str:
        """Generate cache key from prompt."""
        normalized = prompt.lower().strip()
        hash_digest = hashlib.sha256(normalized.encode()).hexdigest()
        return f"{prefix}:{hash_digest[:16]}"

    async def get_response(self, prompt: str) -> str | None:
        """Get cached response for a prompt."""
        if not self.enable_cache:
            return None
        
        key = self._generate_key(prompt)
        
        try:
            value = await self.backend.get(key)
            if value:
                logger.info(f"Cache hit for prompt (key: {key[:20]}...)")
            return value
        except Exception as e:
            logger.warning(f"Primary cache failed, trying fallback: {e}")
            if self.fallback_backend:
                try:
                    return await self.fallback_backend.get(key)
                except Exception as fallback_error:
                    logger.error(f"Fallback cache also failed: {fallback_error}")
            return None

    async def set_response(self, prompt: str, response: str) -> None:
        """Cache a response for a prompt."""
        if not self.enable_cache:
            return
        
        key = self._generate_key(prompt)
        
        try:
            await self.backend.set(key, response, self.ttl_seconds)
            logger.info(f"Cached response (key: {key[:20]}..., ttl: {self.ttl_seconds}s)")
        except Exception as e:
            logger.warning(f"Primary cache set failed, trying fallback: {e}")
            if self.fallback_backend:
                try:
                    await self.fallback_backend.set(key, response, self.ttl_seconds)
                except Exception as fallback_error:
                    logger.error(f"Fallback cache set also failed: {fallback_error}")

    async def invalidate(self, prompt: str) -> None:
        """Invalidate cached response for a prompt."""
        if not self.enable_cache:
            return
        
        key = self._generate_key(prompt)
        
        try:
            await self.backend.delete(key)
            if self.fallback_backend:
                await self.fallback_backend.delete(key)
            logger.info(f"Invalidated cache (key: {key[:20]}...)")
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")

    async def health_check(self) -> dict[str, bool]:
        """Check health of cache backends."""
        health = {"primary": False, "fallback": False}
        
        try:
            health["primary"] = await self.backend.health_check()
        except Exception as e:
            logger.error(f"Primary cache health check failed: {e}")
        
        if self.fallback_backend:
            try:
                health["fallback"] = await self.fallback_backend.health_check()
            except Exception as e:
                logger.error(f"Fallback cache health check failed: {e}")
        
        return health


def create_cache_service() -> CacheService:
    """Factory function to create cache service based on configuration."""
    import os
    
    redis_url = os.getenv("REDIS_URL")
    enable_cache = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    
    if redis_url and redis_url.startswith("redis://"):
        try:
            backend = RedisCacheBackend(redis_url)
            logger.info("Using Redis cache backend")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis, falling back to in-memory: {e}")
            backend = InMemoryCacheBackend()
    else:
        backend = InMemoryCacheBackend()
        logger.info("Using in-memory cache backend")
    
    return CacheService(
        backend=backend,
        ttl_seconds=ttl_seconds,
        enable_cache=enable_cache,
    )