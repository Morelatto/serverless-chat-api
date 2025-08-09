"""Storage protocol definitions using typing.Protocol."""

from typing import Any, Protocol


class Repository(Protocol):
    """Repository protocol for message persistence."""

    async def save(self, id: str, user_id: str, content: str, response: str, **metadata) -> None:
        """Save a message interaction."""
        ...

    async def get_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get user's message history."""
        ...

    async def health_check(self) -> bool:
        """Check if repository is healthy."""
        ...

    async def startup(self) -> None:
        """Initialize repository on startup."""
        ...

    async def shutdown(self) -> None:
        """Cleanup repository on shutdown."""
        ...


class Cache(Protocol):
    """Cache protocol for response caching."""

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get cached value."""
        ...

    async def set(self, key: str, value: dict[str, Any], ttl: int = 3600) -> None:
        """Set cached value with TTL."""
        ...

    async def startup(self) -> None:
        """Initialize cache on startup."""
        ...

    async def shutdown(self) -> None:
        """Cleanup cache on shutdown."""
        ...
