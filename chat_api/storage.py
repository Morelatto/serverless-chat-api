"""Storage operations - database and cache."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import databases
import sqlalchemy as sa
from loguru import logger

from .config import settings

# Constants
DEFAULT_CACHE_TTL = 3600  # 1 hour
CACHE_KEY_MAX_LENGTH = 16
HISTORY_DEFAULT_LIMIT = 10

# Parse database URL to determine backend
_parsed_url = urlparse(settings.database_url)
_is_dynamodb = _parsed_url.scheme == "dynamodb"

# Database setup - conditional based on URL scheme
if _is_dynamodb:
    # DynamoDB setup
    _dynamodb_table_name = _parsed_url.netloc or _parsed_url.path.lstrip("/")
    _dynamodb_region = None
    if _parsed_url.query:
        for param in _parsed_url.query.split("&"):
            if param.startswith("region="):
                _dynamodb_region = param.split("=")[1]

    # Import boto3 for DynamoDB (lazy import to avoid dependency in SQLite mode)
    try:
        import boto3

        _dynamodb_client = boto3.client("dynamodb", region_name=_dynamodb_region)
        _dynamodb_resource = boto3.resource("dynamodb", region_name=_dynamodb_region)
        _dynamodb_table = _dynamodb_resource.Table(_dynamodb_table_name)
    except ImportError:
        logger.error("boto3 not available for DynamoDB. Install with: pip install boto3")
        _dynamodb_client = None
        _dynamodb_resource = None
        _dynamodb_table = None

    database = None
    metadata = None
    messages = None
else:
    # SQLite/PostgreSQL setup (using databases for async)
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

    # Initialize database connection - conditional based on backend
    if _is_dynamodb:
        # DynamoDB doesn't need explicit connection setup
        logger.info(f"Using DynamoDB table: {_dynamodb_table_name} in region: {_dynamodb_region}")
    elif database is not None:
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
    if database is None:
        return None
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
    if database is None:
        return
    # Use transactions to ensure table creation is committed
    async with database.transaction():
        # Create table using raw SQL for better control
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS messages (
            id VARCHAR PRIMARY KEY NOT NULL,
            user_id VARCHAR NOT NULL,
            content TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            metadata JSON
        )
        """
        logger.debug("Creating table with SQL: {}", create_table_sql)
        await database.execute(create_table_sql)

        # Create index
        index_sql = "CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages (user_id)"
        logger.debug("Creating index with SQL: {}", index_sql)
        await database.execute(index_sql)

        # Verify table was created
        result = await database.execute("SELECT COUNT(*) FROM messages")
        logger.debug("Table verification successful: {}", result)


def _create_tables_sync(sync_url: str):
    """Synchronously create database tables."""
    if metadata is None:
        return
    engine = sa.create_engine(sync_url)
    metadata.create_all(engine)
    engine.dispose()


async def shutdown():
    """Cleanup storage connections on shutdown.

    Closes database and Redis connections gracefully.
    """
    if not _is_dynamodb and database is not None:
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
    if _is_dynamodb:
        # DynamoDB implementation with new schema
        timestamp = datetime.now(UTC).isoformat()
        item = {
            "pk": f"message#{id}",
            "sk": "data",
            "id": id,
            "user_id": user_id,
            "content": content,
            "response": response,
            "timestamp": timestamp,
            "created_at": timestamp,  # For GSI
            "metadata": metadata_dict,
        }

        # Use asyncio to run the sync DynamoDB operation
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: _dynamodb_table.put_item(Item=item))
    elif database is not None and messages is not None:
        # SQLite/PostgreSQL implementation
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
    if _is_dynamodb:
        # DynamoDB implementation with GSI
        loop = asyncio.get_event_loop()

        def _query_dynamodb():
            from boto3.dynamodb.conditions import Key

            response = _dynamodb_table.query(
                IndexName="user-index",
                KeyConditionExpression=Key("user_id").eq(user_id),
                ScanIndexForward=False,  # Sort descending by created_at
                Limit=limit,
                FilterExpression="begins_with(pk, :msg_prefix)",
                ExpressionAttributeValues={":msg_prefix": "message#"},
            )
            return response["Items"]

        items = await loop.run_in_executor(None, _query_dynamodb)

        return [
            {
                "id": item["id"],
                "user_id": item["user_id"],
                "content": item["content"],
                "response": item["response"],
                "timestamp": item["timestamp"],
                **(item.get("metadata", {})),
            }
            for item in items
        ]
    if database is not None and messages is not None:
        # SQLite/PostgreSQL implementation
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
    return []


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
    elif _is_dynamodb:
        # Use DynamoDB as cache when Redis not available
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: _dynamodb_table.get_item(Key={"pk": f"cache#{key}", "sk": "data"})
            )

            if "Item" in response:
                # Check if not expired (TTL handles auto-deletion but we double-check)
                import time

                if response["Item"].get("ttl", 0) > int(time.time()):
                    cached_data = response["Item"].get("cached_data")
                    return cached_data if isinstance(cached_data, dict) else None
        except (KeyError, TypeError, AttributeError) as e:
            logger.debug("DynamoDB cache get failed for key {}: {}", key, e)
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
    elif _is_dynamodb:
        # Use DynamoDB as cache when Redis not available
        try:
            import time

            expire_time = int(time.time()) + ttl

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: _dynamodb_table.put_item(
                    Item={
                        "pk": f"cache#{key}",
                        "sk": "data",
                        "cached_data": value,
                        "ttl": expire_time,
                        "created_at": datetime.now(UTC).isoformat(),
                    }
                ),
            )
        except (TypeError, AttributeError) as e:
            logger.debug("DynamoDB cache set failed for key {}: {}", key, e)


async def health_check() -> bool:
    """Check storage health.

    Returns:
        True if database is accessible, False otherwise.
    """
    if _is_dynamodb:
        # DynamoDB health check
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: _dynamodb_table.table_status)
        except (AttributeError, RuntimeError) as e:
            logger.warning("DynamoDB health check failed: {}", e)
            return False
        else:
            return True
    elif database is not None:
        # SQLite/PostgreSQL health check
        try:
            await database.execute("SELECT 1")
        except (ConnectionError, TimeoutError):
            logger.exception("Database health check failed")
            return False
        else:
            return True
    return False
