"""
Main entry point for both FastAPI local development and AWS Lambda deployment.
Handles application initialization and request routing.
"""
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum

from src.chat.api import router as chat_router
from src.shared.config import settings

# Configure logging
logger = logging.getLogger(__name__)


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    # Startup
    logger.info({
        "event": "application_startup",
        "environment": "lambda" if settings.AWS_LAMBDA_FUNCTION_NAME else "local",
        "settings": settings.to_dict()
    })
    yield
    # Shutdown
    logger.info("Application shutting down")


# Create FastAPI application
app = FastAPI(
    title="Chat API - Itaú AI Platform",
    description="Microservice for processing prompts with LLM integration",
    version="1.0.0",
    docs_url="/docs" if not settings.AWS_LAMBDA_FUNCTION_NAME else None,
    redoc_url="/redoc" if not settings.AWS_LAMBDA_FUNCTION_NAME else None,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions gracefully."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.LOG_LEVEL == "DEBUG" else "An unexpected error occurred",
            "trace_id": request.headers.get("X-Trace-Id", "unknown")
        }
    )


# Root endpoint
@app.get("/")
async def root() -> dict[str, str | None]:
    """Root endpoint with API information."""
    return {
        "name": "Chat API",
        "version": "1.0.0",
        "status": "running",
        "environment": "lambda" if settings.AWS_LAMBDA_FUNCTION_NAME else "local",
        "docs": "/docs" if not settings.AWS_LAMBDA_FUNCTION_NAME else "disabled in production"
    }


# Include chat routes
app.include_router(chat_router)


# Lambda handler for AWS deployment
handler = Mangum(app, lifespan="off")


def run() -> None:
    """Run the application locally with uvicorn."""
    import uvicorn

    logger.info(f"Starting local server on {settings.API_HOST}:{settings.API_PORT}")

    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )


# Local development server
if __name__ == "__main__":
    run()
