"""FastAPI application and route handlers."""

import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .chat import ChatResponse, ChatService
from .config import settings
from .exceptions import ChatAPIError, LLMProviderError, StorageError, ValidationError
from .middleware import add_request_id, create_token, get_current_user
from .providers import create_llm_provider
from .storage import create_cache, create_repository
from .types import MessageRecord

_chat_service: ChatService | None = None


def configure_logging() -> None:
    """Configure logging - should be called at startup, not import time."""
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


def get_limiter() -> Limiter:
    """Get or create rate limiter."""
    return Limiter(
        key_func=get_remote_address,
        storage_uri=settings.redis_url or "memory://",
        default_limits=[settings.rate_limit],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global _chat_service
    configure_logging()

    # Create service components
    repository = create_repository()
    cache = create_cache()
    llm_provider = create_llm_provider()

    # Initialize components
    await repository.startup()
    await cache.startup()

    # Create service
    _chat_service = ChatService(
        repository=repository,
        cache=cache,
        llm_provider=llm_provider,
    )

    logger.info("Application started successfully")

    yield

    # Shutdown components
    await repository.shutdown()
    await cache.shutdown()
    _chat_service = None
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Chat API",
    version="1.0.0",
    description="A simple LLM chat service with Pythonic design",
    lifespan=lifespan,
)

app.middleware("http")(add_request_id)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = get_limiter()
app.state.limiter = limiter  # Required by slowapi
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


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

    if isinstance(exc, ValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, LLMProviderError | StorageError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc), "type": exc.__class__.__name__},
    )


def get_chat_service() -> ChatService:
    """Get chat service singleton."""
    if _chat_service is None:
        raise RuntimeError("Service not initialized")
    return _chat_service


@app.post("/chat", tags=["chat"])
@limiter.limit(settings.rate_limit)
async def chat_endpoint(
    request: Request,
    service: Annotated[ChatService, Depends(get_chat_service)],
    content: str = Body(..., min_length=1, max_length=10000),
    user_id: str = Depends(get_current_user),
) -> ChatResponse:
    """Process a chat message."""
    try:
        result = await service.process_message(user_id, content)

        return ChatResponse(
            id=result["id"],
            content=result["content"],
            timestamp=datetime.now(UTC),
            cached=result.get("cached", False),
            model=result.get("model"),
        )
    except LLMProviderError as e:
        logger.error(f"LLM provider error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable",
            headers={
                "X-Request-ID": request.state.request_id
                if hasattr(request.state, "request_id")
                else ""
            },
        ) from e
    except StorageError as e:
        logger.error(f"Storage error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Storage service unavailable",
            headers={
                "X-Request-ID": request.state.request_id
                if hasattr(request.state, "request_id")
                else ""
            },
        ) from e
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Unexpected error in chat handler: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
            headers={
                "X-Request-ID": request.state.request_id
                if hasattr(request.state, "request_id")
                else ""
            },
        ) from e


@app.get("/history/{user_id}", tags=["chat"])
async def history_endpoint(
    request: Request,
    response: Response,
    user_id: str,
    service: Annotated[ChatService, Depends(get_chat_service)],
    limit: int = Query(10, ge=1, le=100),
) -> list[MessageRecord]:
    """Retrieve chat history for a user."""
    # Basic validation for path parameter
    if not user_id or len(user_id) > 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID",
            headers={"X-Request-ID": getattr(request.state, "request_id", "")},
        )

    return await service.get_history(user_id, limit)


@app.get("/health", tags=["health"])
async def health_endpoint(
    response: Response,
    service: Annotated[ChatService, Depends(get_chat_service)],
    detailed: bool = Query(False, description="Include detailed environment information"),
) -> dict[str, Any]:
    """Check health status of all components.

    Args:
        detailed: If True, includes version and environment information.

    """
    status = await service.health_check()
    all_healthy = all(status.values())

    if not all_healthy:
        response.status_code = 503

    result: dict[str, Any] = {
        "status": "healthy" if all_healthy else "unhealthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "services": status,
    }

    if detailed:
        result["version"] = "1.0.0"
        result["environment"] = {
            "llm_provider": settings.llm_provider,
            "rate_limit": settings.rate_limit,
        }

    return result


@app.get("/", tags=["health"])
async def root_endpoint(response: Response) -> dict[str, str]:
    """API information endpoint."""
    return {
        "name": "Chat API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.post("/login", tags=["auth"])
async def login_endpoint(user_id: str = Body(..., min_length=3, max_length=100)) -> dict[str, str]:
    """Demo login endpoint for testing JWT.

    Args:
        user_id: User identifier to generate token for.

    Returns:
        Dictionary with access_token and token_type.
    """
    token = create_token(user_id)
    return {"access_token": token, "token_type": "bearer"}


app.openapi_tags = [
    {"name": "chat", "description": "Chat operations"},
    {"name": "health", "description": "Health checks"},
    {"name": "auth", "description": "Authentication"},
]


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    return app
