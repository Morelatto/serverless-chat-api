"""SQLite repository implementation."""

import asyncio
from datetime import UTC, datetime
from typing import Any

import databases
import sqlalchemy as sa
from loguru import logger


class SQLiteRepository:
    """SQLite/PostgreSQL repository using databases."""

    def __init__(self, database_url: str):
        """Initialize SQLite repository.

        Args:
            database_url: Database connection URL.
        """
        self.database = databases.Database(database_url)
        self.metadata = sa.MetaData()

        # Define messages table
        self.messages = sa.Table(
            "messages",
            self.metadata,
            sa.Column("id", sa.String, primary_key=True),
            sa.Column("user_id", sa.String, index=True),
            sa.Column("content", sa.Text),
            sa.Column("response", sa.Text),
            sa.Column("timestamp", sa.DateTime),
            sa.Column("metadata", sa.JSON),
        )

    async def startup(self) -> None:
        """Initialize database connection and create tables."""
        await self.database.connect()

        # For in-memory databases, ensure tables are created in the same connection
        url_str = str(self.database.url)
        if ":memory:" in url_str:
            # Create tables directly without checking sync URL
            await self._create_tables_async()
        else:
            await self._create_tables()

    async def shutdown(self) -> None:
        """Close database connection."""
        await self.database.disconnect()

    async def save(self, id: str, user_id: str, content: str, response: str, **metadata) -> None:
        """Save a message interaction.

        Args:
            id: Unique message identifier.
            user_id: User identifier.
            content: User's message content.
            response: LLM's response.
            **metadata: Additional metadata.
        """
        query = self.messages.insert().values(
            id=id,
            user_id=user_id,
            content=content,
            response=response,
            timestamp=datetime.now(UTC),
            metadata=metadata,
        )
        await self.database.execute(query)

    async def get_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get user's message history.

        Args:
            user_id: User identifier.
            limit: Maximum number of messages to return.

        Returns:
            List of message dictionaries ordered by timestamp descending.
        """
        query = (
            self.messages.select()
            .where(self.messages.c.user_id == user_id)
            .order_by(self.messages.c.timestamp.desc())
            .limit(limit)
        )
        rows = await self.database.fetch_all(query)
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

    async def health_check(self) -> bool:
        """Check if database is accessible.

        Returns:
            True if database is healthy, False otherwise.
        """
        try:
            await self.database.execute("SELECT 1")
            return True
        except (ConnectionError, TimeoutError):
            logger.exception("Database health check failed")
            return False

    async def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        sync_url = self._get_sync_url()

        if sync_url is None:
            # For in-memory databases, create tables using async connection
            await self._create_tables_async()
        else:
            # Run synchronous table creation in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._create_tables_sync, sync_url)

    def _get_sync_url(self) -> str | None:
        """Get synchronous database URL for table creation."""
        url_str = str(self.database.url)
        # Handle SQLite async driver
        if "sqlite" in url_str and "+aiosqlite" in url_str:
            sync_url = url_str.replace("+aiosqlite", "")
            # For in-memory databases, we can't create tables synchronously
            if ":memory:" in sync_url:
                return None
            return sync_url
        # For other databases, use as-is
        return url_str

    async def _create_tables_async(self) -> None:
        """Create database tables using async connection (for in-memory DB)."""
        try:
            # Check if table exists
            check_sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
            result = await self.database.fetch_one(check_sql)

            if result is None:
                # Create table using raw SQL
                create_table_sql = """
                CREATE TABLE messages (
                    id VARCHAR PRIMARY KEY NOT NULL,
                    user_id VARCHAR NOT NULL,
                    content TEXT NOT NULL,
                    response TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    metadata JSON
                )
                """
                await self.database.execute(create_table_sql)

                # Create index
                index_sql = "CREATE INDEX idx_messages_user_id ON messages (user_id)"
                await self.database.execute(index_sql)
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            # Try alternative approach - just create without checking
            try:
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
                await self.database.execute(create_table_sql)
            except Exception:
                pass  # Table might already exist

    def _create_tables_sync(self, sync_url: str) -> None:
        """Synchronously create database tables."""
        engine = sa.create_engine(sync_url)
        self.metadata.create_all(engine)
        engine.dispose()
