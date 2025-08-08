"""FastAPI application."""

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from . import handlers, storage
from .config import settings
from .middleware import add_request_id
from .models import ChatResponse

# Configure loguru
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level,
    serialize=False,  # Use True for JSON logs in production
)
if settings.log_file:
    logger.add(
        settings.log_file,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        level=settings.log_level,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    await storage.startup()
    yield
    await storage.shutdown()


# Create app
app = FastAPI(
    title="Chat API", version="1.0.0", description="A simple LLM chat service", lifespan=lifespan
)

# Add middleware
app.middleware("http")(add_request_id)

# Add rate limiting
app.state.limiter = handlers.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Routes
app.post("/chat", response_model=ChatResponse, tags=["chat"])(handlers.chat_handler)
app.get("/history/{user_id}", tags=["chat"])(handlers.history_handler)
app.get("/health", tags=["health"])(handlers.health_handler)
app.get("/", tags=["health"])(lambda: {"name": "Chat API", "version": "1.0.0", "status": "running"})

# OpenAPI customization
app.openapi_tags = [
    {"name": "chat", "description": "Chat operations"},
    {"name": "health", "description": "Health checks"},
]
