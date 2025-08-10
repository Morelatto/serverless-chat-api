"""Mock LLM provider for testing purposes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from chat_api.exceptions import LLMProviderError
from chat_api.providers import LLMConfig, LLMResponse

if TYPE_CHECKING:
    from chat_api.types import TokenUsage


class MockProvider:
    """Mock LLM provider for testing."""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig(model="mock-model")
        self.call_count = 0
        self.responses: list[str] = []
        self.should_fail = False

    def set_response(self, response: str) -> None:
        """Set the response for the next call."""
        self.responses.append(response)

    def set_failure(self, should_fail: bool = True) -> None:
        """Configure the provider to fail on next call."""
        self.should_fail = should_fail

    async def complete(self, prompt: str) -> LLMResponse:
        """Generate mock completion."""
        self.call_count += 1

        if self.should_fail:
            raise LLMProviderError("Mock provider configured to fail")

        # Use configured response or default
        text = self.responses.pop(0) if self.responses else f"Mock response to: {prompt[:50]}..."

        usage: TokenUsage = {
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": len(text.split()),
            "total_tokens": len(prompt.split()) + len(text.split()),
        }

        return LLMResponse(
            text=text,
            model=self.config.model,
            usage=usage,
        )

    async def health_check(self) -> bool:
        """Mock health check."""
        return not self.should_fail
