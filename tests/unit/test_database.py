"""
Unit tests for DatabaseInterface.
Tests SQLite operations and DynamoDB mock operations.
"""
import os
import tempfile
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from src.shared.database import DatabaseInterface


class TestDatabaseSQLite:
    """Test SQLite database operations."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Set environment variable for database path
        os.environ["DATABASE_PATH"] = db_path

        yield db_path

        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass
        finally:
            if "DATABASE_PATH" in os.environ:
                del os.environ["DATABASE_PATH"]

    @pytest.fixture
    def db_interface(self, temp_db):
        """Create a DatabaseInterface instance with SQLite."""
        # Ensure we're not in production mode
        if "AWS_LAMBDA_FUNCTION_NAME" in os.environ:
            del os.environ["AWS_LAMBDA_FUNCTION_NAME"]

        return DatabaseInterface()

    def test_sqlite_initialization(self, db_interface, temp_db):
        """Test SQLite database initialization."""
        assert db_interface.is_production is False
        assert db_interface.conn is not None

        # Check table exists
        cursor = db_interface.conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='interactions'
        """
        )
        assert cursor.fetchone() is not None

        # Check indexes exist
        cursor = db_interface.conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='index' AND name IN ('idx_user_id', 'idx_timestamp')
        """
        )
        indexes = [row[0] for row in cursor.fetchall()]
        assert "idx_user_id" in indexes
        assert "idx_timestamp" in indexes

    @pytest.mark.asyncio
    async def test_save_interaction(self, db_interface):
        """Test saving a new interaction."""
        interaction_id = await db_interface.save_interaction(
            user_id="test_user",
            prompt="Test prompt",
            response="Test response",
            model="test-model",
            trace_id="trace123",
        )

        assert interaction_id is not None
        assert len(interaction_id) == 36  # UUID format

        # Verify data was saved
        cursor = db_interface.conn.execute(
            "SELECT * FROM interactions WHERE interaction_id = ?", (interaction_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["user_id"] == "test_user"
        assert row["prompt"] == "Test prompt"
        assert row["response"] == "Test response"
        assert row["model"] == "test-model"
        assert row["trace_id"] == "trace123"

    @pytest.mark.asyncio
    async def test_save_interaction_minimal(self, db_interface):
        """Test saving interaction with minimal data."""
        interaction_id = await db_interface.save_interaction(
            user_id="test_user", prompt="Test prompt"
        )

        cursor = db_interface.conn.execute(
            "SELECT * FROM interactions WHERE interaction_id = ?", (interaction_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["response"] is None
        assert row["model"] is None

    @pytest.mark.asyncio
    async def test_update_interaction(self, db_interface):
        """Test updating an existing interaction."""
        # Create interaction
        interaction_id = await db_interface.save_interaction(
            user_id="test_user", prompt="Test prompt"
        )

        # Update it
        await db_interface.update_interaction(
            interaction_id=interaction_id,
            response="Updated response",
            model="updated-model",
            tokens=100,
            latency_ms=500,
        )

        # Verify update
        cursor = db_interface.conn.execute(
            "SELECT * FROM interactions WHERE interaction_id = ?", (interaction_id,)
        )
        row = cursor.fetchone()
        assert row["response"] == "Updated response"
        assert row["model"] == "updated-model"
        assert row["tokens"] == 100
        assert row["latency_ms"] == 500

    @pytest.mark.asyncio
    async def test_update_interaction_with_error(self, db_interface):
        """Test updating interaction with error."""
        interaction_id = await db_interface.save_interaction(
            user_id="test_user", prompt="Test prompt"
        )

        await db_interface.update_interaction(
            interaction_id=interaction_id, error="Test error occurred"
        )

        cursor = db_interface.conn.execute(
            "SELECT error FROM interactions WHERE interaction_id = ?", (interaction_id,)
        )
        row = cursor.fetchone()
        assert row["error"] == "Test error occurred"

    @pytest.mark.asyncio
    async def test_get_interaction(self, db_interface):
        """Test retrieving a specific interaction."""
        # Create interaction
        interaction_id = await db_interface.save_interaction(
            user_id="test_user", prompt="Test prompt", response="Test response", model="test-model"
        )

        # Retrieve it
        interaction = await db_interface.get_interaction(interaction_id)

        assert interaction is not None
        assert interaction["interaction_id"] == interaction_id
        assert interaction["user_id"] == "test_user"
        assert interaction["prompt"] == "Test prompt"
        assert interaction["response"] == "Test response"

    @pytest.mark.asyncio
    async def test_get_interaction_not_found(self, db_interface):
        """Test retrieving non-existent interaction."""
        interaction = await db_interface.get_interaction("non-existent-id")
        assert interaction is None

    @pytest.mark.asyncio
    async def test_get_user_interactions(self, db_interface):
        """Test retrieving user interactions."""
        # Create multiple interactions
        for i in range(5):
            await db_interface.save_interaction(
                user_id="test_user", prompt=f"Prompt {i}", response=f"Response {i}"
            )

        # Create interactions for another user
        await db_interface.save_interaction(user_id="other_user", prompt="Other prompt")

        # Get user interactions
        interactions = await db_interface.get_user_interactions("test_user", limit=3)

        assert len(interactions) == 3
        assert all(i["user_id"] == "test_user" for i in interactions)

        # Check ordering (most recent first)
        assert interactions[0]["prompt"] == "Prompt 4"
        assert interactions[1]["prompt"] == "Prompt 3"
        assert interactions[2]["prompt"] == "Prompt 2"

    @pytest.mark.asyncio
    async def test_get_user_interactions_empty(self, db_interface):
        """Test retrieving interactions for user with no data."""
        interactions = await db_interface.get_user_interactions("non_existent_user")
        assert interactions == []

    @pytest.mark.asyncio
    async def test_health_check_success(self, db_interface):
        """Test successful health check."""
        result = await db_interface.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, db_interface):
        """Test health check with database error."""
        # Close the connection to simulate failure
        db_interface.conn.close()

        with pytest.raises(Exception):
            await db_interface.health_check()

    @pytest.mark.asyncio
    async def test_concurrent_writes(self, db_interface):
        """Test multiple concurrent write operations."""
        import asyncio

        async def save_interaction(i):
            return await db_interface.save_interaction(user_id=f"user_{i}", prompt=f"Prompt {i}")

        # Create multiple interactions concurrently
        tasks = [save_interaction(i) for i in range(10)]
        interaction_ids = await asyncio.gather(*tasks)

        assert len(interaction_ids) == 10
        assert len(set(interaction_ids)) == 10  # All unique

        # Verify all were saved
        cursor = db_interface.conn.execute("SELECT COUNT(*) as count FROM interactions")
        count = cursor.fetchone()["count"]
        assert count == 10


class TestDatabaseDynamoDB:
    """Test DynamoDB database operations."""

    @pytest.fixture
    def mock_dynamodb(self):
        """Mock DynamoDB resources."""
        with patch("boto3.resource") as mock_resource:
            mock_table = MagicMock()
            mock_table.table_status = "ACTIVE"
            mock_table.put_item = MagicMock()
            mock_table.update_item = MagicMock()
            mock_table.get_item = MagicMock()
            mock_table.query = MagicMock()

            mock_dynamodb_resource = MagicMock()
            mock_dynamodb_resource.Table.return_value = mock_table
            mock_resource.return_value = mock_dynamodb_resource

            yield mock_table

    @pytest.fixture
    def db_interface_prod(self, mock_dynamodb):
        """Create a DatabaseInterface instance for production (DynamoDB)."""
        # Set production environment
        os.environ["AWS_LAMBDA_FUNCTION_NAME"] = "test-function"

        # Mock the boto3 import that happens inside _init_dynamodb
        with patch.object(DatabaseInterface, "_init_dynamodb") as mock_init:
            db = DatabaseInterface()
            # Manually set the attributes that _init_dynamodb would set
            db.dynamodb = MagicMock()
            db.table = mock_dynamodb

        # Cleanup
        del os.environ["AWS_LAMBDA_FUNCTION_NAME"]

        return db

    def test_dynamodb_initialization(self, db_interface_prod, mock_dynamodb):
        """Test DynamoDB initialization."""
        assert db_interface_prod.is_production is True
        assert hasattr(db_interface_prod, "table")

    @pytest.mark.asyncio
    async def test_save_interaction_dynamodb(self, db_interface_prod, mock_dynamodb):
        """Test saving interaction to DynamoDB."""
        interaction_id = await db_interface_prod.save_interaction(
            user_id="test_user",
            prompt="Test prompt",
            response="Test response",
            model="test-model",
            trace_id="trace123",
        )

        assert interaction_id is not None

        # Verify put_item was called
        mock_dynamodb.put_item.assert_called_once()
        call_args = mock_dynamodb.put_item.call_args[1]["Item"]

        assert call_args["interaction_id"] == interaction_id
        assert call_args["user_id"] == "test_user"
        assert call_args["prompt"] == "Test prompt"
        assert call_args["response"] == "Test response"
        assert call_args["model"] == "test-model"

    @pytest.mark.asyncio
    async def test_update_interaction_dynamodb(self, db_interface_prod, mock_dynamodb):
        """Test updating interaction in DynamoDB."""
        await db_interface_prod.update_interaction(
            interaction_id="test_id",
            response="Updated response",
            model="updated-model",
            tokens=100,
            latency_ms=500,
        )

        mock_dynamodb.update_item.assert_called_once()
        call_args = mock_dynamodb.update_item.call_args[1]

        assert call_args["Key"]["interaction_id"] == "test_id"
        assert ":response" in call_args["ExpressionAttributeValues"]
        assert ":model" in call_args["ExpressionAttributeValues"]
        assert ":tokens" in call_args["ExpressionAttributeValues"]
        assert ":latency" in call_args["ExpressionAttributeValues"]

    @pytest.mark.asyncio
    async def test_get_interaction_dynamodb(self, db_interface_prod, mock_dynamodb):
        """Test getting interaction from DynamoDB."""
        mock_dynamodb.get_item.return_value = {
            "Item": {"interaction_id": "test_id", "user_id": "test_user", "prompt": "Test prompt"}
        }

        interaction = await db_interface_prod.get_interaction("test_id")

        assert interaction is not None
        assert interaction["interaction_id"] == "test_id"
        assert interaction["user_id"] == "test_user"

        mock_dynamodb.get_item.assert_called_once_with(Key={"interaction_id": "test_id"})

    @pytest.mark.asyncio
    async def test_get_user_interactions_dynamodb(self, db_interface_prod, mock_dynamodb):
        """Test getting user interactions from DynamoDB."""
        mock_dynamodb.query.return_value = {
            "Items": [
                {"interaction_id": "id1", "prompt": "Prompt 1"},
                {"interaction_id": "id2", "prompt": "Prompt 2"},
            ]
        }

        interactions = await db_interface_prod.get_user_interactions("test_user", limit=5)

        assert len(interactions) == 2
        mock_dynamodb.query.assert_called_once()

        call_args = mock_dynamodb.query.call_args[1]
        assert call_args["ExpressionAttributeValues"][":uid"] == "test_user"
        assert call_args["Limit"] == 5

    @pytest.mark.asyncio
    async def test_health_check_dynamodb_success(self, db_interface_prod, mock_dynamodb):
        """Test DynamoDB health check success."""
        result = await db_interface_prod.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_dynamodb_failure(self, db_interface_prod, mock_dynamodb):
        """Test DynamoDB health check failure."""
        # Make table_status access raise an exception
        type(mock_dynamodb).table_status = PropertyMock(side_effect=Exception("Connection error"))

        with pytest.raises(Exception, match="Connection error"):
            await db_interface_prod.health_check()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
