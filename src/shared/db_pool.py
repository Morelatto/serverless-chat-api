"""SQLite connection pool for better performance in concurrent scenarios."""

import logging
import sqlite3
from contextlib import contextmanager
from queue import Queue
from threading import Lock
from typing import Any, Generator

logger = logging.getLogger(__name__)


class SQLitePool:
    """Thread-safe SQLite connection pool with automatic cleanup."""
    
    def __init__(
        self,
        database: str,
        max_connections: int = 5,
        check_same_thread: bool = False,
        timeout: float = 30.0,
    ):
        """Initialize connection pool.
        
        Args:
            database: Path to SQLite database file
            max_connections: Maximum number of connections in pool
            check_same_thread: SQLite check_same_thread parameter
            timeout: Connection timeout in seconds
        """
        self.database = database
        self.max_connections = max_connections
        self.check_same_thread = check_same_thread
        self.timeout = timeout
        self.pool: Queue[sqlite3.Connection] = Queue(maxsize=max_connections)
        self._lock = Lock()
        self._created_connections = 0
        self._closed = False
        
        # Pre-create minimum connections
        self._initialize_pool()
        logger.info(f"SQLite pool initialized with max {max_connections} connections")
    
    def _initialize_pool(self) -> None:
        """Pre-create minimum connections for the pool."""
        min_connections = min(2, self.max_connections)
        for _ in range(min_connections):
            conn = self._create_connection()
            self.pool.put(conn)
            self._created_connections += 1
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with proper configuration."""
        conn = sqlite3.connect(
            self.database,
            check_same_thread=self.check_same_thread,
            timeout=self.timeout,
        )
        conn.row_factory = sqlite3.Row
        
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        
        # Create tables if needed
        self._ensure_tables(conn)
        
        return conn
    
    def _ensure_tables(self, conn: sqlite3.Connection) -> None:
        """Ensure required tables exist."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interactions (
                interaction_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT,
                model TEXT,
                timestamp TEXT NOT NULL,
                trace_id TEXT,
                tokens INTEGER,
                latency_ms INTEGER,
                error TEXT,
                metadata TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON interactions(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON interactions(timestamp)")
        conn.commit()
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a connection from the pool.
        
        Yields:
            sqlite3.Connection: Database connection
            
        Raises:
            RuntimeError: If pool is closed
        """
        if self._closed:
            raise RuntimeError("Connection pool is closed")
        
        conn = None
        try:
            # Try to get existing connection
            if not self.pool.empty():
                conn = self.pool.get_nowait()
            else:
                # Create new connection if under limit
                with self._lock:
                    if self._created_connections < self.max_connections:
                        conn = self._create_connection()
                        self._created_connections += 1
                        logger.debug(f"Created new connection ({self._created_connections}/{self.max_connections})")
                    else:
                        # Wait for available connection
                        logger.debug("Waiting for available connection")
                        conn = self.pool.get(timeout=self.timeout)
            
            # Test connection is alive
            try:
                conn.execute("SELECT 1")
            except sqlite3.Error:
                logger.warning("Connection is dead, creating new one")
                conn.close()
                conn = self._create_connection()
            
            yield conn
            
        finally:
            if conn and not self._closed:
                # Return connection to pool
                try:
                    self.pool.put_nowait(conn)
                except Exception:
                    # Pool is full, close connection
                    conn.close()
                    with self._lock:
                        self._created_connections -= 1
    
    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> list[sqlite3.Row]:
        """Execute a query and return results.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            List of result rows
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params or ())
            return cursor.fetchall()
    
    def execute_many(self, query: str, params_list: list[tuple[Any, ...]]) -> None:
        """Execute multiple queries efficiently.
        
        Args:
            query: SQL query to execute
            params_list: List of parameter tuples
        """
        with self.get_connection() as conn:
            conn.executemany(query, params_list)
            conn.commit()
    
    def close(self) -> None:
        """Close all connections in the pool."""
        self._closed = True
        
        # Close all connections
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
        
        logger.info("Connection pool closed")
    
    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics.
        
        Returns:
            Dictionary with pool statistics
        """
        return {
            "max_connections": self.max_connections,
            "created_connections": self._created_connections,
            "available_connections": self.pool.qsize(),
            "in_use_connections": self._created_connections - self.pool.qsize(),
            "closed": self._closed,
        }
    
    def __enter__(self) -> "SQLitePool":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - close pool."""
        self.close()


# Global pool instance
_pool: SQLitePool | None = None
_pool_lock = Lock()


def get_pool(database: str | None = None) -> SQLitePool:
    """Get or create the global connection pool.
    
    Args:
        database: Database path (uses default if None)
        
    Returns:
        SQLitePool instance
    """
    global _pool
    
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                import os
                db_path = database or os.getenv("DATABASE_PATH", "chat_history.db")
                _pool = SQLitePool(
                    database=db_path,
                    max_connections=int(os.getenv("DB_POOL_SIZE", "5")),
                )
    
    return _pool