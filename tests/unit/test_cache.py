"""Unit tests for cache service."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from src.shared.cache import CacheService, InMemoryCacheBackend


class TestInMemoryCacheBackend:
    """Test in-memory cache backend."""

    @pytest.mark.asyncio
    async def test_should_store_and_retrieve_value(self):
        """Should store and retrieve cached value."""
        backend = InMemoryCacheBackend()
        
        await backend.set("test_key", "test_value", ttl=60)
        result = await backend.get("test_key")
        
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_should_return_none_for_missing_key(self):
        """Should return None for missing key."""
        backend = InMemoryCacheBackend()
        
        result = await backend.get("missing_key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_should_expire_values(self):
        """Should expire values after TTL."""
        backend = InMemoryCacheBackend()
        
        # Set with 0 TTL (already expired)
        backend.cache["expired_key"] = {
            "value": "expired_value",
            "expires_at": datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
        }
        
        result = await backend.get("expired_key")
        
        assert result is None
        assert "expired_key" not in backend.cache

    @pytest.mark.asyncio
    async def test_should_delete_value(self):
        """Should delete cached value."""
        backend = InMemoryCacheBackend()
        
        await backend.set("test_key", "test_value", ttl=60)
        await backend.delete("test_key")
        result = await backend.get("test_key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_should_check_existence(self):
        """Should check if key exists."""
        backend = InMemoryCacheBackend()
        
        await backend.set("test_key", "test_value", ttl=60)
        
        assert await backend.exists("test_key") is True
        assert await backend.exists("missing_key") is False

    @pytest.mark.asyncio
    async def test_should_evict_oldest_on_max_size(self):
        """Should evict oldest entry when max size reached."""
        backend = InMemoryCacheBackend(max_size=2)
        
        await backend.set("key1", "value1", ttl=60)
        await backend.set("key2", "value2", ttl=60)
        await backend.set("key3", "value3", ttl=60)  # Should evict key1
        
        assert len(backend.cache) == 2
        assert await backend.get("key2") == "value2"
        assert await backend.get("key3") == "value3"


class TestCacheService:
    """Test high-level cache service."""

    @pytest.mark.asyncio
    async def test_should_generate_consistent_keys(self):
        """Should generate consistent cache keys."""
        service = CacheService()
        
        key1 = service._generate_key("Hello World")
        key2 = service._generate_key("hello world")  # Case insensitive
        key3 = service._generate_key("  Hello World  ")  # Trimmed
        
        assert key1 == key2
        assert key1 == key3

    @pytest.mark.asyncio
    async def test_should_cache_and_retrieve_response(self):
        """Should cache and retrieve response."""
        backend = InMemoryCacheBackend()
        service = CacheService(backend=backend, ttl_seconds=60)
        
        await service.set_response("test prompt", "test response")
        result = await service.get_response("test prompt")
        
        assert result == "test response"

    @pytest.mark.asyncio
    async def test_should_respect_enable_cache_flag(self):
        """Should respect enable_cache flag."""
        backend = InMemoryCacheBackend()
        service = CacheService(backend=backend, enable_cache=False)
        
        await service.set_response("test prompt", "test response")
        result = await service.get_response("test prompt")
        
        assert result is None  # Cache disabled

    @pytest.mark.asyncio
    async def test_should_invalidate_cached_response(self):
        """Should invalidate cached response."""
        backend = InMemoryCacheBackend()
        service = CacheService(backend=backend)
        
        await service.set_response("test prompt", "test response")
        await service.invalidate("test prompt")
        result = await service.get_response("test prompt")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_should_handle_backend_failure_gracefully(self):
        """Should handle backend failures gracefully."""
        # Create a failing backend
        class FailingBackend:
            async def get(self, key: str) -> None:
                raise Exception("Backend failed")
            
            async def set(self, key: str, value: str, ttl: int) -> None:
                raise Exception("Backend failed")
            
            async def health_check(self) -> bool:
                return False
        
        service = CacheService(backend=FailingBackend())
        
        # Should not raise, just return None
        result = await service.get_response("test")
        assert result is None
        
        # Should not raise
        await service.set_response("test", "response")

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Should perform health check."""
        backend = InMemoryCacheBackend()
        service = CacheService(backend=backend)
        
        health = await service.health_check()
        
        assert health["primary"] is True
        assert health.get("fallback") is False  # No fallback for in-memory