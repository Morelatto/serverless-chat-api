"""Retry logic for the Chat API using stamina."""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import stamina
from loguru import logger

from .exceptions import LLMProviderError

F = TypeVar("F", bound=Callable[..., Any])


def with_llm_retry(
    provider_name: str,
    max_retries: int = 3,
    min_wait: int = 1,
    max_wait: int = 10,
) -> Callable[[F], F]:
    """Decorator to add retry logic to LLM provider methods using stamina.

    Args:
        provider_name: Name of the provider for error messages
        max_retries: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorated function with retry logic

    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Configure stamina for this specific call
            retrying = stamina.retry_context(
                on=(TimeoutError, ConnectionError, LLMProviderError),
                attempts=max_retries,
                wait_initial=min_wait,
                wait_max=max_wait,
                wait_jitter=True,  # Add jitter to prevent thundering herd
            )

            async for attempt in retrying:
                with attempt:
                    try:
                        return await func(*args, **kwargs)
                    except TimeoutError as e:
                        logger.warning(f"{provider_name} attempt {attempt.num}: Timeout - {e}")
                        if attempt.num == max_retries:
                            raise LLMProviderError(f"{provider_name} request timed out") from e
                        raise
                    except ConnectionError as e:
                        logger.warning(
                            f"{provider_name} attempt {attempt.num}: Connection failed - {e}"
                        )
                        if attempt.num == max_retries:
                            raise LLMProviderError(
                                f"Failed to connect to {provider_name} API"
                            ) from e
                        raise
                    except Exception as e:
                        logger.error(f"{provider_name} attempt {attempt.num}: Failed - {e}")
                        if attempt.num == max_retries:
                            raise LLMProviderError(f"{provider_name} API error: {e}") from e
                        raise

            # This should never be reached due to stamina's retry_context behavior
            # but ruff requires an explicit return or raise
            raise LLMProviderError(f"{provider_name} retry logic failed unexpectedly")

        return wrapper  # type: ignore[return-value,no-any-return]

    return decorator
