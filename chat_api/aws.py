"""AWS Lambda handler for the Chat API."""

from typing import Any

from loguru import logger
from mangum import Mangum

from chat_api import app

logger.add(lambda msg: print(msg, end=""))
handler = Mangum(app, lifespan="off")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point.

    Args:
        event: Lambda event dictionary containing request information.
        context: Lambda context object with runtime information.

    Returns:
        Response dictionary with statusCode, headers, and body.

    """
    logger.info("Lambda event: {}", event)
    response = handler(event, context)
    logger.info("Lambda response status: {}", response.get("statusCode"))

    return response  # type: ignore[no-any-return]
