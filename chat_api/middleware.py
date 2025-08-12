"""Request tracking middleware and JWT authentication."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Header, HTTPException, Request, status
from jose import JWTError, jwt
from loguru import logger

from .config import settings


async def add_request_id(request: Request, call_next):
    """Add request ID to context for tracking.

    Args:
        request: Incoming FastAPI request.
        call_next: Next middleware or handler in chain.

    Returns:
        Response with X-Request-ID header.

    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    with logger.contextualize(request_id=request_id):
        logger.debug(
            "Request started",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        logger.debug(
            "Request completed",
            status_code=response.status_code,
        )

        return response


def create_token(user_id: str) -> str:
    """Create a JWT token for a user.

    Args:
        user_id: The user identifier to encode in the token.

    Returns:
        Encoded JWT token as string.
    """
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_expiration_minutes)
    payload = {
        "sub": user_id,
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }
    token: str = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token


async def get_current_user(authorization: str = Header()) -> str:
    """Extract and validate user_id from JWT token.

    Args:
        authorization: Authorization header value (Bearer token).

    Returns:
        User ID extracted from valid token.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Extract token from Bearer scheme
        if not authorization.startswith("Bearer "):
            raise credentials_exception

        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")

        if user_id is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception from e
    else:
        return user_id
