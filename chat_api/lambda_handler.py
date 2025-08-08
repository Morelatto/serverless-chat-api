"""AWS Lambda handler for the Chat API."""

from typing import Any

from loguru import logger
from mangum import Mangum

from .app import app

# Configure loguru for Lambda
logger.add(lambda msg: print(msg, end=""))  # Lambda logs to stdout

# Create the Lambda handler using Mangum
handler = Mangum(app, lifespan="off")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point.

    Args:
        event: Lambda event dictionary containing request information.
        context: Lambda context object with runtime information.

    Returns:
        Response dictionary with statusCode, headers, and body.
    """
    # Log the incoming event for debugging
    logger.info("Lambda event: {}", event)

    # Process the request through Mangum/FastAPI
    response = handler(event, context)

    # Log the response for debugging
    logger.info("Lambda response status: {}", response.get("statusCode"))

    return response  # type: ignore[no-any-return]
