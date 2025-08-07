"""Distributed rate limiting with Redis and in-memory fallback."""

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Protocol

from src.shared.exceptions import RateLimitException

logger = logging.getLogger(__name__)


class RateLimitBackend(Protocol):
    """Protocol for rate limit backend implementations."""

    async def check_and_increment(
        self, key: str, limit: int, window_seconds: int
    ) -> tuple[bool, int]:
        """Check if request is allowed and increment counter.
        
        Returns:
            tuple: (is_allowed, current_count)
        """
        ...

    async def get_remaining(self, key: str, limit: int, window_seconds: int) -> int:
        """Get remaining requests in current window."""
        ...

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        ...


class InMemoryRateLimitBackend:
    """In-memory rate limit backend for development and fallback."""

    def __init__(self) -> None:
        """Initialize in-memory rate limiter."""
        self.requests: dict[str, list[datetime]] = defaultdict(list)
        logger.info("In-memory rate limit backend initialized")

    async def check_and_increment(
        self, key: str, limit: int, window_seconds: int
    ) -> tuple[bool, int]:
        """Check and increment in-memory counter."""
        current_time = datetime.now(UTC).replace(tzinfo=None)
        window_start = current_time - timedelta(seconds=window_seconds)
        
        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if req_time > window_start
        ]
        
        current_count = len(self.requests[key])
        
        if current_count >= limit:
            return False, current_count
        
        self.requests[key].append(current_time)
        return True, current_count + 1

    async def get_remaining(self, key: str, limit: int, window_seconds: int) -> int:
        """Get remaining requests in current window."""
        current_time = datetime.now(UTC).replace(tzinfo=None)
        window_start = current_time - timedelta(seconds=window_seconds)
        
        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > window_start
        ]
        
        return max(0, limit - len(self.requests[key]))

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        self.requests.pop(key, None)


