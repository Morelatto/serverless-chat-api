"""Data models using Pydantic."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError


class ChatMessage(BaseModel):
    """Input message from user."""

    user_id: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=4000)

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_user_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise PydanticCustomError("empty_user_id", "User ID cannot be empty", {"input": value})
        if len(value.strip()) > 100:
            raise PydanticCustomError(
                "user_id_too_long",
                "User ID is too long (max 100 characters)",
                {"length": len(value), "max_length": 100},
            )
        return value.strip()

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not value or not value.strip():
            raise PydanticCustomError(
                "empty_content", "Message content cannot be empty", {"input": value}
            )
        if len(value.strip()) > 4000:
            raise PydanticCustomError(
                "content_too_long",
                "Message is too long (max 4000 characters)",
                {"length": len(value), "max_length": 4000},
            )
        return value.strip()


class ChatResponse(BaseModel):
    """Response from the API."""

    id: str
    content: str
    timestamp: datetime
    cached: bool = False
    model: str | None = None
