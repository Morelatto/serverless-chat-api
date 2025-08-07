"""Refactored chat service with separated responsibilities."""

import logging
import time
from datetime import UTC, datetime
from typing import Any, Protocol

from src.shared.cache import CacheService, create_cache_service
from src.shared.database import DatabaseInterface
from src.shared.exceptions import CircuitBreakerOpenException, LLMProviderException
from src.shared.llm import LLMProviderFactory

logger = logging.getLogger(__name__)


class MetricsCollector(Protocol):
    """Protocol for metrics collection."""

    async def record_request(
        self,
        user_id: str,
        model: str,
        latency_ms: int,
        cached: bool,
        success: bool,
    ) -> None:
        """Record a request metric."""
        ...


class SimpleMetricsCollector:
    """Simple metrics collector implementation."""

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self.total_requests = 0
        self.total_errors = 0
        self.total_cache_hits = 0
        self.total_latency_ms = 0

    async def record_request(
        self,
        user_id: str,
        model: str,
        latency_ms: int,
        cached: bool,
        success: bool,
    ) -> None:
        """Record request metrics."""
        self.total_requests += 1
        self.total_latency_ms += latency_ms
        
        if cached:
            self.total_cache_hits += 1
        
        if not success:
            self.total_errors += 1
        
        logger.info(
            {
                "event": "metrics_recorded",
                "user_id": user_id,
                "model": model,
                "latency_ms": latency_ms,
                "cached": cached,
                "success": success,
                "total_requests": self.total_requests,
            }
        )


