"""LLM Provider abstractions using Strategy Pattern."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

import litellm
from loguru import logger

from .exceptions import ConfigurationError, LLMProviderError
from .retry import with_llm_retry
from .types import TokenUsage


def setup_litellm() -> None:
    """Setup litellm configuration."""
    import os

    litellm.set_verbose = False
    litellm.drop_params = True
    litellm.suppress_debug_info = True

    os.environ["LITELLM_LOG"] = "INFO"


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""

    model: str
    api_key: str | None = None
    timeout: int = 30
    temperature: float = 0.1
    seed: int = 42


@dataclass
class LLMResponse:
    """Standard response from LLM providers."""

    text: str
    model: str
    usage: TokenUsage


class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    async def complete(self, prompt: str) -> LLMResponse: ...
    async def health_check(self) -> bool: ...


class SimpleLLMProvider:
    """Base implementation for LLM providers using litellm."""

    def __init__(self, config: LLMConfig, provider_name: str) -> None:
        """Initialize the provider.

        Args:
            config: LLM configuration
            provider_name: Name of the provider for logging
        """
        self.config = config
        self.provider_name = provider_name

        if not config.api_key:
            raise ConfigurationError(f"{provider_name} API key is required")

        setup_litellm()

    async def complete(self, prompt: str) -> LLMResponse:
        """Generate completion for the given prompt."""
        return await self._complete_with_retry(prompt, self.provider_name)

    @with_llm_retry("SimpleLLMProvider", max_retries=3)
    async def _complete_with_retry(self, prompt: str, provider: str) -> LLMResponse:
        """Internal completion with retry."""
        try:
            response = await litellm.acompletion(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                timeout=self.config.timeout,
                api_key=self.config.api_key,
                temperature=self.config.temperature,
                seed=self.config.seed,
            )
        except Exception as e:
            logger.error(f"{self.provider_name} completion failed: {e}")
            raise LLMProviderError(f"{self.provider_name} completion failed: {e}") from e

        typed_usage = self._extract_usage(response)

        return LLMResponse(
            text=response.choices[0].message.content,
            model=response.model,
            usage=typed_usage,
        )

    def _extract_usage(self, response: Any) -> TokenUsage:
        """Extract usage data from response."""
        typed_usage: TokenUsage = {}

        if response.usage:
            usage_data = response.usage.model_dump()

            for field in ["prompt_tokens", "completion_tokens", "total_tokens"]:
                if field in usage_data:
                    typed_usage[field] = usage_data[field]  # type: ignore

            try:
                cost = litellm.completion_cost(completion_response=response)
                if cost is not None:
                    typed_usage["cost_usd"] = Decimal(str(cost))
            except Exception as e:  # noqa: BLE001
                logger.debug(f"Cost calculation not available for {response.model}: {e}")

        return typed_usage

    async def health_check(self) -> bool:
        """Check if provider is configured."""
        return bool(self.config.api_key)


def create_llm_provider() -> LLMProvider:
    """Factory function to create the appropriate LLM provider."""
    from .config import settings

    if settings.gemini_api_key:
        logger.info("Using Gemini provider")
        config = LLMConfig(
            model=settings.gemini_model,
            api_key=settings.gemini_api_key,
            timeout=settings.llm_timeout,
        )
        return SimpleLLMProvider(config, "Gemini")

    if settings.openrouter_api_key:
        logger.info("Using OpenRouter provider")
        config = LLMConfig(
            model=settings.openrouter_model or settings.openrouter_default_model,
            api_key=settings.openrouter_api_key,
            timeout=settings.llm_timeout,
        )
        return SimpleLLMProvider(config, "OpenRouter")

    raise ConfigurationError(
        "No LLM provider configured. Set either GEMINI_API_KEY or OPENROUTER_API_KEY"
    )
