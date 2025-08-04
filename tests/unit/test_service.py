"""
Unit tests for ChatService and related components.
Tests caching, circuit breaker, and service orchestration.
"""
from unittest.mock import AsyncMock, patch

import pytest

from src.chat.service import ChatService, CircuitBreaker, CircuitState, ResponseCache


class TestResponseCache:
    """Test the ResponseCache implementation."""

    def test_cache_initialization(self):
        """Test cache initializes correctly."""
        cache = ResponseCache(ttl_seconds=3600)
        assert cache.ttl == 3600
        assert cache.cache == {}

    def test_cache_key_generation(self):
        """Test cache key generation is consistent."""
        cache = ResponseCache()
        key1 = cache._get_key("Hello World")
        key2 = cache._get_key("hello world")  # Case insensitive
        key3 = cache._get_key("  Hello World  ")  # Strips whitespace

        assert key1 == key2 == key3
        assert isinstance(key1, str)
        assert len(key1) == 32  # MD5 hex digest length

    def test_cache_set_and_get(self):
        """Test setting and getting cached values."""
        cache = ResponseCache(ttl_seconds=3600)

        cache.set("test prompt", "test response")
        result = cache.get("test prompt")

        assert result == "test response"

    def test_cache_expiration(self):
        """Test cache entries expire after TTL."""
        import time

        cache = ResponseCache(ttl_seconds=0.1)  # Very short TTL for testing

        cache.set("test prompt", "test response")

        # Should be available immediately
        assert cache.get("test prompt") == "test response"

        # Wait for expiration
        time.sleep(0.2)

        # Should be expired now
        result = cache.get("test prompt")
        assert result is None

    def test_cache_size_limit(self):
        """Test cache size limiting works."""
        cache = ResponseCache()

        # Add more than 1000 entries
        for i in range(1005):
            cache.set(f"prompt_{i}", f"response_{i}")

        # Cache should not exceed 1000 entries
        assert len(cache.cache) <= 1000

    def test_cache_case_insensitive(self):
        """Test cache is case insensitive."""
        cache = ResponseCache()

        cache.set("Hello World", "response")
        assert cache.get("hello world") == "response"
        assert cache.get("HELLO WORLD") == "response"


class TestCircuitBreaker:
    """Test the CircuitBreaker implementation."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_initialization(self):
        """Test circuit breaker initializes in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10)

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 10

    @pytest.mark.asyncio
    async def test_successful_call_in_closed_state(self):
        """Test successful calls in CLOSED state."""
        cb = CircuitBreaker()

        async def success_func():
            return "success"

        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_failure_counting(self):
        """Test failure counting increments correctly."""
        cb = CircuitBreaker(failure_threshold=3)

        async def failing_func():
            raise Exception("Test failure")

        # First failure
        with pytest.raises(Exception):
            await cb.call(failing_func)
        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED

        # Second failure
        with pytest.raises(Exception):
            await cb.call(failing_func)
        assert cb.failure_count == 2
        assert cb.state == CircuitState.CLOSED

        # Third failure - should open circuit
        with pytest.raises(Exception):
            await cb.call(failing_func)
        assert cb.failure_count == 3
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_state_rejects_calls(self):
        """Test OPEN state rejects calls immediately."""
        cb = CircuitBreaker(failure_threshold=1)

        async def failing_func():
            raise Exception("Test failure")

        # Open the circuit
        with pytest.raises(Exception):
            await cb.call(failing_func)
        assert cb.state == CircuitState.OPEN

        # Should reject without calling function
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await cb.call(failing_func)

    @pytest.mark.asyncio
    async def test_half_open_recovery(self):
        """Test recovery from OPEN to HALF_OPEN to CLOSED."""
        import time

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)  # Short timeout for testing

        async def failing_func():
            raise Exception("Test failure")

        async def success_func():
            return "success"

        # Open the circuit
        with pytest.raises(Exception):
            await cb.call(failing_func)
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.2)

        # Should enter HALF_OPEN and succeed
        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0


