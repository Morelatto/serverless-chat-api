"""
Pydantic models for request/response validation and sanitization.
Ensures data integrity and security through automatic validation.
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
import re


class ChatRequest(BaseModel):
    """Request model for chat endpoint with validation."""
    
    userId: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique user identifier"
    )
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User's prompt to the LLM"
    )
    
    @field_validator('userId')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Ensure userId contains only safe characters."""
        if not re.match(r'^[a-zA-Z0-9\-_]+$', v):
            raise ValueError("userId must contain only alphanumeric characters, hyphens, and underscores")
        return v
    
    @field_validator('prompt')
    @classmethod
    def sanitize_prompt(cls, v: str) -> str:
        """Remove potential security threats and PII from prompt."""
        # Remove potential SQL injection patterns
        dangerous_patterns = [
            r'(?i)(DROP\s+TABLE)',
            r'(?i)(DELETE\s+FROM)',
            r'(?i)(INSERT\s+INTO)',
            r'(?i)(UPDATE\s+.*\s+SET)',
            r'(?i)<script.*?>.*?</script>',
            r'(?i)(javascript:)',
            r'(?i)(onclick|onerror|onload)='
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v):
                raise ValueError("Potentially dangerous content detected in prompt")
        
        # Remove PII patterns (Brazilian context)
        # CPF pattern: XXX.XXX.XXX-XX
        v = re.sub(r'\d{3}\.\d{3}\.\d{3}-\d{2}', '[CPF_REMOVED]', v)
        
        # Email pattern
        v = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL_REMOVED]', v)
        
        # Phone pattern (Brazilian): (XX) XXXXX-XXXX or (XX) XXXX-XXXX
        v = re.sub(r'\(\d{2}\)\s?\d{4,5}-\d{4}', '[PHONE_REMOVED]', v)
        
        # Credit card pattern: XXXX XXXX XXXX XXXX
        v = re.sub(r'\d{4}\s?\d{4}\s?\d{4}\s?\d{4}', '[CARD_REMOVED]', v)
        
        return v.strip()


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    
    id: str = Field(..., description="Unique interaction identifier")
    userId: str = Field(..., description="User who made the request")
    prompt: str = Field(..., description="Original prompt")
    response: str = Field(..., description="LLM response")
    model: str = Field(..., description="Model used for generation")
    timestamp: str = Field(..., description="ISO timestamp of response")
    cached: bool = Field(default=False, description="Whether response was cached")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "userId": "user123",
                "prompt": "What is the weather today?",
                "response": "I don't have access to real-time weather data...",
                "model": "gemini-pro",
                "timestamp": "2024-01-15T10:30:00Z",
                "cached": False
            }
        }


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="Current timestamp")
    version: Optional[str] = Field(default="1.0.0", description="API version")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    trace_id: Optional[str] = Field(None, description="Request trace ID for debugging")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())