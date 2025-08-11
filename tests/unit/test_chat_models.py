"""Test Pydantic models."""

from datetime import UTC, datetime

import pytest
from pydantic_core import ValidationError as PydanticValidationError

from chat_api.chat import ChatMessage, ChatResponse
from chat_api.exceptions import ValidationError


def test_chat_message_valid() -> None:
    """Test valid chat message."""
    message = ChatMessage(user_id="test123", content="Hello world")
    assert message.user_id == "test123"
    assert message.content == "Hello world"


def test_chat_message_preserves_content() -> None:
    """Test that chat message preserves original content."""
    original_content = "Contact me at john.doe@example.com or call 123-456-7890"
    message = ChatMessage(user_id="test123", content=original_content)
    assert message.content == original_content


def test_chat_message_empty_user_id() -> None:
    """Test chat message with empty user_id."""
    with pytest.raises(PydanticValidationError):
        ChatMessage(user_id="", content="Hello")


def test_chat_message_empty_content() -> None:
    """Test chat message with empty content."""
    with pytest.raises(PydanticValidationError):
        ChatMessage(user_id="test123", content="")


def test_chat_message_long_user_id() -> None:
    """Test chat message with too long user_id."""
    # User ID longer than 100 chars gets truncated by sanitizer
    long_id = "x" * 101
    message = ChatMessage(user_id=long_id, content="Hello")
    assert len(message.user_id) == 100  # Truncated to max length


def test_chat_message_long_content() -> None:
    """Test chat message with too long content."""
    # Content longer than max_length (10000) should fail
    long_content = "x" * 10001
    # Our validator raises our custom ValidationError, not Pydantic's
    with pytest.raises((ValidationError, PydanticValidationError)):
        ChatMessage(user_id="test123", content=long_content)


def test_chat_response() -> None:
    """Test chat response model."""
    response = ChatResponse(
        id="test-123",
        content="Hello there!",
        timestamp=datetime.now(UTC),
        cached=True,
        model="test-model",
    )

    assert response.id == "test-123"
    assert response.content == "Hello there!"
    assert response.cached is True
    assert response.model == "test-model"


def test_chat_response_defaults() -> None:
    """Test chat response with defaults."""
    response = ChatResponse(id="test-123", content="Hello there!", timestamp=datetime.now(UTC))

    assert response.cached is False
    assert response.model is None
