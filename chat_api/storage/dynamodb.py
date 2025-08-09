"""DynamoDB repository implementation."""

import asyncio
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from loguru import logger


class DynamoDBRepository:
    """DynamoDB repository implementation."""

    def __init__(self, database_url: str):
        """Initialize DynamoDB repository.

        Args:
            database_url: DynamoDB URL in format: dynamodb://table_name?region=us-east-1
        """
        parsed = urlparse(database_url)
        self.table_name = parsed.netloc or parsed.path.lstrip("/")
        self.region = None

        # Parse region from query string
        if parsed.query:
            for param in parsed.query.split("&"):
                if param.startswith("region="):
                    self.region = param.split("=")[1]

        self.client = None
        self.table = None

    async def startup(self) -> None:
        """Initialize DynamoDB connection."""
        try:
            import boto3

            # Initialize clients
            resource = boto3.resource("dynamodb", region_name=self.region)
            self.table = resource.Table(self.table_name)
            self.client = boto3.client("dynamodb", region_name=self.region)

            logger.info(f"Connected to DynamoDB table: {self.table_name} in {self.region}")
        except ImportError:
            logger.error("boto3 not available. Install with: pip install boto3")
            raise

    async def shutdown(self) -> None:
        """No cleanup needed for DynamoDB."""
        pass

    async def save(self, id: str, user_id: str, content: str, response: str, **metadata) -> None:
        """Save a message interaction.

        Args:
            id: Unique message identifier.
            user_id: User identifier.
            content: User's message content.
            response: LLM's response.
            **metadata: Additional metadata.
        """
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
            "metadata": metadata,
        }

        # Run sync operation in executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self.table.put_item(Item=item))

    async def get_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get user's message history.

        Args:
            user_id: User identifier.
            limit: Maximum number of messages to return.

        Returns:
            List of message dictionaries ordered by timestamp descending.
        """

        def _query_dynamodb():
            from boto3.dynamodb.conditions import Key

            response = self.table.query(
                IndexName="user-index",
                KeyConditionExpression=Key("user_id").eq(user_id),
                ScanIndexForward=False,  # Sort descending
                Limit=limit,
                FilterExpression="begins_with(pk, :msg_prefix)",
                ExpressionAttributeValues={":msg_prefix": "message#"},
            )
            return response["Items"]

        loop = asyncio.get_event_loop()
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

    async def health_check(self) -> bool:
        """Check if DynamoDB is accessible.

        Returns:
            True if DynamoDB is healthy, False otherwise.
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.table.table_status)
            return True
        except (AttributeError, RuntimeError) as e:
            logger.warning(f"DynamoDB health check failed: {e}")
            return False
