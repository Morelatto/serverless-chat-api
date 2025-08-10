"""Chat service - Core business logic and models (Python 2025 style)."""

import uuid
from datetime import datetime

from loguru import logger
from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from .exceptions import LLMProviderError, StorageError
from .providers import LLMProvider
from .storage import Cache, Repository, cache_key
from .types import ChatResult, HealthStatus, MessageRecord

# Constants
USER_ID_LOG_LENGTH = 8  # Characters to show in logs for privacy


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

    async def process_message(
        self,
        user_id: str,
        content: str,
    ) -> ChatResult:
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
            logger.debug(f"Cache hit for user {user_id[:USER_ID_LOG_LENGTH]}")
            cached["cached"] = True
            # Return as ChatResult with usage from cache if available
            cached_result: ChatResult = {
                "id": cached["id"],
                "content": cached["content"],
                "model": cached["model"],
                "cached": True,
                "usage": cached.get("usage", {}),
            }
            return cached_result

        logger.debug(f"Cache miss for user {user_id[:USER_ID_LOG_LENGTH]}")

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
        result: ChatResult = {
            "id": message_id,
            "content": llm_response.text,
            "model": llm_response.model,
            "cached": False,
            "usage": llm_response.usage,
        }

        # Cache it (exclude usage from cache)
        cache_data = {
            "id": message_id,
            "content": llm_response.text,
            "model": llm_response.model,
            "cached": False,
        }
        await self.cache.set(key, cache_data)

        return result

    async def get_history(self, user_id: str, limit: int = 10) -> list[MessageRecord]:
        """Get chat history for a user.

        Args:
            user_id: User identifier.
            limit: Maximum number of messages to return.

        Returns:
            List of message dictionaries.

        """
        return await self.repository.get_history(user_id, limit)  # type: ignore

    async def health_check(self) -> HealthStatus:
        """Check health of all system components.

        Returns:
            Dictionary with health status of each component.

        """
        logger.debug("Performing health checks")
        storage_ok = await self.repository.health_check()

        llm_ok = False
        try:
            llm_ok = await self.llm_provider.health_check()
            logger.debug(f"LLM health check: ok={llm_ok}")
        except Exception as e:  # noqa: BLE001
            logger.warning("LLM health check failed: {}", e)
            llm_ok = False

        result: HealthStatus = {"storage": storage_ok, "llm": llm_ok}
        return result
