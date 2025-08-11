"""Tests for API handlers and exception handling."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError

from chat_api.api import (
    chat_api_exception_handler,
    create_app,
    validation_exception_handler,
)
from chat_api.exceptions import (
    ChatAPIError,
    LLMProviderError,
    StorageError,
    ValidationError,
)


@pytest.mark.asyncio
async def test_validation_exception_handler_missing_field():
    """Test validation handler with missing field - covers line 101."""
    mock_request = MagicMock(spec=Request)

    # Create a validation error with missing field
    mock_error = MagicMock()
    mock_error.errors.return_value = [
        {"loc": ["body", "user_id"], "type": "missing", "msg": "Field required"},
    ]

    exc = RequestValidationError(errors=[])
    exc.errors = mock_error.errors

    response = await validation_exception_handler(mock_request, exc)

    assert response.status_code == 400
    data = response.body.decode()
    assert "user_id" in data
    assert "missing" in data


@pytest.mark.asyncio
async def test_validation_exception_handler_json_invalid():
    """Test validation handler with invalid JSON - covers line 101."""
    mock_request = MagicMock(spec=Request)

    mock_error = MagicMock()
    mock_error.errors.return_value = [{"loc": [], "type": "json_invalid", "msg": "Invalid JSON"}]

    exc = RequestValidationError(errors=[])
    exc.errors = mock_error.errors

    response = await validation_exception_handler(mock_request, exc)

    assert response.status_code == 400
    data = response.body.decode()
    assert "Invalid JSON format" in data


@pytest.mark.asyncio
async def test_chat_api_exception_handler_llm_error():
    """Test exception handler with LLMProviderError - covers lines 121-136."""
    mock_request = MagicMock(spec=Request)
    exc = LLMProviderError("LLM service unavailable")

    response = await chat_api_exception_handler(mock_request, exc)

    assert response.status_code == 503
    data = response.body.decode()
    assert "LLM service unavailable" in data
    assert "LLMProviderError" in data


@pytest.mark.asyncio
async def test_chat_api_exception_handler_storage_error():
    """Test exception handler with StorageError - covers lines 121-136."""
    mock_request = MagicMock(spec=Request)
    exc = StorageError("Database connection failed")

    response = await chat_api_exception_handler(mock_request, exc)

    assert response.status_code == 503
    data = response.body.decode()
    assert "Database connection failed" in data
    assert "StorageError" in data


@pytest.mark.asyncio
async def test_chat_api_exception_handler_validation_error():
    """Test exception handler with ValidationError - covers lines 121-136."""
    mock_request = MagicMock(spec=Request)
    exc = ValidationError("Invalid input")

    response = await chat_api_exception_handler(mock_request, exc)

    assert response.status_code == 400
    data = response.body.decode()
    assert "Invalid input" in data
    assert "ValidationError" in data


@pytest.mark.asyncio
async def test_chat_api_exception_handler_generic():
    """Test exception handler with generic ChatAPIError - covers lines 121-136."""
    mock_request = MagicMock(spec=Request)
    exc = ChatAPIError("Generic error")

    response = await chat_api_exception_handler(mock_request, exc)

    assert response.status_code == 500  # Default status code
    data = response.body.decode()
    assert "Generic error" in data
    assert "ChatAPIError" in data


def test_create_app():
    """Test create_app function - covers line 253."""
    app = create_app()

    assert app is not None
    assert app.title == "Chat API"
    assert app.version == "1.0.0"
    assert hasattr(app.state, "limiter")


def test_log_file_configuration():
    """Test log file configuration - covers line 33."""
    # This tests the module-level code that adds a log file handler
    # Since module-level code runs on import, we need to check if settings.log_file
    # would trigger the logger.add call

    # Just verify the configuration can be set
    # The actual logger.add is hard to test since it's module-level code
    # But we can at least verify the config works
    with patch.dict(
        os.environ,
        {"CHAT_LOG_FILE": "/tmp/test.log"},
    ):
        from chat_api.config import Settings

        test_settings = Settings(_env_file=None)
        assert test_settings.log_file == "/tmp/test.log"


@pytest.mark.asyncio
async def test_health_endpoint_unhealthy_status():
    """Test health endpoint when services are unhealthy - covers lines 213, 223-224."""
    from fastapi import Response

    from chat_api.api import health_endpoint

    # Mock the chat service
    mock_service = AsyncMock()
    mock_service.health_check.return_value = {
        "storage": False,  # Unhealthy storage
        "llm": True,
    }

    # Create a mock response
    mock_response = MagicMock(spec=Response)

    # Test basic health check
    result = await health_endpoint(mock_response, detailed=False, service=mock_service)

    # Should set status code to 503 when unhealthy
    assert mock_response.status_code == 503
    assert result["status"] == "unhealthy"
    assert "timestamp" in result
    assert result["services"]["storage"] is False
    assert result["services"]["llm"] is True

    # Test detailed health check - covers lines 223-224
    mock_response.status_code = None  # Reset
    result = await health_endpoint(mock_response, detailed=True, service=mock_service)

    assert mock_response.status_code == 503
    assert result["status"] == "unhealthy"
    assert "version" in result
    assert result["version"] == "1.0.0"
    assert "environment" in result
    assert "llm_provider" in result["environment"]
    assert "rate_limit" in result["environment"]
