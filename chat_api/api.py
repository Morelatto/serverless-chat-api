"""FastAPI application - All routes and middleware in one place (Python 2025 style)."""

import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .chat import ChatMessage, ChatResponse, ChatService
from .config import settings
from .exceptions import ChatAPIError, LLMProviderError, StorageError, ValidationError
from .middleware import add_request_id
from .providers import create_llm_provider
from .storage import create_cache, create_repository
from .types import MessageRecord

# Configure loguru
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level,
    serialize=False,
)
if settings.log_file:
    logger.add(
        settings.log_file,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        level=settings.log_level,
    )

# Rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url or "memory://",
    default_limits=[settings.rate_limit],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Create dependencies
    repository = create_repository(settings.database_url)
    cache = create_cache(settings.redis_url)

    # Create LLM provider
    api_key = (
        settings.gemini_api_key
        if settings.llm_provider == "gemini"
        else settings.openrouter_api_key
    )
    llm_provider = create_llm_provider(
        provider_type=settings.llm_provider,
        model=settings.llm_model,
        api_key=api_key,
    )

    # Initialize resources
    await repository.startup()
    await cache.startup()

    # Create service and store in app.state
    app.state.chat_service = ChatService(repository, cache, llm_provider)

    logger.info("Application started successfully")
    yield

    # Cleanup
    await repository.shutdown()
    await cache.shutdown()
    logger.info("Application shutdown complete")


# Create app
app = FastAPI(
    title="Chat API",
    version="1.0.0",
    description="A simple LLM chat service with Pythonic design",
    lifespan=lifespan,
)

# Add middleware
app.middleware("http")(add_request_id)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Validation error handler
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle validation errors with clean messages."""
    error_messages = []

    for error in exc.errors():  # type: ignore[attr-defined]
        field = error["loc"][-1] if error["loc"] else "field"
        message = error.get("msg", f"Invalid {field}")

        match error["type"]:
            case "missing":
                message = f"Required field '{field}' is missing"
            case "json_invalid":
                message = "Invalid JSON format"

        error_messages.append(message)

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Validation failed",
            "message": "; ".join(error_messages),
            "details": error_messages,
        },
    )


app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]


@app.exception_handler(ChatAPIError)
async def chat_api_exception_handler(request: Request, exc: ChatAPIError) -> JSONResponse:
    """Handle domain-specific errors."""
    logger.error(f"Chat API error: {exc}")

    # Map exception types to status codes
    status_map = {
        LLMProviderError: 503,
        StorageError: 503,
        ValidationError: 400,
    }

    status_code = 500
    for exc_type, code in status_map.items():
        if isinstance(exc, exc_type):
            status_code = code
            break

    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc), "type": exc.__class__.__name__},
    )


# ============== Routes ==============
# ============== Dependencies ==============
async def get_chat_service(request: Request) -> ChatService:
    """Get chat service from app state."""
    service: ChatService = request.app.state.chat_service
    return service


# ============== Routes ==============
@app.post("/chat", tags=["chat"])
@limiter.limit(settings.rate_limit)
async def chat_endpoint(
    request: Request,
    message: ChatMessage,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """Process a chat message."""
    try:
        result = await service.process_message(message.user_id, message.content)

        return ChatResponse(
            id=result["id"],
            content=result["content"],
            timestamp=datetime.now(UTC),
            cached=result.get("cached", False),
            model=result.get("model"),
        )
    except LLMProviderError as e:
        logger.error(f"LLM provider error: {e}")
        raise HTTPException(status_code=503, detail=f"Service temporarily unavailable: {e}") from e
    except StorageError as e:
        logger.error(f"Storage error: {e}")
        raise HTTPException(status_code=503, detail=f"Storage error: {e}") from e
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Unexpected error in chat handler: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/history/{user_id}", tags=["chat"])
async def history_endpoint(
    response: Response,
    user_id: str,
    limit: int = 10,
    service: ChatService = Depends(get_chat_service),
) -> list[MessageRecord]:
    """Retrieve chat history for a user."""
    if limit > 100:
        raise HTTPException(400, "Limit cannot exceed 100")

    return await service.get_history(user_id, limit)


@app.get("/health", tags=["health"])
async def health_endpoint(
    response: Response,
    service: ChatService = Depends(get_chat_service),
) -> dict[str, Any]:
    """Check health status of all components."""
    status = await service.health_check()
    all_healthy = all(status.values())

    # Set status code based on health
    if not all_healthy:
        response.status_code = 503

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "services": status,
    }


@app.get("/health/detailed", tags=["health"])
async def detailed_health_endpoint(
    service: ChatService = Depends(get_chat_service),
) -> dict[str, Any]:
    """Get detailed health information."""
    status = await service.health_check()

    return {
        "status": "healthy" if all(status.values()) else "unhealthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "services": status,
        "version": "1.0.0",
        "environment": {
            "llm_provider": settings.llm_provider,
            "rate_limit": settings.rate_limit,
        },
    }


@app.get("/", tags=["health"])
async def root_endpoint(response: Response) -> dict[str, str]:
    """API information endpoint."""
    return {
        "name": "Chat API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


# OpenAPI customization
app.openapi_tags = [
    {"name": "chat", "description": "Chat operations"},
    {"name": "health", "description": "Health checks"},
]


# Export for use in other modules
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    return app
