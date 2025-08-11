"""Chat service core business logic and models."""

import re
import uuid
from datetime import datetime
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from .exceptions import LLMProviderError, StorageError, ValidationError
from .providers import LLMProvider
from .storage import Cache, Repository, cache_key
from .types import ChatResult, HealthStatus, MessageRecord


def sanitize_user_id(user_id: str) -> str:
    """Sanitize user ID for safe storage and logging."""
    if not user_id or not user_id.strip():
        raise ValidationError("User ID cannot be empty")

    user_id = user_id.strip()
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "", user_id)

    if not sanitized:
        raise ValidationError("User ID contains no valid characters")

    if len(sanitized) < 3:
        raise ValidationError("User ID must be at least 3 characters")

    return sanitized[:100]


def sanitize_content(content: str) -> str:
    """Sanitize and validate message content."""
    if not content or not content.strip():
        raise ValidationError("Message content cannot be empty")

    content = content.strip()

    if len(content) > 10000:
        raise ValidationError("Message content exceeds maximum length (10000 characters)")

    suspicious_patterns = [
        (r"<script", "Script tags not allowed"),
        (r"javascript:", "JavaScript URLs not allowed"),
        (r"data:text/html", "Data URLs not allowed"),
        (r"\x00", "Null bytes not allowed"),
    ]

    for pattern, message in suspicious_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            logger.warning(f"Suspicious pattern detected: {pattern}")
            raise ValidationError(message)

    return content


class ChatMessage(BaseModel):
    """Input message from user."""

    user_id: str = Field(..., min_length=3, max_length=100)
    content: str = Field(..., min_length=1, max_length=10000)

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id(cls, value: str) -> str:
        """Validate and sanitize user ID."""
        if not value or not value.strip():
            raise PydanticCustomError("empty_user_id", "User ID cannot be empty", {"input": value})
        return sanitize_user_id(value.strip())

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, value: str) -> str:
        """Validate and sanitize content."""
        if not value or not value.strip():
            raise PydanticCustomError(
                "empty_content", "Message content cannot be empty", {"input": value}
            )
        return sanitize_content(value)


class ChatResponse(BaseModel):
    """Response from the API."""

    id: str
    content: str
    timestamp: datetime
    cached: bool = False
    model: str | None = None


class ChatService:
    """Chat service handling message processing."""

    def __init__(
        self,
        repository: Repository,
        cache: Cache,
        llm_provider: LLMProvider,
    ) -> None:
        """Initialize with injected dependencies."""
        self.repository = repository
        self.cache = cache
        self.llm_provider = llm_provider

    async def process_message(
        self,
        user_id: str,
        content: str,
    ) -> ChatResult:
        """Process a chat message with caching and persistence."""

        safe_user_id = user_id[:8] + "..." if len(user_id) > 8 else user_id
        logger.debug("Processing message", extra={"user_id": safe_user_id})

        key = cache_key(user_id, content)
        cached = await self._try_cache_get(key)
        if cached:
            logger.debug("Cache hit", extra={"user_id": safe_user_id})
            cached["cached"] = True
            return cached  # type: ignore

        logger.debug("Cache miss", extra={"user_id": safe_user_id})

        try:
            llm_response = await self.llm_provider.complete(content)
        except LLMProviderError:
            raise
        except Exception as e:
            logger.error(f"Unexpected LLM error: {e}", extra={"user_id": safe_user_id})
            raise LLMProviderError(f"Failed to generate response: {e}") from e

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
            logger.error(
                "Failed to save message",
                extra={"message_id": message_id, "user_id": safe_user_id, "error": str(e)},
            )
            raise StorageError(f"Failed to save message: {e}") from e

        if llm_response.usage:
            logger.info(
                "Token usage",
                extra={
                    "user_id": safe_user_id,
                    "model": llm_response.model,
                    "prompt_tokens": llm_response.usage.get("prompt_tokens"),
                    "completion_tokens": llm_response.usage.get("completion_tokens"),
                    "total_tokens": llm_response.usage.get("total_tokens"),
                },
            )

        result: ChatResult = {
            "id": message_id,
            "content": llm_response.text,
            "model": llm_response.model,
            "cached": False,
            "usage": llm_response.usage,
        }

        await self._try_cache_set(key, dict(result))

        return result

    async def get_history(self, user_id: str, limit: int = 10) -> list[MessageRecord]:
        """Retrieve chat history for a user."""
        return await self.repository.get_history(user_id, limit)

    async def health_check(self) -> HealthStatus:
        """Check health of all components."""
        logger.debug("Performing health checks")

        storage_ok = await self._check_storage_health()
        llm_ok = await self._check_llm_health()
        cache_ok = await self._check_cache_health()

        return {
            "storage": storage_ok,
            "llm": llm_ok,
            "cache": cache_ok,
        }

    async def _try_cache_get(self, key: str) -> dict[str, Any] | None:
        """Try to get from cache with graceful fallback."""
        try:
            return await self.cache.get(key)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Cache get failed (non-critical): {e}")
            return None

    async def _try_cache_set(self, key: str, value: dict[str, Any]) -> None:
        """Try to set cache with graceful fallback."""
        try:
            cache_data = {k: v for k, v in value.items() if k != "usage"}
            await self.cache.set(key, cache_data)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Cache set failed (non-critical): {e}")

    async def _check_storage_health(self) -> bool:
        """Check storage health."""
        try:
            return await self.repository.health_check()
        except Exception as e:  # noqa: BLE001
            logger.error(f"Storage health check failed: {e}")
            return False

    async def _check_llm_health(self) -> bool:
        """Check LLM provider health."""
        try:
            return await self.llm_provider.health_check()
        except Exception as e:  # noqa: BLE001
            logger.error(f"LLM health check failed: {e}")
            return False

    async def _check_cache_health(self) -> bool:
        """Check cache health."""
        try:
            test_key = "__health_check__"
            await self.cache.set(test_key, {"test": True}, ttl=1)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Cache health check failed: {e}")
            return False
        else:
            return True
