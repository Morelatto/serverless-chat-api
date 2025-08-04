"""
Unified database interface supporting both SQLite (local) and DynamoDB (production).
Handles all persistence operations with automatic environment detection.
"""
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class DatabaseInterface:
    """Unified interface for database operations."""

    def __init__(self):
        """Initialize database based on environment."""
        self.is_production = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None

        if self.is_production:
            self._init_dynamodb()
        else:
            self._init_sqlite()

    def _init_sqlite(self):
        """Initialize SQLite for local development."""
        db_path = os.getenv("DATABASE_PATH", "chat_history.db")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Create table if not exists
        self.conn.execute("""
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
        """)

        # Create indexes for performance
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON interactions(user_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON interactions(timestamp)")
        self.conn.commit()

        logger.info("SQLite database initialized")

    def _init_dynamodb(self):
        """Initialize DynamoDB for production."""
        import boto3

        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(os.getenv("DYNAMODB_TABLE", "chat-interactions"))
        logger.info("DynamoDB initialized")

    async def save_interaction(
        self,
        user_id: str,
        prompt: str,
        response: str | None = None,
        model: str | None = None,
        trace_id: str | None = None
    ) -> str:
        """Save a new interaction to the database."""
        interaction_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        if self.is_production:
            # DynamoDB
            item = {
                'interaction_id': interaction_id,
                'user_id': user_id,
                'prompt': prompt,
                'timestamp': timestamp,
                'trace_id': trace_id or ''
            }

            if response:
                item['response'] = response
            if model:
                item['model'] = model

            self.table.put_item(Item=item)

        else:
            # SQLite
            self.conn.execute("""
                INSERT INTO interactions
                (interaction_id, user_id, prompt, response, model, timestamp, trace_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (interaction_id, user_id, prompt, response, model, timestamp, trace_id))
            self.conn.commit()

        logger.info(f"Saved interaction {interaction_id} for user {user_id}")
        return interaction_id

    async def update_interaction(
        self,
        interaction_id: str,
        response: str | None = None,
        model: str | None = None,
        tokens: int | None = None,
        latency_ms: int | None = None,
        error: str | None = None
    ):
        """Update an existing interaction with response data."""
        if self.is_production:
            # DynamoDB update
            update_expr = "SET "
            expr_values = {}

            if response:
                update_expr += "response = :response, "
                expr_values[':response'] = response
            if model:
                update_expr += "model = :model, "
                expr_values[':model'] = model
            if tokens:
                update_expr += "tokens = :tokens, "
                expr_values[':tokens'] = tokens
            if latency_ms:
                update_expr += "latency_ms = :latency, "
                expr_values[':latency'] = latency_ms
            if error:
                update_expr += "error = :error, "
                expr_values[':error'] = error

            update_expr = update_expr.rstrip(", ")

            self.table.update_item(
                Key={'interaction_id': interaction_id},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values
            )

        else:
            # SQLite update
            updates = []
            params = []

            if response is not None:
                updates.append("response = ?")
                params.append(response)
            if model:
                updates.append("model = ?")
                params.append(model)
            if tokens:
                updates.append("tokens = ?")
                params.append(tokens)
            if latency_ms:
                updates.append("latency_ms = ?")
                params.append(latency_ms)
            if error:
                updates.append("error = ?")
                params.append(error)

            if updates:
                params.append(interaction_id)
                query = f"UPDATE interactions SET {', '.join(updates)} WHERE interaction_id = ?"
                self.conn.execute(query, params)
                self.conn.commit()

        logger.info(f"Updated interaction {interaction_id}")

    async def get_interaction(self, interaction_id: str) -> dict[str, Any] | None:
        """Retrieve a specific interaction by ID."""
        if self.is_production:
            response = self.table.get_item(Key={'interaction_id': interaction_id})
            return response.get('Item')
        else:
            cursor = self.conn.execute(
                "SELECT * FROM interactions WHERE interaction_id = ?",
                (interaction_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    async def get_user_interactions(self, user_id: str, limit: int = 10) -> list:
        """Get recent interactions for a user."""
        if self.is_production:
            response = self.table.query(
                IndexName='UserIdIndex',
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={':uid': user_id},
                Limit=limit,
                ScanIndexForward=False
            )
            return response.get('Items', [])
        else:
            cursor = self.conn.execute("""
                SELECT * FROM interactions
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]

    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            if self.is_production:
                # DynamoDB describe table
                _ = self.table.table_status
            else:
                # SQLite simple query
                self.conn.execute("SELECT 1").fetchone()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            raise e
