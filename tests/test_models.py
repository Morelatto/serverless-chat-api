"""Test Pydantic models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from chat_api.models import ChatMessage, ChatResponse


def test_chat_message_valid():
    """Test valid chat message."""
    message = ChatMessage(user_id="test123", content="Hello world")
    assert message.user_id == "test123"
    assert message.content == "Hello world"


def test_chat_message_preserves_content():
    """Test that chat message preserves original content."""
    original_content = "Contact me at john.doe@example.com or call 123-456-7890"
    message = ChatMessage(user_id="test123", content=original_content)
    assert message.content == original_content


def test_chat_message_empty_user_id():
    """Test chat message with empty user_id."""
    with pytest.raises(ValidationError):
        ChatMessage(user_id="", content="Hello")


def test_chat_message_empty_content():
    """Test chat message with empty content."""
    with pytest.raises(ValidationError):
        ChatMessage(user_id="test123", content="")


def test_chat_message_long_user_id():
    """Test chat message with too long user_id."""
    long_id = "x" * 101
    with pytest.raises(ValidationError):
        ChatMessage(user_id=long_id, content="Hello")


def test_chat_message_long_content():
    """Test chat message with too long content."""
    long_content = "x" * 4001
    with pytest.raises(ValidationError):
        ChatMessage(user_id="test123", content=long_content)


def test_chat_response():
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


def test_chat_response_defaults():
    """Test chat response with defaults."""
    response = ChatResponse(id="test-123", content="Hello there!", timestamp=datetime.now(UTC))

    assert response.cached is False
    assert response.model is None
