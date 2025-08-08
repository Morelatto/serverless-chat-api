"""Chat API - A simple LLM chat service."""

__version__ = "1.0.0"
__all__ = ["ChatMessage", "ChatResponse", "app", "process_message"]

from .app import app
from .core import process_message
from .models import ChatMessage, ChatResponse
