"""HTTP request handlers."""

from datetime import UTC, datetime

from fastapi import HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings
from .core import health_check as core_health
from .core import process_message
from .models import ChatMessage, ChatResponse

# Rate limiter - explicit backend configuration
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url or "memory://",  # Explicit memory backend when no Redis
    default_limits=[settings.rate_limit],
)


@limiter.limit(settings.rate_limit)
async def chat_handler(request: Request, message: ChatMessage) -> ChatResponse:
    """Handle incoming chat requests.

    Args:
        request: FastAPI request object (used for rate limiting).
        message: Chat message containing user_id and content.

    Returns:
        ChatResponse with generated content and metadata.

    Raises:
        HTTPException: If processing fails.
    """
    try:
        # Get repository and cache from app state
        repository = request.app.state.repository
        cache = request.app.state.cache

        result = await process_message(message.user_id, message.content, repository, cache)

        return ChatResponse(
            id=result["id"],
            content=result["content"],
            timestamp=datetime.now(UTC),
            cached=result.get("cached", False),
            model=result.get("model"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


async def history_handler(request: Request, user_id: str, limit: int = 10) -> list:
    """Retrieve chat history for a user.

    Args:
        request: FastAPI request object for accessing app state.
        user_id: Unique identifier for the user.
        limit: Maximum number of messages to return (max 100).

    Returns:
        List of message dictionaries with content and metadata.

    Raises:
        HTTPException: If limit exceeds 100.
    """
    if limit > 100:
        raise HTTPException(400, "Limit cannot exceed 100")

    # Get repository from app state
    repository = request.app.state.repository
    return await repository.get_history(user_id, limit)


async def health_handler(request: Request) -> dict:
    """Check health status of all system components.

    Args:
        request: FastAPI request object for accessing app state.

    Returns:
        Dictionary containing overall status, timestamp, and individual service statuses.
    """
    # Get repository from app state
    repository = request.app.state.repository

    status = await core_health(repository)
    all_healthy = all(status.values())

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "services": status,
    }
