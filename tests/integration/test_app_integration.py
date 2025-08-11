"""Integration tests for components working together."""

import os
from unittest.mock import AsyncMock, patch

import pytest

from chat_api.factory import ServiceFactory


@pytest.mark.asyncio
async def test_service_factory_creates_complete_service() -> None:
    """Test that ServiceFactory creates a working ChatService."""
    with (
        patch.dict(
            os.environ,
            {
                "CHAT_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
                "CHAT_OPENROUTER_API_KEY": "test-key",
                "CHAT_LLM_PROVIDER": "openrouter",
                "AWS_LAMBDA_FUNCTION_NAME": "",  # Not in Lambda
            },
            clear=True,
        ),
        patch("chat_api.storage.SQLiteRepository.startup"),
        patch("chat_api.storage.SQLiteRepository.shutdown"),
        patch("chat_api.storage.SQLiteRepository.health_check", return_value=True),
        patch("chat_api.storage.InMemoryCache.startup"),
        patch("chat_api.storage.InMemoryCache.shutdown"),
        patch("chat_api.providers.create_llm_provider") as mock_create_llm,
    ):
        # Mock LLM provider
        mock_llm = AsyncMock()
        mock_llm.health_check.return_value = True
        mock_create_llm.return_value = mock_llm

        # Create service through factory
        service = await ServiceFactory.create_for_environment()

        # Verify service has all required components
        assert service is not None
        assert hasattr(service, "repository")
        assert hasattr(service, "cache")
        assert hasattr(service, "llm_provider")

        # Test health check works
        health_status = await service.health_check()
        assert health_status["storage"] is True
        assert health_status["llm"] is True

        # Clean up
        await ServiceFactory.shutdown_service(service)
