"""Test error handling and edge cases."""

from unittest.mock import Mock

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError

from chat_api.api import chat_api_exception_handler, validation_exception_handler
from chat_api.exceptions import (
    LLMProviderError,
    StorageError,
)
from chat_api.exceptions import (
    ValidationError as ChatValidationError,
)


@pytest.mark.asyncio
async def test_chat_api_validation_error_handler():
    """Test handling of validation errors."""
    request = Mock(spec=Request)
    exc = ChatValidationError("Invalid input data")

    response = await chat_api_exception_handler(request, exc)

    assert response.status_code == 400
    content = response.body.decode()
    assert "Invalid input data" in content
    assert "ValidationError" in content


@pytest.mark.asyncio
async def test_chat_api_llm_error_handler():
    """Test handling of LLM provider errors."""
    request = Mock(spec=Request)
    exc = LLMProviderError("Provider unavailable")

    response = await chat_api_exception_handler(request, exc)

    assert response.status_code == 503
    content = response.body.decode()
    assert "Provider unavailable" in content
    assert "LLMProviderError" in content


@pytest.mark.asyncio
async def test_chat_api_storage_error_handler():
    """Test handling of storage errors."""
    request = Mock(spec=Request)
    exc = StorageError("Database connection failed")

    response = await chat_api_exception_handler(request, exc)

    assert response.status_code == 503
    content = response.body.decode()
    assert "Database connection failed" in content
    assert "StorageError" in content


@pytest.mark.asyncio
async def test_validation_exception_handler_missing_field():
    """Test handling of missing field validation errors."""
    request = Mock(spec=Request)

    # Create a mock validation error
    errors = [{"loc": ["body", "user_id"], "type": "missing", "msg": "Field required"}]
    exc = Mock(spec=RequestValidationError)
    exc.errors.return_value = errors

    response = await validation_exception_handler(request, exc)

    assert response.status_code == 400
    content = response.body.decode()
    assert "Required field 'user_id' is missing" in content


@pytest.mark.asyncio
async def test_validation_exception_handler_invalid_json():
    """Test handling of invalid JSON errors."""
    request = Mock(spec=Request)

    errors = [{"loc": ["body"], "type": "json_invalid", "msg": "Invalid JSON"}]
    exc = Mock(spec=RequestValidationError)
    exc.errors.return_value = errors

    response = await validation_exception_handler(request, exc)

    assert response.status_code == 400
    content = response.body.decode()
    assert "Invalid JSON format" in content
