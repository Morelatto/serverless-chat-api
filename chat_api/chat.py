"""Chat service - Core business logic and models (Python 2025 style)."""

import time
import uuid
from datetime import datetime
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from .exceptions import LLMProviderError, StorageError
from .providers import LLMProvider
from .storage import Cache, Repository, cache_key


# ============== Models ==============
class ChatMessage(BaseModel):
    """Input message from user."""

    user_id: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=4000)

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id(cls, value: str) -> str:
        if not value or not value.strip():
            msg = "empty_user_id"
            raise PydanticCustomError(msg, "User ID cannot be empty", {"input": value})
        if len(value.strip()) > 100:
            msg = "user_id_too_long"
            raise PydanticCustomError(
                msg,
                "User ID is too long (max 100 characters)",
                {"length": len(value), "max_length": 100},
            )
        return value.strip()

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not value or not value.strip():
            msg = "empty_content"
            raise PydanticCustomError(
                msg,
                "Message content cannot be empty",
                {"input": value},
            )
        if len(value.strip()) > 4000:
            msg = "content_too_long"
            raise PydanticCustomError(
                msg,
                "Message is too long (max 4000 characters)",
                {"length": len(value), "max_length": 4000},
            )
        return value.strip()


class ChatResponse(BaseModel):
    """Response from the API."""

    id: str
    content: str
    timestamp: datetime
    cached: bool = False
    model: str | None = None


# ============== Core Service ==============
class ChatService:
    """Chat service handling message processing with injected dependencies."""

    def __init__(
        self,
        repository: Repository,
        cache: Cache,
        llm_provider: LLMProvider,
    ) -> None:
        """Initialize chat service with dependencies.

        Args:
            repository: Storage repository for persistence.
            cache: Cache instance for response caching.
            llm_provider: LLM provider for generating responses.

        """
        self.repository = repository
        self.cache = cache
        self.llm_provider = llm_provider
        self._last_health_check: dict[str, Any] | None = None
        self._health_check_timestamp: float = 0

    async def process_message(
        self,
        user_id: str,
        content: str,
    ) -> dict[str, Any]:
        """Process a chat message.

        Args:
            user_id: User identifier.
            content: Message content to process.

        Returns:
            Dictionary with message ID, response content, model, and cache status.

        """
        # Check cache
        key = cache_key(user_id, content)
        cached = await self.cache.get(key)
        if cached:
            logger.debug(f"Cache hit for user {user_id[:8]}")
            cached["cached"] = True
            return cached

        logger.debug(f"Cache miss for user {user_id[:8]}")

        # Generate response
        try:
            llm_response = await self.llm_provider.complete(content)
        except LLMProviderError:
            # Re-raise known provider errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error during LLM completion: {e}")
            raise LLMProviderError(f"Failed to generate response: {e}") from e

        # Save to database with usage tracking
        message_id = str(uuid.uuid4())
        try:
            await self.repository.save(
                id=message_id,
                user_id=user_id,
                content=content,
                response=llm_response.text,
                model=llm_response.model,
                usage=llm_response.usage,
            )
        except Exception as e:
            logger.error(f"Failed to save message {message_id}: {e}")
            raise StorageError(f"Failed to save chat message: {e}") from e

        # Log token usage for monitoring (structured logging for modern observability tools)
        if llm_response.usage:
            logger.info(
                "Token usage",
                user_id=user_id,
                model=llm_response.model,
                **llm_response.usage,
            )

        # Prepare response
        result = {
            "id": message_id,
            "content": llm_response.text,
            "model": llm_response.model,
            "cached": False,
        }

        # Cache it
        await self.cache.set(key, result)

        return result

    async def get_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get chat history for a user.

        Args:
            user_id: User identifier.
            limit: Maximum number of messages to return.

        Returns:
            List of message dictionaries.

        """
        return await self.repository.get_history(user_id, limit)

    async def health_check(self) -> dict[str, bool]:
        """Check health of all system components with caching.

        Returns:
            Dictionary with health status of each component.

        """
        # Return cached result if less than 30 seconds old
        current_time = time.time()
        if self._last_health_check is not None and current_time - self._health_check_timestamp < 30:
            logger.debug("Returning cached health check result")
            return self._last_health_check

        # Perform actual health checks
        logger.debug("Performing health checks")
        storage_ok = await self.repository.health_check()

        llm_ok = False
        try:
            llm_ok = await self.llm_provider.health_check()
            logger.debug(f"LLM health check: ok={llm_ok}")
        except (LLMProviderError, ValueError, ConnectionError, TimeoutError, Exception) as e:
            logger.warning("LLM health check failed: {}", e)
            llm_ok = False

        result = {"storage": storage_ok, "llm": llm_ok}

        # Cache the result
        self._last_health_check = result
        self._health_check_timestamp = current_time

        return result


# ============== Standalone Functions (for backward compatibility) ==============
async def process_message_with_deps(
    user_id: str,
    content: str,
    repository: Repository,
    cache: Cache,
    llm_provider: LLMProvider,
) -> dict[str, Any]:
    """Process a chat message with injected dependencies (backward compatibility).

    Args:
        user_id: User identifier.
        content: Message content to process.
        repository: Repository instance for persistence.
        cache: Cache instance for caching.
        llm_provider: LLM provider instance.

    Returns:
        Dictionary with message ID, response content, model, and cache status.

    """
    service = ChatService(repository, cache, llm_provider)
    return await service.process_message(user_id, content)


async def health_check(
    repository: Repository,
    llm_provider: LLMProvider,
) -> dict[str, bool]:
    """Check health of all systems (backward compatibility).

    Args:
        repository: Repository instance to check.
        llm_provider: LLM provider instance.

    Returns:
        Dictionary with health status of each component.

    """
    # Dummy cache for health check
    from .storage import InMemoryCache

    cache = InMemoryCache()

    service = ChatService(repository, cache, llm_provider)
    return await service.health_check()
