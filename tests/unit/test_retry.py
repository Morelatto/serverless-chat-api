"""Simple retry logic tests - focused on actual usage patterns."""

import pytest

from chat_api.exceptions import LLMProviderError
from chat_api.retry import with_llm_retry


class TestRetrySimple:
    """Test simplified retry decorator functionality."""

    @pytest.mark.asyncio
    async def test_success_no_retry_needed(self) -> None:
        """Test that successful calls don't trigger retries."""
        call_count = 0

        @with_llm_retry("TestProvider")
        async def success_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await success_function()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_connection_error_retries_then_succeeds(self) -> None:
        """Test that connection errors are retried."""
        call_count = 0

        @with_llm_retry("TestProvider", max_retries=3)
        async def retry_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success after retries"

        result = await retry_then_succeed()
        assert result == "success after retries"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_error_becomes_llm_error(self) -> None:
        """Test that non-retryable errors become LLMProviderError."""

        @with_llm_retry("TestProvider")
        async def non_retryable_error():
            raise ValueError("Invalid API response")

        with pytest.raises(LLMProviderError, match="TestProvider API error: Invalid API response"):
            await non_retryable_error()

    @pytest.mark.asyncio
    async def test_timeout_error_retries(self) -> None:
        """Test that timeout errors are retried."""
        call_count = 0

        @with_llm_retry("TestProvider", max_retries=2)
        async def timeout_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("Request timeout")
            return "success after timeout"

        result = await timeout_then_succeed()
        assert result == "success after timeout"
        assert call_count == 2
