"""Chat API - A simple LLM chat service with Pythonic design."""

from .api import app, create_app
from .chat import ChatMessage, ChatResponse, ChatService
from .providers import create_llm_provider

__version__ = "1.0.0"

__all__ = [
    "ChatMessage",
    "ChatResponse",
    "ChatService",
    "app",
    "create_app",
    "create_llm_provider",
]
