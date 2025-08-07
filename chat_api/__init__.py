"""Chat API - A simple LLM chat service."""

__version__ = "1.0.0"
__all__ = ["app", "process_message", "ChatMessage", "ChatResponse"]

from .app import app
from .core import process_message
from .models import ChatMessage, ChatResponse
