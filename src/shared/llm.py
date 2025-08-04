"""Multi-provider LLM integration with automatic failover."""

import logging
import os
import time
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """Factory for creating and managing LLM providers."""

    def __init__(self) -> None:
        """Initialize available providers based on API keys."""
        self.providers = {}
        self.primary_provider = os.getenv("LLM_PROVIDER", "gemini")
        self.fallback_enabled = os.getenv("LLM_FALLBACK", "true").lower() == "true"

        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            self.providers["gemini"] = GeminiProvider(gemini_key)
            logger.info("Gemini provider initialized")

        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            self.providers["openrouter"] = OpenRouterProvider(openrouter_key)  # type: ignore[assignment]
            logger.info("OpenRouter provider initialized")

        if not self.providers:
            logger.error("No LLM API keys found - at least one provider must be configured")

    async def generate(self, prompt: str, trace_id: str | None = None) -> dict[str, Any]:
        """Generate response with automatic fallback."""
        start_time = time.time()

        # Try primary provider
        if self.primary_provider in self.providers:
            try:
                result = await self.providers[self.primary_provider].generate(prompt)
                result["latency_ms"] = int((time.time() - start_time) * 1000)

                logger.info(
                    {
                        "event": "llm_success",
                        "provider": self.primary_provider,
                        "trace_id": trace_id,
                        "latency_ms": result["latency_ms"],
                    }
                )

                return result

            except Exception as e:
                logger.warning(f"Primary provider {self.primary_provider} failed: {e}")

                if not self.fallback_enabled:
                    raise e

        # Try fallback providers
        for name, provider in self.providers.items():
            if name != self.primary_provider:
                try:
                    logger.info(f"Attempting fallback to {name}")
                    result = await provider.generate(prompt)
                    result["latency_ms"] = int((time.time() - start_time) * 1000)
                    result["fallback"] = True

                    logger.info(
                        {
                            "event": "llm_fallback_success",
                            "provider": name,
                            "trace_id": trace_id,
                            "latency_ms": result["latency_ms"],
                        }
                    )

                    return result

                except Exception as e:
                    logger.warning(f"Fallback provider {name} failed: {e}")
                    continue

        raise Exception("All LLM providers failed")

    async def health_check(self) -> bool:
        """Check if at least one provider is healthy."""
        for _name, provider in self.providers.items():
            try:
                await provider.health_check()
                return True
            except Exception:
                continue
        return False


class GeminiProvider:
    """Google Gemini API provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        import google.generativeai as genai

        genai.configure(api_key=api_key)  # type: ignore[attr-defined]
        self.model = genai.GenerativeModel("gemini-pro")  # type: ignore[attr-defined]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=10))
    async def generate(self, prompt: str) -> dict[str, Any]:
        """Generate response from Gemini."""
        try:
            response = self.model.generate_content(prompt)

            return {
                "response": response.text,
                "model": "gemini-pro",
                "tokens": getattr(response.usage_metadata, "total_token_count", 0)
                if hasattr(response, "usage_metadata")
                else 0,
            }
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise e

    async def health_check(self) -> bool:
        """Check Gemini availability."""
        try:
            await self.generate("test")
            return True
        except Exception:
            return False


class OpenRouterProvider:
    """OpenRouter API provider using OpenAI SDK."""

    def __init__(self, api_key: str):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={"HTTP-Referer": "https://github.com/Morelatto/AWSDeployTest"},
        )
        self.model = os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=10))
    async def generate(self, prompt: str) -> dict[str, Any]:
        """Generate response from OpenRouter."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000,
            )

            return {
                "response": response.choices[0].message.content,
                "model": response.model,
                "tokens": response.usage.total_tokens if response.usage else 0,
            }
        except Exception as e:
            logger.error(f"OpenRouter generation failed: {e}")
            raise

    async def health_check(self) -> bool:
        """Check OpenRouter availability."""
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
