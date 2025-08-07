"""Refactored Chat API endpoints with dependency injection and better error handling."""

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from src.chat.models import ChatRequest, ChatResponse, HealthResponse
from src.chat.service_refactored import ChatOrchestrator
from src.shared.dependencies import (
    check_rate_limit_dependency,
    get_chat_orchestrator,
    verify_api_key,
)
from src.shared.exceptions import ChatAPIException

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    req: Request,
    orchestrator: Annotated[ChatOrchestrator, Depends(get_chat_orchestrator)],
    api_key_hash: Annotated[str, Depends(verify_api_key)],
    x_trace_id: Annotated[str | None, Header()] = None,
) -> ChatResponse:
    """Process chat prompt and return LLM response with improved error handling."""
    trace_id = x_trace_id or str(uuid4())
    
    logger.info(
        {
            "event": "chat_request_received",
            "trace_id": trace_id,
            "user_id": request.userId,
            "prompt_length": len(request.prompt),
            "api_key_hash": api_key_hash,
        }
    )
    
    try:
        # Check rate limit (this will raise exception if exceeded)
        await check_rate_limit_dependency(
            api_key_hash=api_key_hash,
            rate_limiter=orchestrator.cache_service,  # Injected via dependencies
            user_id=request.userId,
            trace_id=trace_id,
        )
        
        # Process the prompt
        result = await orchestrator.process_prompt(
            user_id=request.userId,
            prompt=request.prompt,
            trace_id=trace_id,
        )
        
        # Create response
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
                "event": "chat_request_success",
                "trace_id": trace_id,
                "interaction_id": result["interaction_id"],
                "model": result["model"],
                "cached": result.get("cached", False),
                "latency_ms": result.get("latency_ms", 0),
            }
        )
        
        return response
        
    except ChatAPIException:
        # Re-raise our custom exceptions (they have proper status codes)
        raise
    except Exception as e:
        # Log unexpected errors and wrap them
        logger.error(
            {
                "event": "chat_request_error",
                "trace_id": trace_id,
                "user_id": request.userId,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise ChatAPIException(
            message="An unexpected error occurred while processing your request",
            status_code=500,
            trace_id=trace_id,
        ) from e


@router.get("/chat/history/{user_id}")
async def get_user_history(
    user_id: str,
    orchestrator: Annotated[ChatOrchestrator, Depends(get_chat_orchestrator)],
    api_key_hash: Annotated[str, Depends(verify_api_key)],
    limit: int = 10,
) -> dict[str, Any]:
    """Get user interaction history."""
    logger.info(
        {
            "event": "history_request",
            "user_id": user_id,
            "limit": limit,
            "api_key_hash": api_key_hash,
        }
    )
    
    try:
        history = await orchestrator.get_user_history(user_id, limit)
        
        return {
            "user_id": user_id,
            "interactions": history,
            "count": len(history),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to get user history: {e}")
        raise ChatAPIException(
            message="Failed to retrieve user history",
            status_code=500,
        ) from e


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(UTC).isoformat(),
        version="2.0.0",  # Updated version
    )


@router.get("/health/detailed")
async def detailed_health_check(
    orchestrator: Annotated[ChatOrchestrator, Depends(get_chat_orchestrator)],
) -> JSONResponse:
    """Detailed health check with all service statuses."""
    try:
        health_status = await orchestrator.check_health()
        
        # Determine overall health
        all_healthy = (
            health_status.get("database", False)
            and health_status.get("llm", False)
            and health_status.get("circuit_breaker", "closed") != "open"
        )
        
        return JSONResponse(
            content={
                "status": "healthy" if all_healthy else "degraded",
                "timestamp": datetime.now(UTC).isoformat(),
                "services": health_status,
                "version": "2.0.0",
            },
            status_code=200 if all_healthy else 503,
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(UTC).isoformat(),
                "error": str(e),
                "version": "2.0.0",
            },
            status_code=503,
        )


@router.get("/metrics")
async def get_metrics(
    orchestrator: Annotated[ChatOrchestrator, Depends(get_chat_orchestrator)],
    api_key_hash: Annotated[str, Depends(verify_api_key)],
) -> dict[str, Any]:
    """Get application metrics."""
    metrics = orchestrator.metrics
    
    # Calculate averages
    avg_latency = (
        metrics.total_latency_ms / metrics.total_requests
        if metrics.total_requests > 0
        else 0
    )
    
    cache_hit_rate = (
        metrics.total_cache_hits / metrics.total_requests
        if metrics.total_requests > 0
        else 0
    )
    
    error_rate = (
        metrics.total_errors / metrics.total_requests
        if metrics.total_requests > 0
        else 0
    )
    
    return {
        "total_requests": metrics.total_requests,
        "total_errors": metrics.total_errors,
        "total_cache_hits": metrics.total_cache_hits,
        "average_latency_ms": round(avg_latency, 2),
        "cache_hit_rate": round(cache_hit_rate, 4),
        "error_rate": round(error_rate, 4),
        "timestamp": datetime.now(UTC).isoformat(),
    }


# Exception handler for our custom exceptions
async def chat_api_exception_handler(
    request: Request, exc: ChatAPIException
) -> JSONResponse:
    """Handle ChatAPIException and return proper response."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )