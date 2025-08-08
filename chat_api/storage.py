"""Storage operations - database and cache."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from typing import Any

import databases
import sqlalchemy as sa
from loguru import logger

from .config import settings

# Constants
DEFAULT_CACHE_TTL = 3600  # 1 hour
CACHE_KEY_MAX_LENGTH = 16
HISTORY_DEFAULT_LIMIT = 10

# Database setup (using databases for async)
database = databases.Database(settings.database_url)
metadata = sa.MetaData()

# Single table - simple and effective
messages = sa.Table(
    "messages",
    metadata,
    sa.Column("id", sa.String, primary_key=True),
    sa.Column("user_id", sa.String, index=True),
    sa.Column("content", sa.Text),
    sa.Column("response", sa.Text),
    sa.Column("timestamp", sa.DateTime),
    sa.Column("metadata", sa.JSON),
)

# Redis cache (initialized on startup)
_redis: Any | None = None  # Type is redis.asyncio.Redis when available


async def startup():
    """Initialize storage on startup."""
    global _redis
    await database.connect()

    # Create tables if not exist - handle different database types
    await _create_tables()

    # Initialize Redis if configured
    if settings.redis_url:
        try:
            import redis.asyncio as redis

            _redis = redis.from_url(settings.redis_url, decode_responses=True)
            # Test connection
            await _redis.ping()
            logger.info("Redis cache connected")
        except (ConnectionError, TimeoutError, ImportError) as e:
            logger.warning("Redis connection failed: {}. Running without cache.", e)
            _redis = None


async def _create_tables():
    """Create database tables if they don't exist."""
    # Get sync URL for table creation
    sync_url = _get_sync_database_url()

    if sync_url is None:
        # For in-memory databases, create tables using async connection
        await _create_tables_async()
    else:
        # Run synchronous table creation in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _create_tables_sync, sync_url)


def _get_sync_database_url() -> str | None:
    """Get synchronous database URL for table creation."""
    url_str = str(database.url)
    # Handle SQLite async driver
    if "sqlite" in url_str and "+aiosqlite" in url_str:
        sync_url = url_str.replace("+aiosqlite", "")
        # For in-memory databases, we can't create tables synchronously
        # because they exist only in the async connection
        if ":memory:" in sync_url:
            return None  # Will skip sync table creation
        return sync_url
    # For other databases, use as-is
    return url_str


async def _create_tables_async():
    """Create database tables using async connection (for in-memory DB)."""
    # Use SQLAlchemy DDL generation but execute with async connection
    from sqlalchemy.schema import CreateIndex, CreateTable

    # Generate create table statement
    create_table_stmt = CreateTable(messages, if_not_exists=True)
    await database.execute(str(create_table_stmt.compile(compile_kwargs={"literal_binds": True})))

    # Create index
    create_index_stmt = CreateIndex(
        sa.Index("idx_messages_user_id", messages.c.user_id), if_not_exists=True
    )
    await database.execute(str(create_index_stmt.compile(compile_kwargs={"literal_binds": True})))


def _create_tables_sync(sync_url: str):
    """Synchronously create database tables."""
    engine = sa.create_engine(sync_url)
    metadata.create_all(engine)
    engine.dispose()


async def shutdown():
    """Cleanup storage connections on shutdown.

    Closes database and Redis connections gracefully.
    """
    await database.disconnect()
    if _redis:
        await _redis.close()


async def save_message(id: str, user_id: str, content: str, response: str, **metadata_dict) -> None:
    """Save a message interaction to the database.

    Args:
        id: Unique message identifier.
        user_id: User identifier.
        content: User's message content.
        response: LLM's response.
        **metadata_dict: Additional metadata (model, usage, etc.).
    """
    query = messages.insert().values(
        id=id,
        user_id=user_id,
        content=content,
        response=response,
        timestamp=datetime.now(UTC),
        metadata=metadata_dict,
    )
    await database.execute(query)


async def get_user_history(
    user_id: str, limit: int = HISTORY_DEFAULT_LIMIT
) -> list[dict[str, Any]]:
    """Get user's message history from database.

    Args:
        user_id: User identifier.
        limit: Maximum number of messages to return.

    Returns:
        List of message dictionaries ordered by timestamp descending.
    """
    query = (
        messages.select()
        .where(messages.c.user_id == user_id)
        .order_by(messages.c.timestamp.desc())
        .limit(limit)
    )
    rows = await database.fetch_all(query)
    return [
        {
            "id": row["id"],
            "user_id": row["user_id"],
            "content": row["content"],
            "response": row["response"],
            "timestamp": row["timestamp"].isoformat(),
            **(row["metadata"] or {}),
        }
        for row in rows
    ]


def cache_key(user_id: str, content: str) -> str:
    """Generate efficient cache key.

    For short content, hash the full text.
    For long content, use prefix + hash to avoid hashing large strings.
    """
    if len(content) <= 100:
        text = f"{user_id}:{content}"
    else:
        # Use first 100 chars + hash of full content for efficiency
        text = f"{user_id}:{content[:100]}:{hash(content)}"

    return hashlib.sha256(text.encode()).hexdigest()[:CACHE_KEY_MAX_LENGTH]


async def get_cached(key: str) -> dict[str, Any] | None:
    """Get from cache.

    Returns:
        Cached data if found, None otherwise.
    """
    if _redis:
        try:
            data = await _redis.get(key)
            return json.loads(data) if data else None
        except (json.JSONDecodeError, ConnectionError, TimeoutError) as e:
            logger.debug("Cache get failed for key {}: {}", key, e)
            return None
    return None


async def set_cached(key: str, value: dict[str, Any], ttl: int = DEFAULT_CACHE_TTL) -> None:
    """Set in cache with TTL.

    Args:
        key: Cache key
        value: Data to cache
        ttl: Time to live in seconds
    """
    if _redis:
        try:
            await _redis.setex(key, ttl, json.dumps(value))
        except (TypeError, ConnectionError, TimeoutError) as e:
            logger.debug("Cache set failed for key {}: {}", key, e)


async def health_check() -> bool:
    """Check storage health.

    Returns:
        True if database is accessible, False otherwise.
    """
    try:
        await database.execute("SELECT 1")
    except (ConnectionError, TimeoutError):
        logger.exception("Database health check failed")
        return False
    else:
        return True
