"""Dependency injection container for the application."""

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from src.chat.service_refactored import (
    ChatOrchestrator,
    ChatRepository,
    CircuitBreakerService,
    LLMService,
    SimpleMetricsCollector,
)
from src.shared.cache import CacheService, create_cache_service
from src.shared.config import settings
from src.shared.database import DatabaseInterface
from src.shared.exceptions import AuthenticationException, AuthorizationException
from src.shared.llm import LLMProviderFactory
from src.shared.rate_limiter import RateLimiterService, create_rate_limiter

logger = logging.getLogger(__name__)


# Singleton instances cache
@lru_cache
def get_database() -> DatabaseInterface:
    """Get database instance (singleton)."""
    return DatabaseInterface()


@lru_cache
def get_cache_service() -> CacheService:
    """Get cache service instance (singleton)."""
    return create_cache_service()


@lru_cache
def get_rate_limiter() -> RateLimiterService:
    """Get rate limiter instance (singleton)."""
    return create_rate_limiter()


@lru_cache
def get_llm_factory() -> LLMProviderFactory:
    """Get LLM factory instance (singleton)."""
    return LLMProviderFactory()


@lru_cache
def get_metrics_collector() -> SimpleMetricsCollector:
    """Get metrics collector instance (singleton)."""
    return SimpleMetricsCollector()


@lru_cache
def get_circuit_breaker() -> CircuitBreakerService:
    """Get circuit breaker instance (singleton)."""
    return CircuitBreakerService(
        failure_threshold=settings.CIRCUIT_BREAKER_THRESHOLD,
        recovery_timeout=settings.CIRCUIT_BREAKER_TIMEOUT,
    )


def get_chat_repository(
    database: Annotated[DatabaseInterface, Depends(get_database)]
) -> ChatRepository:
    """Get chat repository with injected database."""
    return ChatRepository(database=database)


def get_llm_service(
    llm_factory: Annotated[LLMProviderFactory, Depends(get_llm_factory)]
) -> LLMService:
    """Get LLM service with injected factory."""
    return LLMService(llm_factory=llm_factory)


def get_chat_orchestrator(
    repository: Annotated[ChatRepository, Depends(get_chat_repository)],
    llm_service: Annotated[LLMService, Depends(get_llm_service)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    circuit_breaker: Annotated[CircuitBreakerService, Depends(get_circuit_breaker)],
    metrics_collector: Annotated[SimpleMetricsCollector, Depends(get_metrics_collector)],
) -> ChatOrchestrator:
    """Get chat orchestrator with all dependencies injected."""
    return ChatOrchestrator(
        repository=repository,
        llm_service=llm_service,
        cache_service=cache_service,
        circuit_breaker=circuit_breaker,
        metrics_collector=metrics_collector,
    )


async def verify_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> str:
    """Verify API key and return hashed key for identification."""
    import hashlib
    
    # Skip API key check if not required
    if not settings.REQUIRE_API_KEY:
        return "dev-mode"
    
    # Check if API key is provided
    if not x_api_key:
        raise AuthenticationException(
            message="API key required in X-Api-Key header"
        )
    
    # Validate API key
    valid_keys = settings.API_KEYS.split(",") if settings.API_KEYS else []
    if x_api_key not in valid_keys:
        raise AuthorizationException(
            message="Invalid API key"
        )
    
    # Return hashed key for logging/rate limiting
    return hashlib.sha256(x_api_key.encode()).hexdigest()[:8]


async def check_rate_limit_dependency(
    api_key_hash: Annotated[str, Depends(verify_api_key)],
    rate_limiter: Annotated[RateLimiterService, Depends(get_rate_limiter)],
    user_id: str,
    trace_id: str | None = None,
) -> None:
    """Check rate limit for the request."""
    await rate_limiter.check_rate_limit(
        user_id=user_id,
        api_key_hash=api_key_hash if api_key_hash != "dev-mode" else None,
        trace_id=trace_id,
    )


# Export commonly used dependencies
__all__ = [
    "get_database",
    "get_cache_service",
    "get_rate_limiter",
    "get_llm_factory",
    "get_metrics_collector",
    "get_circuit_breaker",
    "get_chat_repository",
    "get_llm_service",
    "get_chat_orchestrator",
    "verify_api_key",
    "check_rate_limit_dependency",
]