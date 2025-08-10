"""Shared retry logic for the Chat API."""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .exceptions import LLMProviderError

F = TypeVar("F", bound=Callable[..., Any])


def with_llm_retry(
    provider_name: str,
    max_retries: int = 3,
    min_wait: int = 1,
    max_wait: int = 10,
) -> Callable[[F], F]:
    """Decorator to add retry logic to LLM provider methods.

    Args:
        provider_name: Name of the provider for error messages
        max_retries: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorated function with retry logic

    """

    def decorator(func: F) -> F:
        retry_decorator = retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(min=min_wait, max=max_wait),
        )

        @retry_decorator
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except TimeoutError as e:
                logger.error(f"{provider_name} call timed out: {e}")
                raise LLMProviderError(f"{provider_name} request timed out") from e
            except ConnectionError as e:
                logger.error(f"{provider_name} connection failed: {e}")
                raise LLMProviderError(f"Failed to connect to {provider_name} API") from e
            except Exception as e:
                logger.error(f"{provider_name} call failed: {e}")
                raise LLMProviderError(f"{provider_name} API error: {e}") from e

        return wrapper  # type: ignore[return-value,no-any-return]

    return decorator
