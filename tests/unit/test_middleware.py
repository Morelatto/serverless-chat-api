"""Tests for middleware functionality."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, Request, Response
from jose import jwt

from chat_api.config import settings
from chat_api.middleware import add_request_id, create_token, get_current_user


class TestRequestIDMiddleware:
    """Test request ID middleware."""

    @pytest.mark.asyncio
    async def test_add_request_id_with_existing_header(self):
        """Test middleware preserves existing X-Request-ID header."""
        # Create mock request with existing header
        request = Mock(spec=Request)
        request.headers = Mock()
        request.headers.get = Mock(return_value="existing-id-123")
        request.state = Mock()
        request.method = "GET"
        request.url = Mock(path="/test")
        request.client = None

        # Mock call_next
        async def mock_call_next(req):
            response = Mock(spec=Response)
            response.headers = {}
            response.status_code = 200
            return response

        # Call middleware
        response = await add_request_id(request, mock_call_next)

        # Should preserve existing ID
        assert request.state.request_id == "existing-id-123"
        assert response.headers["X-Request-ID"] == "existing-id-123"

    @pytest.mark.asyncio
    async def test_add_request_id_generates_new_id(self):
        """Test middleware generates new ID when header missing."""
        # Create mock request without header
        from types import SimpleNamespace

        request = Mock(spec=Request)
        # Mock headers.get to make the default value be used
        mock_headers = {}
        request.headers = Mock()
        request.headers.get = lambda key, default=None: mock_headers.get(key, default)

        request.state = SimpleNamespace()
        request.method = "GET"
        request.url = Mock(path="/test")
        request.client = None

        # Mock call_next
        async def mock_call_next(req):
            response = Mock(spec=Response)
            response.headers = {}
            response.status_code = 200
            return response

        # Mock uuid generation - patch uuid.uuid4 directly
        with patch("chat_api.middleware.uuid.uuid4") as mock_uuid4:
            # Create a mock UUID that returns our string when converted to str
            mock_uuid = Mock()
            mock_uuid4.return_value = mock_uuid

            # Patch str() on the returned UUID object
            with patch.object(mock_uuid, "__str__", return_value="generated-uuid-456"):
                # Call middleware
                response = await add_request_id(request, mock_call_next)

                # Should generate new ID
                assert request.state.request_id == "generated-uuid-456"
                assert response.headers["X-Request-ID"] == "generated-uuid-456"

    @pytest.mark.asyncio
    async def test_add_request_id_propagates_to_response(self):
        """Test request ID is propagated to response headers."""
        request = Mock(spec=Request)
        request.headers = Mock()
        request.headers.get = Mock(return_value="test-id-789")
        request.state = Mock()
        request.method = "GET"
        request.url = Mock(path="/test")
        request.client = None

        async def mock_call_next(req):
            # Verify request has ID set
            assert req.state.request_id == "test-id-789"
            response = Mock(spec=Response)
            response.headers = {}
            response.status_code = 200
            return response

        response = await add_request_id(request, mock_call_next)

        # Verify response has the header
        assert response.headers["X-Request-ID"] == "test-id-789"

    @pytest.mark.asyncio
    async def test_add_request_id_handles_exception(self):
        """Test middleware handles exceptions from downstream."""
        from types import SimpleNamespace

        request = Mock(spec=Request)
        # Mock headers.get to make the default value be used
        mock_headers = {}
        request.headers = Mock()
        request.headers.get = lambda key, default=None: mock_headers.get(key, default)

        request.state = SimpleNamespace()
        request.method = "GET"
        request.url = Mock(path="/test")
        request.client = None

        async def mock_call_next(req):
            raise ValueError("Test error")

        # Mock uuid generation - patch uuid.uuid4 directly
        with patch("chat_api.middleware.uuid.uuid4") as mock_uuid4:
            # Create a mock UUID that returns our string when converted to str
            mock_uuid = Mock()
            mock_uuid4.return_value = mock_uuid

            # Patch str() on the returned UUID object
            with patch.object(mock_uuid, "__str__", return_value="error-uuid-000"):
                # Should propagate the exception
                with pytest.raises(ValueError, match="Test error"):
                    await add_request_id(request, mock_call_next)

                # But should still set request ID before exception
                assert request.state.request_id == "error-uuid-000"


class TestJWTAuthentication:
    """Test JWT authentication functions."""

    def test_token_creation_and_validation(self):
        """Test creating a token and extracting user_id from it."""
        user_id = "test_user_123"

        # Create token
        token = create_token(user_id)
        assert isinstance(token, str)

        # Decode and verify
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == user_id
        assert "exp" in payload
        assert "iat" in payload

        # Check expiration is in future
        exp_timestamp = payload["exp"]
        now_timestamp = datetime.now(UTC).timestamp()
        assert exp_timestamp > now_timestamp

    def test_expired_token_rejected(self):
        """Test that expired tokens are rejected."""
        user_id = "test_user_456"

        # Create an expired token
        expired_time = datetime.now(UTC) - timedelta(minutes=1)
        payload = {
            "sub": user_id,
            "exp": expired_time,
            "iat": datetime.now(UTC) - timedelta(minutes=31),
        }
        expired_token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

        # Try to validate - should raise
        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(get_current_user(f"Bearer {expired_token}"))

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test get_current_user with valid token."""
        user_id = "valid_user_789"
        token = create_token(user_id)

        # Should extract user_id successfully
        extracted_user_id = await get_current_user(f"Bearer {token}")
        assert extracted_user_id == user_id

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_format(self):
        """Test get_current_user with invalid authorization format."""
        # Missing Bearer prefix
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("invalid_token")

        assert exc_info.value.status_code == 401

        # Empty authorization
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("")

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid token."""
        # Malformed token
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("Bearer invalid.jwt.token")

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_missing_sub(self):
        """Test get_current_user with token missing 'sub' claim."""
        # Create token without 'sub' claim
        payload = {
            "exp": datetime.now(UTC) + timedelta(minutes=30),
            "iat": datetime.now(UTC),
        }
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(f"Bearer {token}")

        assert exc_info.value.status_code == 401
