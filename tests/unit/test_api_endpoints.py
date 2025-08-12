"""Tests for API endpoints and lifecycle."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI

from chat_api.chat import ChatService
from chat_api.exceptions import LLMProviderError, StorageError, ValidationError
from chat_api.middleware import create_token


class TestLifespan:
    """Test application lifecycle management."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_and_shutdown(self):
        """Test lifespan context manager initializes and cleans up."""
        from chat_api.api import lifespan

        app = FastAPI()

        with (
            patch("chat_api.api.create_repository") as mock_create_repo,
            patch("chat_api.api.create_cache") as mock_create_cache,
            patch("chat_api.api.create_llm_provider") as mock_create_provider,
        ):
            # Setup mocks
            mock_repo = AsyncMock()
            mock_cache = AsyncMock()
            mock_provider = Mock()

            mock_create_repo.return_value = mock_repo
            mock_create_cache.return_value = mock_cache
            mock_create_provider.return_value = mock_provider

            # Run lifespan
            async with lifespan(app):
                # Check service was created
                import chat_api.api

                assert chat_api.api._chat_service is not None
                assert isinstance(chat_api.api._chat_service, ChatService)

                # Verify startup was called
                mock_repo.startup.assert_called_once()
                mock_cache.startup.assert_called_once()

            # After context, verify shutdown was called
            mock_repo.shutdown.assert_called_once()
            mock_cache.shutdown.assert_called_once()

            # Service should be cleaned up
            assert chat_api.api._chat_service is None

    @pytest.mark.asyncio
    async def test_lifespan_handles_startup_error(self):
        """Test lifespan handles errors during startup."""
        from chat_api.api import lifespan

        app = FastAPI()

        with patch("chat_api.api.create_repository") as mock_create_repo:
            mock_repo = AsyncMock()
            mock_repo.startup.side_effect = Exception("Database connection failed")
            mock_create_repo.return_value = mock_repo

            with pytest.raises(Exception, match="Database connection failed"):
                async with lifespan(app):
                    pass


class TestGetChatService:
    """Test chat service dependency."""

    def test_get_chat_service_when_initialized(self):
        """Test getting chat service when it's initialized."""
        import chat_api.api
        from chat_api.api import get_chat_service

        mock_service = Mock(spec=ChatService)
        chat_api.api._chat_service = mock_service

        result = get_chat_service()
        assert result is mock_service

    def test_get_chat_service_when_not_initialized(self):
        """Test getting chat service raises error when not initialized."""
        import chat_api.api
        from chat_api.api import get_chat_service

        chat_api.api._chat_service = None

        with pytest.raises(RuntimeError, match="Service not initialized"):
            get_chat_service()


class TestChatEndpoint:
    """Test /chat endpoint error handling."""

    def test_chat_endpoint_llm_error(self):
        """Test chat endpoint handles LLM provider errors."""
        mock_service = Mock()
        mock_service.process_message = AsyncMock(side_effect=LLMProviderError("Provider down"))

        with patch("chat_api.api.get_chat_service", return_value=mock_service):
            from fastapi.testclient import TestClient

            from chat_api.api import app

            with TestClient(app) as client:
                token = create_token("test123")
                response = client.post(
                    "/chat", json="Hello", headers={"Authorization": f"Bearer {token}"}
                )

                assert response.status_code == 503
                assert "Service temporarily unavailable" in response.json()["detail"]

    def test_chat_endpoint_storage_error(self):
        """Test chat endpoint handles storage errors."""
        mock_service = Mock()
        mock_service.process_message = AsyncMock(side_effect=StorageError("Database down"))

        with patch("chat_api.api.get_chat_service", return_value=mock_service):
            from fastapi.testclient import TestClient

            from chat_api.api import app

            with TestClient(app) as client:
                token = create_token("test123")
                response = client.post(
                    "/chat", json="Hello", headers={"Authorization": f"Bearer {token}"}
                )

                assert response.status_code == 503
                assert "Storage service unavailable" in response.json()["detail"]

    def test_chat_endpoint_validation_error(self):
        """Test chat endpoint handles validation errors."""
        mock_service = Mock()
        mock_service.process_message = AsyncMock(side_effect=ValidationError("Invalid input"))

        with patch("chat_api.api.get_chat_service", return_value=mock_service):
            from fastapi.testclient import TestClient

            from chat_api.api import app

            with TestClient(app) as client:
                token = create_token("test123")
                response = client.post(
                    "/chat", json="Hello", headers={"Authorization": f"Bearer {token}"}
                )

                assert response.status_code == 400
                assert "Invalid input" in response.json()["detail"]

    def test_chat_endpoint_unexpected_error(self):
        """Test chat endpoint handles unexpected errors."""
        mock_service = Mock()
        mock_service.process_message = AsyncMock(side_effect=RuntimeError("Unexpected"))

        with patch("chat_api.api.get_chat_service", return_value=mock_service):
            from fastapi.testclient import TestClient

            from chat_api.api import app

            with TestClient(app) as client:
                token = create_token("test123")
                response = client.post(
                    "/chat", json="Hello", headers={"Authorization": f"Bearer {token}"}
                )

                assert response.status_code == 500
                assert "Internal server error" in response.json()["detail"]


