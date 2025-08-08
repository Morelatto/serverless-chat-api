"""Entry point for python -m chat_api"""

import uvicorn

from .app import app
from .config import settings


def main():
    """Run the chat API server."""
    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level.lower())


if __name__ == "__main__":
    main()
