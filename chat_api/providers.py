"""LLM Provider abstractions using Strategy Pattern."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

import litellm
from loguru import logger

from .exceptions import ConfigurationError
from .retry import with_llm_retry
from .types import TokenUsage


def setup_litellm() -> None:
    """Setup litellm configuration."""
    import os

    litellm.set_verbose = False
    litellm.drop_params = True
    litellm.suppress_debug_info = True

    # Enable observability features
    os.environ["LITELLM_LOG"] = "INFO"  # Enable for metrics


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""

    model: str
    api_key: str | None = None
    timeout: int = 30
    temperature: float = 0.1  # Low temperature for consistent responses
    seed: int = 42  # Fixed seed for reproducibility


@dataclass
class LLMResponse:
    """Standard response from LLM providers."""

    text: str
    model: str
    usage: TokenUsage


class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    async def complete(self, prompt: str) -> LLMResponse:
        """Generate completion for the given prompt."""
        ...

    async def health_check(self) -> bool:
        """Check if the provider is configured and accessible."""
        ...


class GeminiProvider:
    """Gemini LLM provider implementation."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        if not config.api_key:
            raise ConfigurationError("Gemini API key is required")

        # Configure litellm
        setup_litellm()

    @with_llm_retry(
        provider_name="Gemini",
        max_retries=3,
        min_wait=1,
        max_wait=10,
    )
    async def complete(self, prompt: str) -> LLMResponse:
        """Generate completion using Gemini."""
        response = await litellm.acompletion(
            model=self.config.model,
            messages=[{"role": "user", "content": prompt}],
            timeout=self.config.timeout,
            api_key=self.config.api_key,
            temperature=self.config.temperature,
            seed=self.config.seed,
        )

        # Extract usage and calculate cost if available
        from .types import TokenUsage

        # Build properly typed usage dict
        typed_usage: TokenUsage = {}
        if response.usage:
            usage_data = response.usage.model_dump()
            if "prompt_tokens" in usage_data:
                typed_usage["prompt_tokens"] = usage_data["prompt_tokens"]
            if "completion_tokens" in usage_data:
                typed_usage["completion_tokens"] = usage_data["completion_tokens"]
            if "total_tokens" in usage_data:
                typed_usage["total_tokens"] = usage_data["total_tokens"]

            # Try to calculate cost
            try:
                cost = litellm.completion_cost(completion_response=response)
                if cost is not None:
                    typed_usage["cost_usd"] = Decimal(str(cost))
            except (ValueError, KeyError, TypeError, Exception) as e:
                logger.debug(f"Cost calculation not available for {response.model}: {e}")

        return LLMResponse(
            text=response.choices[0].message.content,
            model=response.model,
            usage=typed_usage,
        )

    async def health_check(self) -> bool:
        """Check Gemini provider health."""
        return bool(self.config.api_key)


class OpenRouterProvider:
    """OpenRouter LLM provider implementation."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        if not config.api_key:
            raise ConfigurationError("OpenRouter API key is required")

        # Configure litellm
        setup_litellm()

    @with_llm_retry(
        provider_name="OpenRouter",
        max_retries=3,
        min_wait=1,
        max_wait=10,
    )
    async def complete(self, prompt: str) -> LLMResponse:
        """Generate completion using OpenRouter."""
        response = await litellm.acompletion(
            model=self.config.model,
            messages=[{"role": "user", "content": prompt}],
            timeout=self.config.timeout,
            api_key=self.config.api_key,
            temperature=self.config.temperature,
            seed=self.config.seed,
        )

        # Extract usage and calculate cost if available
        from .types import TokenUsage

        # Build properly typed usage dict
        typed_usage: TokenUsage = {}
        if response.usage:
            usage_data = response.usage.model_dump()
            if "prompt_tokens" in usage_data:
                typed_usage["prompt_tokens"] = usage_data["prompt_tokens"]
            if "completion_tokens" in usage_data:
                typed_usage["completion_tokens"] = usage_data["completion_tokens"]
            if "total_tokens" in usage_data:
                typed_usage["total_tokens"] = usage_data["total_tokens"]

            # Try to calculate cost
            try:
                cost = litellm.completion_cost(completion_response=response)
                if cost is not None:
                    typed_usage["cost_usd"] = Decimal(str(cost))
            except (ValueError, KeyError, TypeError, Exception) as e:
                logger.debug(f"Cost calculation not available for {response.model}: {e}")

        return LLMResponse(
            text=response.choices[0].message.content,
            model=response.model,
            usage=typed_usage,
        )

    async def health_check(self) -> bool:
        """Check OpenRouter provider health."""
        return bool(self.config.api_key)


def create_llm_provider(
    provider_type: str,
    model: str,
    api_key: str | None = None,
    **kwargs: Any,
) -> LLMProvider:
    """Factory function to create LLM provider instances.

    Args:
        provider_type: Type of provider ('gemini', 'openrouter').
        model: Model identifier.
        api_key: API key for the provider.
        **kwargs: Additional configuration options.

    Returns:
        LLMProvider instance.

    Raises:
        ConfigurationError: If provider type is unknown or configuration is invalid.

    """
    config = LLMConfig(
        model=model,
        api_key=api_key,
        timeout=kwargs.get("timeout", 30),
    )

    providers = {
        "gemini": GeminiProvider,
        "openrouter": OpenRouterProvider,
    }

    provider_class = providers.get(provider_type.lower())
    if not provider_class:
        raise ConfigurationError(
            f"Unknown provider type: {provider_type}. Must be 'gemini' or 'openrouter'"
        )

    return provider_class(config)  # type: ignore
