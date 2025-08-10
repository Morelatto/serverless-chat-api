"""Test retry logic functionality."""

from unittest.mock import patch

import pytest

from chat_api.exceptions import LLMProviderError
from chat_api.retry import with_llm_retry


class TestRetryDecorator:
    """Test retry decorator functionality."""

    @pytest.mark.asyncio
    async def test_retry_decorator_success_first_try(self) -> None:
        """Test that decorator doesn't retry on success."""
        call_count = 0

        @with_llm_retry("TestProvider")
        async def test_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await test_function()

        assert result == "success"
        assert call_count == 1  # Called only once

    @pytest.mark.asyncio
    async def test_retry_decorator_success_after_retry(self) -> None:
        """Test successful retry after initial failure."""
        call_count = 0

        @with_llm_retry("TestProvider", max_retries=3)
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("First call fails")
            return "success after retry"

        result = await test_function()

        assert result == "success after retry"
        assert call_count == 2  # Called twice (initial + 1 retry)

    @pytest.mark.asyncio
    async def test_retry_decorator_timeout_error(self) -> None:
        """Test retry behavior with TimeoutError."""
        call_count = 0

        @with_llm_retry("TestProvider", max_retries=2)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Request timeout")

        with pytest.raises(LLMProviderError, match="TestProvider request timed out"):
            await test_function()

        # Should retry max_retries times
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_decorator_connection_error(self) -> None:
        """Test retry behavior with ConnectionError."""
        call_count = 0

        @with_llm_retry("TestProvider", max_retries=3)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Connection refused")

        with pytest.raises(LLMProviderError, match="Failed to connect to TestProvider API"):
            await test_function()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_decorator_generic_exception(self) -> None:
        """Test retry behavior with generic exceptions."""
        call_count = 0

        @with_llm_retry("TestProvider", max_retries=2)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Some API error")

        with pytest.raises(LLMProviderError, match="TestProvider API error: Some API error"):
            await test_function()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_decorator_custom_wait_times(self) -> None:
        """Test retry decorator with custom wait times."""
        call_times = []

        @with_llm_retry("TestProvider", max_retries=3, min_wait=0.001, max_wait=0.002)
        async def test_function():
            import time

            call_times.append(time.time())
            raise TimeoutError("Always fails")

        with pytest.raises(LLMProviderError):
            await test_function()

        # Should have made max_retries calls
        assert len(call_times) == 3

        # Check that there were delays between calls (though very small)
        if len(call_times) > 1:
            delay1 = call_times[1] - call_times[0]
            assert delay1 >= 0.001  # At least min_wait

    @pytest.mark.asyncio
    async def test_retry_decorator_preserves_function_metadata(self) -> None:
        """Test that decorator preserves function metadata."""

        @with_llm_retry("TestProvider")
        async def test_function():
            """Test function docstring."""
            return "test"

        # Function name and docstring should be preserved
        assert test_function.__name__ == "test_function"
        assert "Test function docstring" in test_function.__doc__

    @pytest.mark.asyncio
    async def test_retry_decorator_with_args_and_kwargs(self) -> None:
        """Test that decorator works with function arguments."""
        call_args = []

        @with_llm_retry("TestProvider")
        async def test_function(arg1, arg2, kwarg1=None, kwarg2=None):
            call_args.append((arg1, arg2, kwarg1, kwarg2))
            return f"result: {arg1}, {arg2}, {kwarg1}, {kwarg2}"

        result = await test_function("a", "b", kwarg1="c", kwarg2="d")

        assert result == "result: a, b, c, d"
        assert call_args == [("a", "b", "c", "d")]

    @pytest.mark.asyncio
    async def test_retry_decorator_multiple_retries_with_different_errors(self) -> None:
        """Test retry with different error types on different attempts."""
        call_count = 0
        errors = [TimeoutError("Timeout"), ConnectionError("Connection"), ValueError("Generic")]

        @with_llm_retry("TestProvider", max_retries=3)
        async def test_function():
            nonlocal call_count
            if call_count < len(errors):
                error = errors[call_count]
                call_count += 1
                raise error
            call_count += 1
            return "finally succeeded"

        result = await test_function()

        assert result == "finally succeeded"
        assert call_count == 4  # 3 failures + 1 success

    @pytest.mark.asyncio
    async def test_retry_decorator_logging_behavior(self) -> None:
        """Test that retry decorator logs errors appropriately."""

        @with_llm_retry("TestProvider", max_retries=2)
        async def test_function():
            raise TimeoutError("Test timeout")

        with patch("chat_api.retry.logger") as mock_logger:
            with pytest.raises(LLMProviderError):
                await test_function()

            # Should log each retry attempt
            assert mock_logger.error.call_count == 2

            # Check log messages
            log_calls = mock_logger.error.call_args_list
            assert "TestProvider call timed out" in str(log_calls[0])

    @pytest.mark.asyncio
    async def test_retry_decorator_zero_retries(self) -> None:
        """Test retry decorator with zero retries (fail fast)."""
        call_count = 0

        @with_llm_retry(
            "TestProvider",
            max_retries=1,
        )  # tenacity stop_after_attempt(1) = no retries
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Immediate failure")

        with pytest.raises(LLMProviderError):
            await test_function()

        assert call_count == 1  # Should only be called once

    @pytest.mark.asyncio
    async def test_retry_decorator_exception_chaining(self) -> None:
        """Test that original exceptions are properly chained."""

        @with_llm_retry("TestProvider", max_retries=1)
        async def test_function():
            raise TimeoutError("Original timeout error")

        try:
            await test_function()
        except LLMProviderError as e:
            # Should have original exception chained
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, TimeoutError)
            assert "Original timeout error" in str(e.__cause__)
        else:
            pytest.fail("Should have raised LLMProviderError")

    @pytest.mark.asyncio
    async def test_retry_decorator_with_complex_return_types(self) -> None:
        """Test retry decorator with complex return types."""

        @with_llm_retry("TestProvider")
        async def test_function():
            return {
                "text": "response",
                "model": "test-model",
                "usage": {"tokens": 10},
                "metadata": ["tag1", "tag2"],
            }

        result = await test_function()

        assert result["text"] == "response"
        assert result["model"] == "test-model"
        assert result["usage"]["tokens"] == 10
        assert result["metadata"] == ["tag1", "tag2"]


class TestRetryIntegration:
    """Test retry integration with actual provider patterns."""

    @pytest.mark.asyncio
    async def test_retry_with_provider_like_usage(self) -> None:
        """Test retry decorator used like in actual providers."""

        class MockProvider:
            def __init__(self, provider_name: str):
                self.provider_name = provider_name

            @with_llm_retry("MockProvider", max_retries=2)
            async def complete(self, prompt: str):
                # Simulate provider behavior
                if not hasattr(self, "_call_count"):
                    self._call_count = 0
                self._call_count += 1

                if self._call_count == 1:
                    raise ConnectionError("API temporarily unavailable")

                return {
                    "text": f"Response to: {prompt}",
                    "model": "mock-model",
                    "usage": {"total_tokens": len(prompt)},
                }

        provider = MockProvider("TestProvider")
        result = await provider.complete("Hello world")

        assert result["text"] == "Response to: Hello world"
        assert result["model"] == "mock-model"
        assert result["usage"]["total_tokens"] == 11  # len("Hello world")
        assert provider._call_count == 2  # Failed once, succeeded on retry
