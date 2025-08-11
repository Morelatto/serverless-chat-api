"""Simple retry logic tests."""

import pytest

from chat_api.retry import with_llm_retry


@pytest.mark.asyncio
async def test_success_no_retry_needed():
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
async def test_connection_error_retries():
    """Test that connection errors are retried."""
    call_count = 0

    @with_llm_retry("TestProvider")
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
async def test_timeout_error_retries():
    """Test that timeout errors are retried."""
    call_count = 0

    @with_llm_retry("TestProvider")
    async def timeout_then_succeed():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("Request timed out")
        return "success"

    result = await timeout_then_succeed()
    assert result == "success"
    assert call_count == 2


@pytest.mark.asyncio
async def test_non_retryable_error():
    """Test that non-retryable errors are raised immediately."""
    call_count = 0

    @with_llm_retry("TestProvider")
    async def raise_value_error():
        nonlocal call_count
        call_count += 1
        raise ValueError("Invalid value")

    with pytest.raises(ValueError, match="Invalid value"):
        await raise_value_error()

    assert call_count == 1  # Should not retry
