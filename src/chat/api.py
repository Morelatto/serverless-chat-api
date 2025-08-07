"""Chat API endpoints with security and observability."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from src.chat.models import ChatRequest, ChatResponse, HealthResponse
from src.chat.service import ChatService
from src.shared.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["chat"])

# Rate limiting with automatic cleanup
class RateLimitStorage:
    """Rate limit storage with periodic cleanup to prevent memory leaks."""

    def __init__(self, cleanup_interval_hours: int = 1):
        self.storage: dict[str, list[datetime]] = {}
        self.cleanup_interval = timedelta(hours=cleanup_interval_hours)
        self.last_cleanup = datetime.now(timezone.utc)

    def add_request(self, user_key: str, timestamp: datetime) -> None:
        """Add a request timestamp for a user."""
        if user_key not in self.storage:
            self.storage[user_key] = []
        self.storage[user_key].append(timestamp)
        self._cleanup_if_needed()

    def get_requests(self, user_key: str, since: datetime) -> list[datetime]:
        """Get requests for a user since a given time."""
        if user_key not in self.storage:
            return []
        # Clean while retrieving
        self.storage[user_key] = [t for t in self.storage[user_key] if t > since]
        return self.storage[user_key]

    def _cleanup_if_needed(self) -> None:
        """Cleanup old entries periodically."""
        current_time = datetime.now(timezone.utc)
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries()
            self.last_cleanup = current_time

    def _cleanup_old_entries(self) -> None:
        """Remove expired entries from storage."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        keys_before = len(self.storage)

        for user_key in list(self.storage.keys()):
            self.storage[user_key] = [
                t for t in self.storage[user_key] if t > cutoff
            ]
            if not self.storage[user_key]:
                del self.storage[user_key]

        if keys_before != len(self.storage):
            logger.info(f"Cleaned rate limit storage: {keys_before} -> {len(self.storage)} keys")

rate_limit_storage = RateLimitStorage()


async def verify_api_key(x_api_key: str | None = Header(None)) -> str:
    """Verify API key."""
    if not settings.REQUIRE_API_KEY:
        return "dev-mode"

    if not x_api_key:
        raise HTTPException(status_code=401, detail="API Key required")

    valid_keys = settings.API_KEYS.split(",") if settings.API_KEYS else []
    if x_api_key not in valid_keys:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    return hashlib.sha256(x_api_key.encode()).hexdigest()[:8]


async def check_rate_limit(request: ChatRequest, api_key_hash: str) -> None:
    """Rate limiting per user with automatic cleanup."""
    user_key = f"{request.userId}:{api_key_hash}"
    current_time = datetime.now(timezone.utc)
    minute_ago = current_time - timedelta(minutes=1)
    
    # Get recent requests for this user
    recent_requests = rate_limit_storage.get_requests(user_key, minute_ago)
    
    # Check limit
    if len(recent_requests) >= settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Add current request
    rate_limit_storage.add_request(user_key, current_time)


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(  # type: ignore[no-untyped-def]
    request: ChatRequest, req: Request, api_key_hash: str = Depends(verify_api_key)
):
    """Process chat prompt and return LLM response."""
    trace_id = req.headers.get("X-Trace-Id", str(uuid4()))

    logger.info(
        {
            "event": "chat_request",
            "trace_id": trace_id,
            "user_id": request.userId,
            "prompt_length": len(request.prompt),
            "api_key_hash": api_key_hash,
        }
    )

    # Rate limiting
    await check_rate_limit(request, api_key_hash)

    # Process request
    service = ChatService()
    try:
        result = await service.process_prompt(
            user_id=request.userId, prompt=request.prompt, trace_id=trace_id
        )

        response = ChatResponse(
            id=result["interaction_id"],
            userId=request.userId,
            prompt=request.prompt,
            response=result["response"],
            model=result["model"],
            timestamp=result["timestamp"],
            cached=result.get("cached", False),
        )

        logger.info(
            {
                "event": "chat_success",
                "trace_id": trace_id,
                "interaction_id": result["interaction_id"],
                "latency_ms": result.get("latency_ms", 0),
            }
        )

        return response

    except Exception as e:
        logger.error({"event": "chat_error", "trace_id": trace_id, "error": str(e)})
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy", timestamp=datetime.now(timezone.utc).isoformat())


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    """Readiness check with dependencies."""
    service = ChatService()
    checks = await service.check_dependencies()

    all_ready = all(checks.values())
    status_code = 200 if all_ready else 503

    return JSONResponse(
        content={"ready": all_ready, "checks": checks, "timestamp": datetime.now(timezone.utc).isoformat()},
        status_code=status_code,
    )


# /history/{user_id}
# /v1/metrics
# /v1/models
# /v1/session/*
# endpoints for conversation context
