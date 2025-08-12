"""Type definitions for the Chat API."""

from decimal import Decimal

from typing_extensions import TypedDict


class TokenUsage(TypedDict, total=False):
    """Token usage information from LLM API."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: Decimal


class HealthStatus(TypedDict):
    """Health status of system components."""

    storage: bool
    llm: bool
    cache: bool


class ChatResult(TypedDict):
    """Result from chat processing."""

    id: str
    content: str
    model: str
    cached: bool
    usage: TokenUsage


class MessageRecord(TypedDict, total=False):
    """Database record for a chat message."""

    id: str
    user_id: str
    content: str
    response: str
    model: str | None
    usage: TokenUsage | None
    timestamp: str
