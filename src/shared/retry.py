"""Reusable retry decorator with exponential backoff and jitter."""

import asyncio
import functools
import logging
import random
from typing import Any, Callable, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    log_retries: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Add random jitter to delays to prevent thundering herd
        exceptions: Tuple of exception types to retry on
        log_retries: Whether to log retry attempts
        
    Returns:
        Decorated function with retry logic
        
    Example:
        @retry_with_backoff(max_attempts=3, exceptions=(ConnectionError,))
        def fetch_data():
            # Code that might fail
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            """Wrapper for synchronous functions."""
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        # Last attempt failed, re-raise
                        if log_retries:
                            logger.error(
                                f"{func.__name__} failed after {max_attempts} attempts: {e}"
                            )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    # Add jitter if enabled
                    if jitter:
                        delay *= (0.5 + random.random())
                    
                    if log_retries:
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1}/{max_attempts} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                    
                    import time
                    time.sleep(delay)
            
            # Should never reach here, but for type safety
            if last_exception:
                raise last_exception
            return func(*args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            """Wrapper for asynchronous functions."""
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        # Last attempt failed, re-raise
                        if log_retries:
                            logger.error(
                                f"{func.__name__} failed after {max_attempts} attempts: {e}"
                            )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    # Add jitter if enabled
                    if jitter:
                        delay *= (0.5 + random.random())
                    
                    if log_retries:
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1}/{max_attempts} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                    
                    await asyncio.sleep(delay)
            
            # Should never reach here, but for type safety
            if last_exception:
                raise last_exception
            return await func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Convenience decorators with common configurations

def retry_on_network_error(func: Callable[..., T]) -> Callable[..., T]:
    """Retry decorator specifically for network-related errors.
    
    Retries on ConnectionError, TimeoutError, and OSError.
    """
    return retry_with_backoff(
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0,
        exceptions=(ConnectionError, TimeoutError, OSError),
    )(func)


def retry_on_db_error(func: Callable[..., T]) -> Callable[..., T]:
    """Retry decorator specifically for database errors.
    
    Retries on database lock and operational errors.
    """
    import sqlite3
    
    return retry_with_backoff(
        max_attempts=5,
        base_delay=0.1,
        max_delay=2.0,
        exceptions=(sqlite3.OperationalError, sqlite3.DatabaseError),
        jitter=True,
    )(func)


def retry_critical(func: Callable[..., T]) -> Callable[..., T]:
    """Retry decorator for critical operations.
    
    More aggressive retry strategy for critical operations.
    """
    return retry_with_backoff(
        max_attempts=5,
        base_delay=0.5,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True,
    )(func)


class RetryContext:
    """Context manager for manual retry logic when decorator isn't suitable."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        exceptions: tuple[Type[Exception], ...] = (Exception,),
    ):
        """Initialize retry context.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Initial delay between retries
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to delays
            exceptions: Exception types to retry on
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.exceptions = exceptions
        self.attempt = 0
    
    async def execute(self, coro: Any) -> Any:
        """Execute coroutine with retry logic.
        
        Args:
            coro: Coroutine to execute
            
        Returns:
            Result from coroutine
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for self.attempt in range(self.max_attempts):
            try:
                return await coro
            except self.exceptions as e:
                last_exception = e
                
                if self.attempt == self.max_attempts - 1:
                    raise
                
                # Calculate delay
                delay = min(
                    self.base_delay * (self.exponential_base ** self.attempt),
                    self.max_delay
                )
                
                if self.jitter:
                    delay *= (0.5 + random.random())
                
                logger.warning(
                    f"Attempt {self.attempt + 1}/{self.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                
                await asyncio.sleep(delay)
        
        if last_exception:
            raise last_exception