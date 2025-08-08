"""Middleware for request tracking and monitoring."""

import uuid
from collections.abc import Callable
from typing import cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request ID to all requests for tracking."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with request ID.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or endpoint handler.

        Returns:
            HTTP response with X-Request-ID header.
        """
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state for access in handlers
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return cast("Response", response)


async def add_request_id(request: Request, call_next: Callable) -> Response:
    """Simpler middleware function for request ID tracking.

    Args:
        request: Incoming HTTP request.
        call_next: Next middleware or endpoint handler.

    Returns:
        HTTP response with X-Request-ID header.
    """
    # Get or generate request ID
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # Store in request state
    request.state.request_id = request_id

    # Process request
    response = await call_next(request)

    # Add to response headers
    response.headers["X-Request-ID"] = request_id

    return cast("Response", response)
