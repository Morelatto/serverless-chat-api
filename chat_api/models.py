"""Data models using Pydantic."""
import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    """Input message from user."""
    user_id: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        """Remove PII and sanitize content."""
        # Remove email addresses
        v = re.sub(r'\b[\w._%+-]+@[\w.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', v)
        # Remove phone numbers
        v = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', v)
        return v.strip()


class ChatResponse(BaseModel):
    """Response from the API."""
    id: str
    content: str
    timestamp: datetime
    cached: bool = False
    model: str | None = None
