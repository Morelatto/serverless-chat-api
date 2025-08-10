"""Request tracking middleware."""

import uuid

from fastapi import Request
from loguru import logger


async def add_request_id(request: Request, call_next):
    """Add request ID to context for tracking.

    Args:
        request: Incoming FastAPI request.
        call_next: Next middleware or handler in chain.

    Returns:
        Response with X-Request-ID header.

    """
    # Generate or use existing request ID
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # Add to request state for access in handlers
    request.state.request_id = request_id

    # Add context for structured logging
    with logger.contextualize(request_id=request_id):
        logger.debug(
            "Request started",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        logger.debug(
            "Request completed",
            status_code=response.status_code,
        )

        return response
