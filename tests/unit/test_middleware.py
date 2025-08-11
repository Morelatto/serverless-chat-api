"""Tests for middleware functionality."""

from unittest.mock import Mock, patch

import pytest
from fastapi import Request, Response

from chat_api.middleware import add_request_id


class TestRequestIDMiddleware:
    """Test request ID middleware."""

    @pytest.mark.asyncio
    async def test_add_request_id_with_existing_header(self):
        """Test middleware preserves existing X-Request-ID header."""
        # Create mock request with existing header
        request = Mock(spec=Request)
        request.headers = {"x-request-id": "existing-id-123"}
        request.state = Mock()

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
        request = Mock(spec=Request)
        request.headers = {}
        request.state = Mock()

        # Mock call_next
        async def mock_call_next(req):
            response = Mock(spec=Response)
            response.headers = {}
            response.status_code = 200
            return response

        # Mock uuid generation
        with patch("chat_api.middleware.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value = Mock(hex="generated-uuid-456")

            # Call middleware
            response = await add_request_id(request, mock_call_next)

            # Should generate new ID
            assert request.state.request_id == "generated-uuid-456"
            assert response.headers["X-Request-ID"] == "generated-uuid-456"

    @pytest.mark.asyncio
    async def test_add_request_id_propagates_to_response(self):
        """Test request ID is propagated to response headers."""
        request = Mock(spec=Request)
        request.headers = {"x-request-id": "test-id-789"}
        request.state = Mock()

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
        request = Mock(spec=Request)
        request.headers = {}
        request.state = Mock()

        async def mock_call_next(req):
            raise ValueError("Test error")

        with patch("chat_api.middleware.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value = Mock(hex="error-uuid-000")

            # Should propagate the exception
            with pytest.raises(ValueError, match="Test error"):
                await add_request_id(request, mock_call_next)

            # But should still set request ID before exception
            assert request.state.request_id == "error-uuid-000"
