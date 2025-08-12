"""Storage layer implementations for chat API."""

import json
import time
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import parse_qs, urlparse

import aiosqlite
from loguru import logger

from .config import settings
from .exceptions import StorageError
from .types import MessageRecord


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
    async def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None: ...


def cache_key(user_id: str, content: str) -> str:
    """Generate cache key from user ID and content hash."""
    import hashlib

    content_hash = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:16]  # nosec B324
    return f"{user_id}:{content_hash}"


class InMemoryCache:
    """Simple in-memory cache using Python's dict."""

    def __init__(self, max_size: int | None = None) -> None:
        self.cache: dict[str, tuple[dict[str, Any], float]] = {}
        self.max_size = max_size or settings.cache_max_size
        logger.info(f"In-memory cache initialized with max size {self.max_size}")

    async def startup(self) -> None:
        """Initialize cache."""
        pass

    async def shutdown(self) -> None:
        """Cleanup cache."""
        self.cache.clear()

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get value from cache if not expired."""
        if key not in self.cache:
            logger.debug(f"Cache miss: {key}")
            return None

        data, expiry_time = self.cache[key]

        if time.time() > expiry_time:
            del self.cache[key]
            logger.debug(f"Cache expired: {key}")
            return None

        logger.debug(f"Cache hit: {key}")
        return data

    async def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or settings.cache_ttl_seconds

        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.debug(f"Evicted oldest: {oldest_key}")

        expiry_time = time.time() + ttl
        self.cache[key] = (value, expiry_time)
        logger.debug(f"Cached: {key} (size: {len(self.cache)}/{self.max_size}, TTL: {ttl}s)")

    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)

    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()
        logger.debug("Cache cleared")


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
            logger.info("Redis cache connected successfully")
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error(f"Redis connection failed: {e}")
            raise ConnectionError(f"Failed to connect to Redis at {self.redis_url}: {e}") from e

    async def shutdown(self) -> None:
        """Close Redis connection."""
        if self.client:
            try:
                await self.client.close()
                logger.info("Redis connection closed")
            except (ConnectionError, TimeoutError, OSError) as e:
                logger.warning(f"Error closing Redis connection: {e}")

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get value from Redis."""
        if not self.client:
            raise RuntimeError("Redis client not initialized - call startup() first")

        try:
            data = await self.client.get(key)
            if data:
                result = json.loads(data)
                logger.debug(f"Redis cache hit: {key}")
                return result  # type: ignore[no-any-return]
        except (json.JSONDecodeError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis get error for key {key}: {e}")
            raise
        else:
            logger.debug(f"Redis cache miss: {key}")
            return None

    async def set(self, key: str, value: dict[str, Any], ttl: int = 3600) -> None:
        """Set value in Redis with TTL."""
        if not self.client:
            raise RuntimeError("Redis client not initialized - call startup() first")

        try:
            serialized = json.dumps(value)
            await self.client.setex(key, ttl, serialized)
            logger.debug(f"Redis cached: {key} (TTL: {ttl}s)")
        except (json.JSONDecodeError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis set error for key {key}: {e}")
            raise


class SQLiteRepository:
    """SQLite repository with async aiosqlite."""

    def __init__(self, database_url: str) -> None:
        # Extract the file path from the URL
        if "///" in database_url:
            self.db_path = database_url.split("///")[1]
        else:
            self.db_path = database_url.replace("sqlite+aiosqlite://", "").replace("sqlite://", "")
        self.connection: aiosqlite.Connection | None = None
        logger.info(f"SQLite repository configured: {self.db_path}")

    async def startup(self) -> None:
        """Initialize database connection and create tables."""
        self.connection = await aiosqlite.connect(self.db_path)
        self.connection.row_factory = aiosqlite.Row

        async with self.connection.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                response TEXT NOT NULL,
                model TEXT,
                usage TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
""") as cursor:
            await cursor.close()

        async with self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id
            ON chat_history(user_id, timestamp)
        """) as cursor:
            await cursor.close()

        await self.connection.commit()
        logger.info("SQLite repository initialized")

    async def shutdown(self) -> None:
        """Close database connection."""
        if self.connection:
            await self.connection.close()
            self.connection = None

    async def save(self, **kwargs) -> None:
        """Save message to database."""
        if not self.connection:
            raise StorageError("Database connection not initialized")

        usage_json = json.dumps(kwargs.get("usage", {})) if kwargs.get("usage") else None

        async with self.connection.execute(
            """
            INSERT INTO chat_history (id, user_id, content, response, model, usage)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                kwargs["id"],
                kwargs["user_id"],
                kwargs["content"],
                kwargs["response"],
                kwargs.get("model"),
                usage_json,
            ),
        ) as cursor:
            await cursor.close()
        await self.connection.commit()

    async def get_history(self, user_id: str, limit: int = 10) -> list[MessageRecord]:
        """Get chat history for a user."""
        if not self.connection:
            raise StorageError("Database connection not initialized")

        async with self.connection.execute(
            """
            SELECT id, user_id, content, response, model, usage, timestamp
            FROM chat_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (user_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()

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
        if not self.connection:
            return False

        try:
            async with self.connection.execute("SELECT 1") as cursor:
                await cursor.fetchone()
        except (ConnectionError, TimeoutError, OSError, aiosqlite.Error) as e:
            logger.error(f"Database health check failed: {e}")
            return False
        else:
            return True


class DynamoDBRepository:
    """DynamoDB repository for production."""

    def __init__(self, database_url: str) -> None:
        parsed = urlparse(database_url)
        self.table_name = parsed.netloc or parsed.path.lstrip("/")

        params = parse_qs(parsed.query) if parsed.query else {}
        self.region = params.get("region", ["us-east-1"])[0]

        self.session: Any = None
        logger.info(f"DynamoDB repository configured: {self.table_name} in {self.region}")

    async def startup(self) -> None:
        """Initialize DynamoDB session."""
        import aioboto3

        self.session = aioboto3.Session()

        try:
            async with self.session.client("dynamodb", region_name=self.region) as client:
                await client.describe_table(TableName=self.table_name)
                logger.info(f"DynamoDB table {self.table_name} exists")
        except Exception:  # noqa: BLE001
            logger.info(f"Table {self.table_name} does not exist, creating")
            async with self.session.client("dynamodb", region_name=self.region) as client:
                await self._create_table_with_client(client)

    async def _create_table_with_client(self, client) -> None:
        """Create DynamoDB table if it doesn't exist."""
        await client.create_table(
            TableName=self.table_name,
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "N"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        waiter = client.get_waiter("table_exists")
        await waiter.wait(TableName=self.table_name)

        logger.info(f"DynamoDB table {self.table_name} created")

    async def shutdown(self) -> None:
        """Close session."""
        pass

    async def save(self, **kwargs) -> None:
        """Save message to DynamoDB."""
        from boto3.dynamodb.types import TypeSerializer

        item = {
            "user_id": kwargs["user_id"],
            "timestamp": int(time.time() * 1000),
            "id": kwargs["id"],
            "content": kwargs["content"],
            "response": kwargs["response"],
            "model": kwargs.get("model"),
            "usage": kwargs.get("usage"),
            "ttl": int(time.time()) + 86400 * settings.dynamodb_ttl_days,
        }

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
                ScanIndexForward=False,
                Limit=limit,
            )

        deserializer = TypeDeserializer()
        results: list[MessageRecord] = []

        for item in response.get("Items", []):
            deserialized = {k: deserializer.deserialize(v) for k, v in item.items()}

            timestamp_ms = deserialized.get("timestamp", 0)
            if timestamp_ms:
                dt = datetime.fromtimestamp(timestamp_ms / 1000, UTC)
                timestamp_str = dt.isoformat()
            else:
                timestamp_str = ""

            record: MessageRecord = {
                "id": deserialized.get("id", ""),
                "user_id": deserialized.get("user_id", ""),
                "content": deserialized.get("content", ""),
                "response": deserialized.get("response", ""),
                "model": deserialized.get("model"),
                "usage": deserialized.get("usage"),
                "timestamp": timestamp_str,
            }
            results.append(record)

        return results

    async def health_check(self) -> bool:
        """Check DynamoDB health."""
        try:
            async with self.session.client("dynamodb", region_name=self.region) as client:
                await client.describe_table(TableName=self.table_name)
                return True
        except Exception as e:  # noqa: BLE001
            logger.error(f"DynamoDB health check failed: {e}")
            return False


def create_repository(database_url: str | None = None) -> Repository:
    """Create repository instance based on database URL."""
    from .config import settings

    if database_url is None:
        url = settings.effective_database_url
        if settings.is_lambda_environment:
            logger.info(f"AWS Lambda detected, using DynamoDB: {settings.dynamodb_table}")
    else:
        url = database_url

    parsed = urlparse(url)

    if parsed.scheme == "dynamodb" or url.startswith("dynamodb://"):
        logger.info("Creating DynamoDB repository")
        return DynamoDBRepository(url)
    if parsed.scheme in ("sqlite", "sqlite+aiosqlite") or url.startswith("sqlite"):
        logger.info("Creating SQLite repository")
        return SQLiteRepository(url)
    raise StorageError(f"Unsupported database URL scheme: {url}. Must be 'sqlite' or 'dynamodb://'")


def create_cache(redis_url: str | None = None) -> Cache:
    """Create cache instance based on configuration."""
    from .config import settings

    url = redis_url or settings.redis_url
    if url:
        logger.info("Creating Redis cache")
        return RedisCache(url)  # type: ignore[return-value]

    logger.info("Using in-memory cache")
    return InMemoryCache()  # type: ignore[return-value]