class ChatRepository:
    """Repository for chat data persistence."""

    def __init__(self, database: DatabaseInterface | None = None) -> None:
        """Initialize repository."""
        self.db = database or DatabaseInterface()

    async def create_interaction(
        self,
        user_id: str,
        prompt: str,
        trace_id: str | None = None,
    ) -> str:
        """Create a new interaction record."""
        return await self.db.save_interaction(
            user_id=user_id,
            prompt=prompt,
            response=None,
            model=None,
            trace_id=trace_id,
        )

    async def update_interaction(
        self,
        interaction_id: str,
        response: str | None = None,
        model: str | None = None,
        tokens: int | None = None,
        latency_ms: int | None = None,
        error: str | None = None,
    ) -> None:
        """Update an existing interaction."""
        await self.db.update_interaction(
            interaction_id=interaction_id,
            response=response,
            model=model,
            tokens=tokens,
            latency_ms=latency_ms,
            error=error,
        )

    async def get_interaction(self, interaction_id: str) -> dict[str, Any] | None:
        """Get an interaction by ID."""
        return await self.db.get_interaction(interaction_id)

    async def get_user_history(
        self, user_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get user interaction history."""
        return await self.db.get_user_interactions(user_id, limit)


class LLMService:
    """Service for LLM interactions."""

    def __init__(
        self,
        llm_factory: LLMProviderFactory | None = None,
        max_retries: int = 3,
    ) -> None:
        """Initialize LLM service."""
        self.llm_factory = llm_factory or LLMProviderFactory()
        self.max_retries = max_retries

    async def generate_response(
        self,
        prompt: str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate response from LLM with retry logic."""
        for attempt in range(self.max_retries):
            try:
                result = await self.llm_factory.generate(
                    prompt=prompt,
                    trace_id=trace_id,
                )
                return result
            except Exception as e:
                logger.warning(
                    f"LLM generation attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )
                if attempt == self.max_retries - 1:
                    raise LLMProviderException(
                        provider=self.llm_factory.primary_provider,
                        original_error=str(e),
                        trace_id=trace_id,
                    )
                # Exponential backoff
                await self._sleep(2 ** attempt)

    async def _sleep(self, seconds: float) -> None:
        """Sleep for testing purposes."""
        import asyncio
        await asyncio.sleep(seconds)

    async def health_check(self) -> bool:
        """Check LLM service health."""
        return await self.llm_factory.health_check()


class CircuitBreakerService:
    """Circuit breaker for external service calls."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_requests: int = 1,
    ) -> None:
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "closed"
        self.half_open_count = 0

    async def call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute function with circuit breaker protection."""
        # Check if circuit should transition from open to half-open
        if self.state == "open":
            if self.last_failure_time:
                time_since_failure = (
                    datetime.now(UTC).replace(tzinfo=None) - self.last_failure_time
                ).total_seconds()
                
                if time_since_failure > self.recovery_timeout:
                    self.state = "half_open"
                    self.half_open_count = 0
                    logger.info("Circuit breaker entering half-open state")
                else:
                    raise CircuitBreakerOpenException(
                        service="LLM",
                        retry_after=int(self.recovery_timeout - time_since_failure),
                    )
            else:
                raise CircuitBreakerOpenException(service="LLM")

        # Handle half-open state
        if self.state == "half_open":
            if self.half_open_count >= self.half_open_requests:
                # Successful requests in half-open, close the circuit
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker recovered to closed state")

        try:
            result = await func(*args, **kwargs)
            
            if self.state == "half_open":
                self.half_open_count += 1
            
            # Reset failure count on success
            if self.state == "closed":
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now(UTC).replace(tzinfo=None)
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )
            
            raise e


class ChatOrchestrator:
    """Main orchestrator for chat operations with separated concerns."""

    def __init__(
        self,
        repository: ChatRepository | None = None,
        llm_service: LLMService | None = None,
        cache_service: CacheService | None = None,
        circuit_breaker: CircuitBreakerService | None = None,
        metrics_collector: MetricsCollector | None = None,
    ) -> None:
        """Initialize chat orchestrator with dependencies."""
        self.repository = repository or ChatRepository()
        self.llm_service = llm_service or LLMService()
        self.cache_service = cache_service or create_cache_service()
        self.circuit_breaker = circuit_breaker or CircuitBreakerService()
        self.metrics = metrics_collector or SimpleMetricsCollector()

    async def process_prompt(
        self,
        user_id: str,
        prompt: str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Process a chat prompt with all services."""
        start_time = time.time()
        
        try:
            # Check cache first
            cached_response = await self.cache_service.get_response(prompt)
            if cached_response:
                # Create interaction record for cached response
                interaction_id = await self.repository.create_interaction(
                    user_id=user_id,
                    prompt=prompt,
                    trace_id=trace_id,
                )
                
                await self.repository.update_interaction(
                    interaction_id=interaction_id,
                    response=cached_response,
                    model="cache",
                    latency_ms=int((time.time() - start_time) * 1000),
                )
                
                # Record metrics
                latency_ms = int((time.time() - start_time) * 1000)
                await self.metrics.record_request(
                    user_id=user_id,
                    model="cache",
                    latency_ms=latency_ms,
                    cached=True,
                    success=True,
                )
                
                return {
                    "interaction_id": interaction_id,
                    "response": cached_response,
                    "model": "cache",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "cached": True,
                    "latency_ms": latency_ms,
                }
            
            # Create interaction record
            interaction_id = await self.repository.create_interaction(
                user_id=user_id,
                prompt=prompt,
                trace_id=trace_id,
            )
            
            try:
                # Generate response with circuit breaker
                llm_result = await self.circuit_breaker.call(
                    self.llm_service.generate_response,
                    prompt=prompt,
                    trace_id=trace_id,
                )
                
                # Update interaction with response
                await self.repository.update_interaction(
                    interaction_id=interaction_id,
                    response=llm_result["response"],
                    model=llm_result["model"],
                    tokens=llm_result.get("tokens", 0),
                    latency_ms=llm_result.get("latency_ms", 0),
                )
                
                # Cache the response
                await self.cache_service.set_response(
                    prompt=prompt,
                    response=llm_result["response"],
                )
                
                # Record metrics
                latency_ms = int((time.time() - start_time) * 1000)
                await self.metrics.record_request(
                    user_id=user_id,
                    model=llm_result["model"],
                    latency_ms=latency_ms,
                    cached=False,
                    success=True,
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
                # Update interaction with error
                await self.repository.update_interaction(
                    interaction_id=interaction_id,
                    error=str(e),
                )
                
                # Record error metrics
                latency_ms = int((time.time() - start_time) * 1000)
                await self.metrics.record_request(
                    user_id=user_id,
                    model="error",
                    latency_ms=latency_ms,
                    cached=False,
                    success=False,
                )
                
                logger.error(
                    {
                        "event": "prompt_processing_failed",
                        "trace_id": trace_id,
                        "interaction_id": interaction_id,
                        "error": str(e),
                    }
                )
                
                raise
                
        except Exception as e:
            logger.error(f"Failed to process prompt: {e}")
            raise

    async def get_user_history(
        self, user_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get user interaction history."""
        return await self.repository.get_user_history(user_id, limit)

    async def check_health(self) -> dict[str, Any]:
        """Check health of all services."""
        health_status = {
            "database": False,
            "llm": False,
            "cache": {},
            "circuit_breaker": self.circuit_breaker.state,
        }
        
        # Check database
        try:
            await self.repository.db.health_check()
            health_status["database"] = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        
        # Check LLM
        try:
            health_status["llm"] = await self.llm_service.health_check()
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
        
        # Check cache
        try:
            health_status["cache"] = await self.cache_service.health_check()
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
        
        return health_status