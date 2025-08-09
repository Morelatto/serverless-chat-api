"""Core business logic."""

import os
import uuid
from typing import Any

import litellm
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings
from .storage import cache_key
from .storage.protocols import Cache, Repository

# Configure litellm
litellm.set_verbose = False
litellm.drop_params = True  # Drop unsupported params automatically


def _setup_llm_environment() -> str:
    """Setup LLM environment and return model string.

    Returns:
        Model string for litellm.
    """
    # Set API keys in environment for litellm
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
    elif settings.llm_provider == "openrouter" and settings.openrouter_api_key:
        os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key

    model = settings.llm_model
    logger.debug(f"LLM setup: provider={settings.llm_provider}, model={model}")
    return model


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def _call_llm(content: str) -> dict[str, Any]:
    """Call LLM with retry logic.

    Args:
        content: The prompt to send to the LLM.

    Returns:
        Dictionary with response text, model, and usage information.
    """
    model = _setup_llm_environment()

    try:
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": content}],
            timeout=30,
        )
    except Exception as e:
        logger.error(f"LLM call failed: {e}, model={model}, provider={settings.llm_provider}")
        raise

    # Extract usage
    usage_dict = {}
    if response.usage:
        usage_dict = response.usage.model_dump()
        # Try to calculate cost, but don't fail if model not mapped
        try:
            cost = litellm.completion_cost(completion_response=response)
            if cost is not None:
                from decimal import Decimal

                usage_dict["cost_usd"] = Decimal(str(cost))
        except (ValueError, KeyError, TypeError, Exception) as e:
            # Cost calculation not available for this model - that's OK
            logger.debug(f"Cost calculation not available for {response.model}: {e}")

    return {
        "text": response.choices[0].message.content,
        "model": response.model,
        "usage": usage_dict,
    }


async def process_message(
    user_id: str, content: str, repository: Repository, cache: Cache
) -> dict[str, Any]:
    """Process a chat message.

    Args:
        user_id: User identifier.
        content: Message content to process.
        repository: Repository instance for persistence.
        cache: Cache instance for caching.

    Returns:
        Dictionary with message ID, response content, model, and cache status.
    """
    # Check cache
    key = cache_key(user_id, content)
    cached = await cache.get(key)
    if cached:
        cached["cached"] = True
        return cached

    # Call LLM
    llm_response = await _call_llm(content)

    # Save to database with usage tracking
    message_id = str(uuid.uuid4())
    await repository.save(
        id=message_id,
        user_id=user_id,
        content=content,
        response=llm_response["text"],
        model=llm_response["model"],
        usage=llm_response["usage"],
    )

    # Log token usage for monitoring
    if llm_response["usage"]:
        logger.info(
            "Token usage",
            user_id=user_id,
            model=llm_response["model"],
            **llm_response["usage"],
        )

    # Prepare response
    result = {
        "id": message_id,
        "content": llm_response["text"],
        "model": llm_response["model"],
        "cached": False,
    }

    # Cache it
    await cache.set(key, result)

    return result


async def health_check(repository: Repository) -> dict[str, bool]:
    """Check health of all systems.

    Args:
        repository: Repository instance to check.

    Returns:
        Dictionary with health status of each component.
    """
    storage_ok = await repository.health_check()

    # Check LLM configuration (don't make actual call)
    llm_ok = True
    try:
        # Just verify configuration is valid
        model = _setup_llm_environment()
        if (settings.llm_provider == "gemini" and not settings.gemini_api_key) or (
            settings.llm_provider == "openrouter" and not settings.openrouter_api_key
        ):
            llm_ok = False
        logger.debug(
            f"LLM health check: provider={settings.llm_provider}, model={model}, ok={llm_ok}"
        )
    except (ValueError, KeyError, AttributeError) as e:
        logger.warning("LLM health check failed: {}", e)
        llm_ok = False

    return {"storage": storage_ok, "llm": llm_ok}