class TestChatService:
    """Test the ChatService orchestration."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for ChatService."""
        with patch("src.chat.service.DatabaseInterface") as mock_db, patch(
            "src.chat.service.LLMProviderFactory"
        ) as mock_llm, patch("src.chat.service.settings") as mock_settings:
            # Configure mock settings
            mock_settings.CACHE_TTL_SECONDS = 3600
            mock_settings.CIRCUIT_BREAKER_THRESHOLD = 5
            mock_settings.CIRCUIT_BREAKER_TIMEOUT = 60
            mock_settings.ENABLE_CACHE = True

            # Configure mock database
            mock_db_instance = AsyncMock()
            mock_db_instance.save_interaction = AsyncMock(return_value="interaction_123")
            mock_db_instance.update_interaction = AsyncMock()
            mock_db_instance.health_check = AsyncMock()
            mock_db.return_value = mock_db_instance

            # Configure mock LLM factory
            mock_llm_instance = AsyncMock()
            mock_llm_instance.generate = AsyncMock(
                return_value={
                    "response": "Generated response",
                    "model": "mock-model",
                    "tokens": 100,
                    "latency_ms": 500,
                }
            )
            mock_llm_instance.health_check = AsyncMock()
            mock_llm.return_value = mock_llm_instance

            yield {"db": mock_db_instance, "llm": mock_llm_instance, "settings": mock_settings}

    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_dependencies):
        """Test ChatService initializes correctly."""
        service = ChatService()

        assert service.db is not None
        assert service.llm_factory is not None
        assert service.cache is not None
        assert service.circuit_breaker is not None

    @pytest.mark.asyncio
    async def test_process_prompt_uncached(self, mock_dependencies):
        """Test processing a new prompt (not cached)."""
        service = ChatService()

        result = await service.process_prompt(
            user_id="user123", prompt="Test prompt", trace_id="trace123"
        )

        # Verify result structure
        assert result["interaction_id"] == "interaction_123"
        assert result["response"] == "Generated response"
        assert result["model"] == "mock-model"
        assert result["cached"] is False
        assert "timestamp" in result
        assert "latency_ms" in result

        # Verify database calls
        mock_dependencies["db"].save_interaction.assert_called_once()
        mock_dependencies["db"].update_interaction.assert_called_once()

        # Verify LLM call
        mock_dependencies["llm"].generate.assert_called_once_with(
            prompt="Test prompt", trace_id="trace123"
        )

    @pytest.mark.asyncio
    async def test_process_prompt_cached(self, mock_dependencies):
        """Test processing a cached prompt."""
        service = ChatService()

        # First call to populate cache
        await service.process_prompt(user_id="user123", prompt="Test prompt", trace_id="trace123")

        # Reset mocks
        mock_dependencies["db"].save_interaction.reset_mock()
        mock_dependencies["llm"].generate.reset_mock()

        # Second call should use cache
        result = await service.process_prompt(
            user_id="user123", prompt="Test prompt", trace_id="trace456"
        )

        assert result["cached"] is True
        assert result["model"] == "cache"
        assert result["response"] == "Generated response"

        # LLM should not be called for cached response
        mock_dependencies["llm"].generate.assert_not_called()

        # Database should still save the interaction
        mock_dependencies["db"].save_interaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_prompt_with_error(self, mock_dependencies):
        """Test error handling in prompt processing."""
        service = ChatService()

        # Make LLM raise an error
        mock_dependencies["llm"].generate.side_effect = Exception("LLM Error")

        with pytest.raises(Exception, match="LLM Error"):
            await service.process_prompt(
                user_id="user123", prompt="Test prompt", trace_id="trace123"
            )

        # Verify error was logged to database
        mock_dependencies["db"].update_interaction.assert_called_with(
            interaction_id="interaction_123", response=None, model="error", error="LLM Error"
        )

    @pytest.mark.asyncio
    async def test_cache_disabled(self, mock_dependencies):
        """Test behavior when cache is disabled."""
        mock_dependencies["settings"].ENABLE_CACHE = False
        service = ChatService()

        # First call
        await service.process_prompt(user_id="user123", prompt="Test prompt", trace_id="trace123")

        # Reset mocks
        mock_dependencies["llm"].generate.reset_mock()

        # Second call should not use cache
        await service.process_prompt(user_id="user123", prompt="Test prompt", trace_id="trace456")

        # LLM should be called both times
        mock_dependencies["llm"].generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_dependencies(self, mock_dependencies):
        """Test dependency health checks."""
        service = ChatService()

        # All dependencies healthy
        result = await service.check_dependencies()

        assert result["database"] is True
        assert result["llm_provider"] is True
        assert result["cache"] is True

        # Test with failing dependencies
        mock_dependencies["db"].health_check.side_effect = Exception("DB Error")
        mock_dependencies["llm"].health_check.side_effect = Exception("LLM Error")

        result = await service.check_dependencies()

        assert result["database"] is False
        assert result["llm_provider"] is False
        assert result["cache"] is True  # Always healthy (in-memory)

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, mock_dependencies):
        """Test circuit breaker integration with service."""
        service = ChatService()
        service.circuit_breaker.failure_threshold = 2

        # Make LLM fail
        mock_dependencies["llm"].generate.side_effect = Exception("LLM Error")

        # First failure
        with pytest.raises(Exception):
            await service.process_prompt("user123", "prompt1", "trace1")

        # Second failure - should open circuit
        with pytest.raises(Exception):
            await service.process_prompt("user123", "prompt2", "trace2")

        # Third call should be rejected by circuit breaker
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await service.process_prompt("user123", "prompt3", "trace3")

        # Verify LLM was only called twice (not for the third attempt)
        assert mock_dependencies["llm"].generate.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
