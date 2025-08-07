"""HTTP request handlers."""
from datetime import UTC, datetime

from fastapi import HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings
from .core import health_check as core_health
from .core import process_message
from .models import ChatMessage, ChatResponse
from .storage import get_user_history

# Rate limiter - explicit backend configuration
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url or "memory://",  # Explicit memory backend when no Redis
    default_limits=[settings.rate_limit]
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
        result = await process_message(message.user_id, message.content)

        return ChatResponse(
            id=result["id"],
            content=result["content"],
            timestamp=datetime.now(UTC),
            cached=result.get("cached", False),
            model=result.get("model")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


async def history_handler(user_id: str, limit: int = 10) -> list:
    """Retrieve chat history for a user.
    
    Args:
        user_id: Unique identifier for the user.
        limit: Maximum number of messages to return (max 100).
        
    Returns:
        List of message dictionaries with content and metadata.
        
    Raises:
        HTTPException: If limit exceeds 100.
    """
    if limit > 100:
        raise HTTPException(400, "Limit cannot exceed 100")

    return await get_user_history(user_id, limit)


async def health_handler() -> dict:
    """Check health status of all system components.
    
    Returns:
        Dictionary containing overall status, timestamp, and individual service statuses.
    """
    status = await core_health()
    all_healthy = all(status.values())

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "services": status
    }