class RedisRateLimitBackend:
    """Redis rate limit backend for production using sliding window."""

    def __init__(self, redis_url: str) -> None:
        """Initialize Redis rate limit backend."""
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
                    decode_responses=False,  # We need bytes for Lua script
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                await self.redis_client.ping()
                self._initialized = True
                
                # Register Lua script for atomic rate limiting
                self._register_lua_script()
                logger.info("Redis rate limit backend initialized")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

    def _register_lua_script(self) -> None:
        """Register Lua script for atomic rate limiting."""
        # Sliding window rate limiter in Lua
        self.lua_script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local current_time = tonumber(ARGV[3])
        
        -- Remove old entries
        redis.call('ZREMRANGEBYSCORE', key, 0, current_time - window)
        
        -- Count current entries
        local current_count = redis.call('ZCARD', key)
        
        if current_count < limit then
            -- Add new entry
            redis.call('ZADD', key, current_time, current_time)
            redis.call('EXPIRE', key, window)
            return {1, current_count + 1}
        else
            return {0, current_count}
        end
        """
        self.script_sha = None

    async def check_and_increment(
        self, key: str, limit: int, window_seconds: int
    ) -> tuple[bool, int]:
        """Check and increment Redis counter using sliding window."""
        await self._ensure_connected()
        
        try:
            current_time = datetime.now(UTC).timestamp()
            
            # Try to use cached script SHA first
            if self.script_sha:
                try:
                    result = await self.redis_client.evalsha(
                        self.script_sha,
                        1,
                        f"ratelimit:{key}",
                        str(limit),
                        str(window_seconds),
                        str(int(current_time * 1000000)),  # Microseconds for precision
                    )
                except Exception:
                    # Script not in cache, will reload below
                    self.script_sha = None
            
            # Load and execute script if SHA not available
            if not self.script_sha:
                self.script_sha = await self.redis_client.script_load(self.lua_script)
                result = await self.redis_client.evalsha(
                    self.script_sha,
                    1,
                    f"ratelimit:{key}",
                    str(limit),
                    str(window_seconds),
                    str(int(current_time * 1000000)),
                )
            
            is_allowed = bool(result[0])
            current_count = int(result[1])
            
            if not is_allowed:
                logger.warning(f"Rate limit exceeded for key {key}: {current_count}/{limit}")
            
            return is_allowed, current_count
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            raise

    async def get_remaining(self, key: str, limit: int, window_seconds: int) -> int:
        """Get remaining requests in current window."""
        await self._ensure_connected()
        
        try:
            current_time = datetime.now(UTC).timestamp()
            
            # Remove old entries
            await self.redis_client.zremrangebyscore(
                f"ratelimit:{key}",
                0,
                current_time - window_seconds
            )
            
            # Count current entries
            current_count = await self.redis_client.zcard(f"ratelimit:{key}")
            
            return max(0, limit - current_count)
            
        except Exception as e:
            logger.error(f"Redis get remaining failed: {e}")
            raise

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        await self._ensure_connected()
        
        try:
            await self.redis_client.delete(f"ratelimit:{key}")
            logger.info(f"Reset rate limit for key {key}")
        except Exception as e:
            logger.error(f"Redis reset failed: {e}")
            raise


class RateLimiterService:
    """High-level rate limiter service with automatic fallback."""

    def __init__(
        self,
        backend: RateLimitBackend | None = None,
        default_limit: int = 60,
        default_window: int = 60,
    ) -> None:
        """Initialize rate limiter service."""
        self.backend = backend or InMemoryRateLimitBackend()
        self.default_limit = default_limit
        self.default_window = default_window
        self.fallback_backend: RateLimitBackend | None = None
        
        # Setup fallback if primary is Redis
        if isinstance(self.backend, RedisRateLimitBackend):
            self.fallback_backend = InMemoryRateLimitBackend()
            logger.info("Configured in-memory fallback for Redis rate limiter")

    async def check_rate_limit(
        self,
        user_id: str,
        api_key_hash: str | None = None,
        limit: int | None = None,
        window: int | None = None,
        trace_id: str | None = None,
    ) -> None:
        """Check rate limit for a user, raise exception if exceeded."""
        limit = limit or self.default_limit
        window = window or self.default_window
        
        # Create composite key
        key_parts = [user_id]
        if api_key_hash:
            key_parts.append(api_key_hash)
        key = ":".join(key_parts)
        
        try:
            is_allowed, current_count = await self.backend.check_and_increment(
                key, limit, window
            )
            
            if not is_allowed:
                raise RateLimitException(
                    limit=limit,
                    window=window,
                    trace_id=trace_id,
                )
            
            logger.debug(f"Rate limit check passed for {key}: {current_count}/{limit}")
            
        except RateLimitException:
            raise
        except Exception as e:
            logger.warning(f"Primary rate limiter failed, trying fallback: {e}")
            
            if self.fallback_backend:
                try:
                    is_allowed, current_count = await self.fallback_backend.check_and_increment(
                        key, limit, window
                    )
                    
                    if not is_allowed:
                        raise RateLimitException(
                            limit=limit,
                            window=window,
                            trace_id=trace_id,
                        )
                    
                    logger.debug(f"Fallback rate limit check passed for {key}: {current_count}/{limit}")
                    
                except RateLimitException:
                    raise
                except Exception as fallback_error:
                    logger.error(f"Fallback rate limiter also failed: {fallback_error}")
                    # In case of total failure, allow the request but log warning
                    logger.warning("Both rate limiters failed, allowing request")

    async def get_rate_limit_info(
        self,
        user_id: str,
        api_key_hash: str | None = None,
        limit: int | None = None,
        window: int | None = None,
    ) -> dict[str, int]:
        """Get rate limit information for a user."""
        limit = limit or self.default_limit
        window = window or self.default_window
        
        # Create composite key
        key_parts = [user_id]
        if api_key_hash:
            key_parts.append(api_key_hash)
        key = ":".join(key_parts)
        
        try:
            remaining = await self.backend.get_remaining(key, limit, window)
            return {
                "limit": limit,
                "remaining": remaining,
                "window_seconds": window,
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit info: {e}")
            return {
                "limit": limit,
                "remaining": limit,  # Assume full quota on error
                "window_seconds": window,
            }

    async def reset_rate_limit(self, user_id: str, api_key_hash: str | None = None) -> None:
        """Reset rate limit for a user (admin function)."""
        # Create composite key
        key_parts = [user_id]
        if api_key_hash:
            key_parts.append(api_key_hash)
        key = ":".join(key_parts)
        
        try:
            await self.backend.reset(key)
            if self.fallback_backend:
                await self.fallback_backend.reset(key)
            logger.info(f"Reset rate limit for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")


def create_rate_limiter() -> RateLimiterService:
    """Factory function to create rate limiter based on configuration."""
    import os
    
    redis_url = os.getenv("REDIS_URL")
    default_limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    default_window = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    
    if redis_url and redis_url.startswith("redis://"):
        try:
            backend = RedisRateLimitBackend(redis_url)
            logger.info("Using Redis rate limit backend")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis rate limiter, falling back to in-memory: {e}")
            backend = InMemoryRateLimitBackend()
    else:
        backend = InMemoryRateLimitBackend()
        logger.info("Using in-memory rate limit backend")
    
    return RateLimiterService(
        backend=backend,
        default_limit=default_limit,
        default_window=default_window,
    )