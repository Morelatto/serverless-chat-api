"""Chat service with business logic and resilience patterns."""

import hashlib
import logging
import time
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from src.shared.config import settings
from src.shared.database import DatabaseInterface
from src.shared.llm import LLMProviderFactory

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker pattern implementation for fault tolerance.
    
    Prevents cascading failures by temporarily blocking calls to a failing service.
    States: CLOSED (normal), OPEN (blocking), HALF_OPEN (testing recovery).
    
    Attributes:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        state: Current circuit state (CLOSED, OPEN, HALF_OPEN)
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Failures required to open circuit
            recovery_timeout: Seconds before attempting recovery
        """
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time: datetime | None = None
        self.state = CircuitState.CLOSED

    async def call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute with circuit breaker."""
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and datetime.now(UTC).replace(
                tzinfo=None
            ) - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                logger.info("Circuit breaker recovered to CLOSED state")
            self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now(UTC).replace(tzinfo=None)

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")

            raise e


class ResponseCache:
    """LRU cache for responses with O(1) operations."""

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        from collections import OrderedDict
        
        self.cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.ttl = ttl_seconds
        self.max_size = max_size

    def _get_key(self, prompt: str) -> str:
        """Generate cache key."""
        normalized = prompt.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(self, prompt: str) -> str | None:
        """Get cached response with LRU update."""
        key = self._get_key(prompt)
        if key in self.cache:
            entry = self.cache[key]
            current_time = datetime.now(timezone.utc).replace(tzinfo=None)
            
            # Check if expired
            if current_time - entry["time"] < timedelta(seconds=self.ttl):
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                logger.info(f"Cache hit for key {key[:8]}")
                return str(entry["response"])
            else:
                # Remove expired entry
                del self.cache[key]
        return None

    def set(self, prompt: str, response: str) -> None:
        """Cache response with LRU eviction."""
        key = self._get_key(prompt)
        
        # Update existing or add new
        if key in self.cache:
            self.cache.move_to_end(key)
        
        self.cache[key] = {
            "response": response,
            "time": datetime.now(timezone.utc).replace(tzinfo=None)
        }
        
        # LRU eviction - O(1) operation
        if len(self.cache) > self.max_size:
            # Remove least recently used (first item)
            self.cache.popitem(last=False)
            logger.debug("Evicted LRU cache entry")


class ChatService:
    """Main service orchestrating chat functionality."""

    def __init__(self) -> None:
        self.db = DatabaseInterface()
        self.llm_factory = LLMProviderFactory()
        self.cache = ResponseCache(ttl_seconds=settings.CACHE_TTL_SECONDS)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.CIRCUIT_BREAKER_THRESHOLD,
            recovery_timeout=settings.CIRCUIT_BREAKER_TIMEOUT,
        )

    async def process_prompt(self, user_id: str, prompt: str, trace_id: str) -> dict[str, Any]:
        """Process chat prompt with resilience."""
        start_time = time.time()

        # Check cache first
        cached_response = self.cache.get(prompt)
        if cached_response and settings.ENABLE_CACHE:
            interaction_id = await self.db.save_interaction(
                user_id=user_id,
                prompt=prompt,
                response=cached_response,
                model="cache",
                trace_id=trace_id,
            )

            return {
                "interaction_id": interaction_id,
                "response": cached_response,
                "model": "cache",
                "timestamp": datetime.now(UTC).isoformat(),
                "cached": True,
                "latency_ms": int((time.time() - start_time) * 1000),
            }

        # Save prompt to database
        interaction_id = await self.db.save_interaction(
            user_id=user_id, prompt=prompt, response=None, model=None, trace_id=trace_id
        )

        try:
            # Call LLM with circuit breaker
            llm_result = await self.circuit_breaker.call(
                self.llm_factory.generate, prompt=prompt, trace_id=trace_id
            )

            # Update database with response
            await self.db.update_interaction(
                interaction_id=interaction_id,
                response=llm_result["response"],
                model=llm_result["model"],
                tokens=llm_result.get("tokens", 0),
                latency_ms=llm_result.get("latency_ms", 0),
            )

            # Cache successful response
            if settings.ENABLE_CACHE:
                self.cache.set(prompt, llm_result["response"])

            # Log metrics
            latency_ms = int((time.time() - start_time) * 1000)
            logger.info(
                {
                    "event": "prompt_processed",
                    "trace_id": trace_id,
                    "interaction_id": interaction_id,
                    "model": llm_result["model"],
                    "tokens": llm_result.get("tokens", 0),
                    "latency_ms": latency_ms,
                    "cached": False,
                }
            )

            return {
                "interaction_id": interaction_id,
                "response": llm_result["response"],
                "model": llm_result["model"],
                "timestamp": datetime.now(UTC).isoformat(),
                "cached": False,
                "latency_ms": latency_ms,
            }

        except Exception as e:
            # Log error and update database
            logger.error(
                {
                    "event": "prompt_failed",
                    "trace_id": trace_id,
                    "interaction_id": interaction_id,
                    "error": str(e),
                }
            )

            await self.db.update_interaction(
                interaction_id=interaction_id, response=None, model="error", error=str(e)
            )

            raise e

    async def check_dependencies(self) -> dict[str, bool]:
        """Check dependencies health."""
        checks = {
            "database": False,
            "llm_provider": False,
            "cache": True,  # Always healthy as it's in-memory
        }

        # Check database
        try:
            await self.db.health_check()
            checks["database"] = True
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")

        # Check LLM provider
        try:
            await self.llm_factory.health_check()
            checks["llm_provider"] = True
        except Exception as e:
            logger.warning(f"LLM provider health check failed: {e}")

        return checks