class TestHistoryEndpoint:
    """Test /history endpoint."""

    def test_history_endpoint_invalid_user_id(self):
        """Test history endpoint validates user ID."""
        mock_service = Mock()
        mock_service.get_history = AsyncMock(return_value=[])

        with patch("chat_api.api.get_chat_service", return_value=mock_service):
            from fastapi.testclient import TestClient

            from chat_api.api import app

            with TestClient(app) as client:
                # Too long user ID
                response = client.get(f"/history/{'x' * 101}")
                assert response.status_code == 400
                assert "Invalid user ID" in response.json()["detail"]

    def test_history_endpoint_limit_validation(self):
        """Test history endpoint validates limit parameter."""
        mock_service = Mock()
        mock_service.get_history = AsyncMock(return_value=[])

        with patch("chat_api.api.get_chat_service", return_value=mock_service):
            from fastapi.testclient import TestClient

            from chat_api.api import app

            with TestClient(app) as client:
                # Limit too high
                response = client.get("/history/test_user?limit=101")
                assert response.status_code == 422  # Validation error

                # Limit too low
                response = client.get("/history/test_user?limit=0")
                assert response.status_code == 422  # Validation error


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_endpoint_all_healthy(self):
        """Test health endpoint when all services are healthy."""
        mock_service = Mock()
        mock_service.health_check = AsyncMock(
            return_value={"storage": True, "llm": True, "cache": True}
        )

        with patch("chat_api.api.get_chat_service", return_value=mock_service):
            from fastapi.testclient import TestClient

            from chat_api.api import app

            with TestClient(app) as client:
                response = client.get("/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert all(data["services"].values())

    def test_health_endpoint_partial_failure(self):
        """Test health endpoint when some services are unhealthy."""
        mock_service = Mock()
        mock_service.health_check = AsyncMock(
            return_value={"storage": True, "llm": False, "cache": True}
        )

        with patch("chat_api.api.get_chat_service", return_value=mock_service):
            from fastapi.testclient import TestClient

            from chat_api.api import app

            with TestClient(app) as client:
                response = client.get("/health")
                assert response.status_code == 503
                data = response.json()
                assert data["status"] == "unhealthy"
                assert data["services"]["llm"] is False

    def test_health_endpoint_detailed(self):
        """Test health endpoint with detailed flag."""
        mock_service = Mock()
        mock_service.health_check = AsyncMock(
            return_value={"storage": True, "llm": True, "cache": True}
        )

        with patch("chat_api.api.get_chat_service", return_value=mock_service):
            from fastapi.testclient import TestClient

            from chat_api.api import app

            with TestClient(app) as client:
                response = client.get("/health?detailed=true")
                assert response.status_code == 200
                data = response.json()
                assert "version" in data
                assert "environment" in data
                assert data["version"] == "1.0.0"
