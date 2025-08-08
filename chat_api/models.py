"""Data models using Pydantic."""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Input message from user."""

    user_id: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    """Response from the API."""

    id: str
    content: str
    timestamp: datetime
    cached: bool = False
    model: str | None = None
