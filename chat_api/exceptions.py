"""Domain-specific exceptions for the Chat API.

Simple, flat hierarchy with clear error messages.
Keep only what's actually used - YAGNI principle.
"""


class ChatAPIError(Exception):
    """Base exception for all Chat API errors."""


class LLMProviderError(ChatAPIError):
    """Error related to LLM provider operations."""


class StorageError(ChatAPIError):
    """Error related to storage operations."""


class ValidationError(ChatAPIError):
    """Error related to input validation (not Pydantic)."""


class ConfigurationError(ChatAPIError):
    """Error related to configuration issues."""
