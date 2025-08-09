"""Core business logic."""

import os
import uuid
from typing import Any

import litellm
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings
from .storage import cache_key, get_cached, save_message, set_cached
from .storage import health_check as storage_health

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

    return settings.llm_model


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def _call_llm(content: str) -> dict[str, Any]:
    """Call LLM with retry logic.

    Args:
        content: The prompt to send to the LLM.

    Returns:
        Dictionary with response text, model, and usage information.
    """
    model = _setup_llm_environment()

    response = await litellm.acompletion(
        model=model,
        messages=[{"role": "user", "content": content}],
        timeout=30,
    )

    # Extract usage and calculate cost
    usage_dict = {}
    if response.usage:
        usage_dict = response.usage.model_dump()
        try:
            # Calculate cost using LiteLLM's built-in function
            cost = litellm.completion_cost(completion_response=response)
            # Convert float to Decimal for DynamoDB compatibility
            from decimal import Decimal

            usage_dict["cost_usd"] = Decimal(str(cost)) if cost is not None else None
        except (ValueError, KeyError, TypeError):
            # Cost calculation not available for this model
            logger.debug("Cost calculation not available for model: {}", response.model)

    return {
        "text": response.choices[0].message.content,
        "model": response.model,
        "usage": usage_dict,
    }


async def process_message(user_id: str, content: str) -> dict[str, Any]:
    """Process a chat message.

    Args:
        user_id: User identifier.
        content: Message content to process.

    Returns:
        Dictionary with message ID, response content, model, and cache status.
    """
    # Check cache
    key = cache_key(user_id, content)
    cached = await get_cached(key)
    if cached:
        cached["cached"] = True
        return cached

    # Call LLM
    llm_response = await _call_llm(content)

    # Save to database with usage tracking
    message_id = str(uuid.uuid4())
    await save_message(
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
    await set_cached(key, result)

    return result


async def health_check() -> dict[str, bool]:
    """Check health of all systems.

    Returns:
        Dictionary with health status of each component.
    """
    storage_ok = await storage_health()

    # Test LLM connection
    llm_ok = True
    try:
        await _call_llm("test")
    except (ValueError, ConnectionError, TimeoutError) as e:
        logger.warning("LLM health check failed: {}", e)
        llm_ok = False

    return {"storage": storage_ok, "llm": llm_ok}
