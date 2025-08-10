"""Unified storage layer - SQLite, DynamoDB, and caching (Python 2025 style)."""

import hashlib
import json
import time
from typing import Any, Protocol
from urllib.parse import parse_qs, urlparse

from databases import Database
from loguru import logger

from .exceptions import StorageError
from .types import MessageRecord

# Constants
CACHE_TTL_SECONDS = 3600  # 1 hour default cache TTL
TTL_DAYS = 30  # DynamoDB TTL in days
CACHE_KEY_LENGTH = 32  # Blake2b hash output length
DEFAULT_CACHE_SIZE = 1000  # Default max cache size


# ============== Protocols ==============
class Repository(Protocol):
    """Storage repository protocol."""

    async def startup(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def save(self, **kwargs) -> None: ...
    async def get_history(self, user_id: str, limit: int) -> list[MessageRecord]: ...
    async def health_check(self) -> bool: ...


class Cache(Protocol):
    """Cache protocol."""

    async def startup(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def get(self, key: str) -> dict[str, Any] | None: ...
    async def set(self, key: str, value: dict[str, Any], ttl: int = CACHE_TTL_SECONDS) -> None: ...


# ============== Cache Implementations ==============
def cache_key(user_id: str, content: str) -> str:
    """Generate secure cache key from user ID and content."""
    combined = f"{user_id}:{content}"
    return hashlib.blake2b(combined.encode(), digest_size=16, salt=b"chat-cache-v1").hexdigest()


class InMemoryCache:
    """Simple in-memory cache with TTL support and LRU eviction."""

    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE) -> None:
        self.cache: dict[str, dict[str, Any]] = {}
        self.access_order: dict[str, float] = {}  # key -> last access time
        self.max_size = max_size
        logger.info(f"In-memory cache initialized with max size {max_size}")

    async def startup(self) -> None:
        """Initialize cache."""
        pass  # No initialization needed

    async def shutdown(self) -> None:
        """Cleanup cache."""
        self.cache.clear()
        self.access_order.clear()

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get value from cache if not expired."""
        if key not in self.cache:
            logger.debug(f"Cache miss: {key}")
            return None

        # Check if expired
        item = self.cache[key]
        if time.time() > item["_expires_at"]:
            # Remove expired item
            del self.cache[key]
            self.access_order.pop(key, None)
            logger.debug(f"Cache expired: {key}")
            return None

        # Update access time for LRU
        self.access_order[key] = time.time()
        logger.debug(f"Cache hit: {key}")

        # Return data without internal fields
        data = item.copy()
        data.pop("_expires_at", None)
        return data

    async def set(self, key: str, value: dict[str, Any], ttl: int = CACHE_TTL_SECONDS) -> None:
        """Set value in cache with TTL."""
        # Evict expired items first
        await self._evict_expired()

        # If at max size, evict least recently used
        if len(self.cache) >= self.max_size:
            await self._evict_lru()

        # Store with expiration time
        item = value.copy()
        item["_expires_at"] = time.time() + ttl
        self.cache[key] = item
        self.access_order[key] = time.time()
        logger.debug(f"Cached: {key} (size: {len(self.cache)}/{self.max_size}, TTL: {ttl}s)")

    async def _evict_expired(self) -> None:
        """Remove expired items."""
        now = time.time()
        expired_keys = [
            key for key, item in self.cache.items() if now > item.get("_expires_at", float("inf"))
        ]
        for key in expired_keys:
            del self.cache[key]
            self.access_order.pop(key, None)
            logger.debug(f"Evicted expired: {key}")

    async def _evict_lru(self) -> None:
        """Remove least recently used item."""
        if not self.access_order:
            return

        lru_key = min(self.access_order.items(), key=lambda x: x[1])[0]
        del self.cache[lru_key]
        del self.access_order[lru_key]
        logger.debug(f"Evicted LRU: {lru_key}")


class RedisCache:
    """Redis cache implementation."""

    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self.client: Any = None
        logger.info(f"Redis cache configured: {redis_url}")

    async def startup(self) -> None:
        """Initialize Redis connection."""
        import redis.asyncio as redis

        try:
            self.client = await redis.from_url(self.redis_url)
            await self.client.ping()
            logger.info("Redis cache connected")
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to in-memory cache.")
            # Fallback to in-memory with cachetools
            self._fallback = InMemoryCache()
            await self._fallback.startup()

    async def shutdown(self) -> None:
        """Close Redis connection."""
        if self.client:
            await self.client.close()

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get value from Redis."""
        if hasattr(self, "_fallback"):
            return await self._fallback.get(key)

        if not self.client:
            return None

        try:
            data = await self.client.get(key)
            if data:
                return json.loads(data)  # type: ignore[no-any-return]
        except (json.JSONDecodeError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis get error: {e}")
        return None

    async def set(self, key: str, value: dict[str, Any], ttl: int = 3600) -> None:
        """Set value in Redis with TTL."""
        if hasattr(self, "_fallback"):
            return await self._fallback.set(key, value, ttl)

        if not self.client:
            return None

        try:
            await self.client.setex(key, ttl, json.dumps(value))
        except (json.JSONDecodeError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis set error: {e}")


# ============== Repository Implementations ==============
class SQLiteRepository:
    """SQLite repository with connection pooling for production use."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        # SQLite doesn't support connection pooling parameters like PostgreSQL
        # The databases library handles SQLite connections appropriately
        self.database = Database(database_url)
        logger.info(f"SQLite repository configured: {database_url}")

    async def startup(self) -> None:
        """Initialize database connection and create tables."""
        await self.database.connect()

        # Create table if not exists
        await self.database.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                response TEXT NOT NULL,
                model TEXT,
                usage TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index for user_id
        await self.database.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id
            ON chat_history(user_id, timestamp DESC)
        """)

        logger.info("SQLite repository initialized")

    async def shutdown(self) -> None:
        """Close database connection."""
        await self.database.disconnect()

    async def save(self, **kwargs) -> None:
        """Save message to database."""
        usage_json = json.dumps(kwargs.get("usage", {})) if kwargs.get("usage") else None

        await self.database.execute(
            """
            INSERT INTO chat_history (id, user_id, content, response, model, usage)
            VALUES (:id, :user_id, :content, :response, :model, :usage)
            """,
            {
                "id": kwargs["id"],
                "user_id": kwargs["user_id"],
                "content": kwargs["content"],
                "response": kwargs["response"],
                "model": kwargs.get("model"),
                "usage": usage_json,
            },
        )

    async def get_history(self, user_id: str, limit: int = 10) -> list[MessageRecord]:
        """Get chat history for a user."""
        rows = await self.database.fetch_all(
            """
            SELECT id, user_id, content, response, model, usage, timestamp
            FROM chat_history
            WHERE user_id = :user_id
            ORDER BY timestamp DESC
            LIMIT :limit
            """,
            {"user_id": user_id, "limit": limit},
        )

        results: list[MessageRecord] = []
        for row in rows:
            record: MessageRecord = {
                "id": row["id"],
                "user_id": row["user_id"],
                "content": row["content"],
                "response": row["response"],
                "model": row["model"],
                "usage": json.loads(row["usage"]) if row["usage"] else None,
                "timestamp": row["timestamp"].isoformat()
                if hasattr(row["timestamp"], "isoformat")
                else str(row["timestamp"])
                if row["timestamp"]
                else "",
            }
            results.append(record)
        return results

    async def health_check(self) -> bool:
        """Check database health."""
        try:
            await self.database.execute("SELECT 1")
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error(f"Database health check failed: {e}")
            return False
        else:
            return True


class DynamoDBRepository:
    """DynamoDB repository for production."""

    def __init__(self, database_url: str) -> None:
        parsed = urlparse(database_url)
        self.table_name = parsed.netloc or parsed.path.lstrip("/")

        # Parse query parameters
        params = parse_qs(parsed.query) if parsed.query else {}
        self.region = params.get("region", ["us-east-1"])[0]

        self.session: Any = None
        logger.info(f"DynamoDB repository configured: {self.table_name} in {self.region}")

    async def startup(self) -> None:
        """Initialize DynamoDB session."""
        import aioboto3

        self.session = aioboto3.Session()

        # Check if table exists, create if not
        try:
            async with self.session.client("dynamodb", region_name=self.region) as client:
                await client.describe_table(TableName=self.table_name)
                logger.info(f"DynamoDB table {self.table_name} exists")
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.info(f"Table {self.table_name} does not exist, creating: {e}")
            await self._create_table()

    async def _create_table(self) -> None:
        """Create DynamoDB table."""
        async with self.session.client("dynamodb", region_name=self.region) as client:
            await client.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "timestamp", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "timestamp", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            # Wait for table to be active
            waiter = client.get_waiter("table_exists")
            await waiter.wait(TableName=self.table_name)

    async def shutdown(self) -> None:
        """Clean up DynamoDB session."""
        # Session doesn't need explicit cleanup in aioboto3

    async def save(self, **kwargs) -> None:
        """Save message to DynamoDB."""
        from datetime import UTC, datetime

        from boto3.dynamodb.types import TypeSerializer

        item = {
            "user_id": kwargs["user_id"],
            "timestamp": datetime.now(UTC).isoformat(),
            "id": kwargs["id"],
            "content": kwargs["content"],
            "response": kwargs["response"],
            "model": kwargs.get("model"),
            "usage": kwargs.get("usage"),
            "ttl": int(time.time()) + 86400 * TTL_DAYS,  # TTL in seconds
        }

        # Use boto3's built-in serializer
        serializer = TypeSerializer()
        serialized_item = {k: serializer.serialize(v) for k, v in item.items() if v is not None}

        async with self.session.client("dynamodb", region_name=self.region) as client:
            await client.put_item(TableName=self.table_name, Item=serialized_item)

    async def get_history(self, user_id: str, limit: int = 10) -> list[MessageRecord]:
        """Get chat history from DynamoDB."""
        from boto3.dynamodb.types import TypeDeserializer

        async with self.session.client("dynamodb", region_name=self.region) as client:
            response = await client.query(
                TableName=self.table_name,
                KeyConditionExpression="user_id = :user_id",
                ExpressionAttributeValues={":user_id": {"S": user_id}},
                Limit=limit,
                ScanIndexForward=False,  # Descending order
            )

        # Use boto3's built-in deserializer
        deserializer = TypeDeserializer()
        results: list[MessageRecord] = []
        for item in response.get("Items", []):
            deserialized_item = {k: deserializer.deserialize(v) for k, v in item.items()}
            record: MessageRecord = {
                "id": deserialized_item["id"],
                "user_id": deserialized_item["user_id"],
                "content": deserialized_item["content"],
                "response": deserialized_item["response"],
                "model": deserialized_item.get("model"),
                "usage": deserialized_item.get("usage"),
                "timestamp": deserialized_item["timestamp"],
            }
            results.append(record)
        return results

    async def health_check(self) -> bool:
        """Check DynamoDB health."""
        try:
            async with self.session.client("dynamodb", region_name=self.region) as client:
                await client.describe_table(TableName=self.table_name)
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error(f"DynamoDB health check failed: {e}")
            return False
        else:
            return True


# ============== Factory Functions ==============
def create_repository(database_url: str | None = None) -> Repository:
    """Create repository instance based on database URL."""
    from .config import settings

    # Use provided URL or get effective URL from settings
    if database_url is None:
        url = settings.effective_database_url
        if settings.is_lambda_environment:
            logger.info(f"AWS Lambda detected, using DynamoDB: {settings.dynamodb_table}")
    else:
        url = database_url

    parsed = urlparse(url)

    if parsed.scheme == "dynamodb":
        logger.info("Creating DynamoDB repository")
        return DynamoDBRepository(url)
    if parsed.scheme in ("sqlite", "sqlite+aiosqlite") or url.startswith("sqlite"):
        logger.info("Creating SQLite repository")
        return SQLiteRepository(url)
    raise StorageError(f"Unsupported database URL scheme: {url}. Must be 'sqlite' or 'dynamodb://'")


def create_cache(redis_url: str | None = None) -> Cache:
    """Create cache instance based on configuration."""
    from .config import settings

    # Try Redis if configured
    url = redis_url or settings.redis_url
    if url:
        logger.info("Creating Redis cache")
        return RedisCache(url)

    # Default to in-memory cache
    logger.info("Using in-memory cache")
    return InMemoryCache()


# Export public API
__all__ = [
    "Cache",
    "DynamoDBRepository",
    "InMemoryCache",
    "RedisCache",
    "Repository",
    "SQLiteRepository",
    "cache_key",
    "create_cache",
    "create_repository",
]
