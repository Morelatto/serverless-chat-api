"""Retry logic for the Chat API using tenacity."""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .exceptions import LLMProviderError

F = TypeVar("F", bound=Callable[..., Any])


def with_llm_retry(
    provider_name: str,
    max_retries: int = 3,
) -> Callable[[F], F]:
    """Decorator to add retry logic to LLM provider methods.

    Args:
        provider_name: Name of the provider for error messages
        max_retries: Maximum number of retry attempts

    Returns:
        Decorated function with retry logic

    """

    def decorator(func: F) -> F:
        @retry(
            retry=retry_if_exception_type((TimeoutError, ConnectionError)),
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            before_sleep=lambda retry_state: logger.warning(
                f"{provider_name} attempt {retry_state.attempt_number}: {retry_state.outcome.exception() if retry_state.outcome else 'Unknown error'}",
            ),
        )
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except (TimeoutError, ConnectionError):
                # Tenacity will handle retries
                raise
            except Exception as e:
                logger.error(f"{provider_name} API error: {e}")
                raise LLMProviderError(f"{provider_name} API error: {e}") from e

        return wrapper  # type: ignore[return-value,no-any-return]

    return decorator
