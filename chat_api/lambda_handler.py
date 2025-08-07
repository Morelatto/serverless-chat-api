"""AWS Lambda handler for the Chat API."""
import logging
from typing import Any

from mangum import Mangum

from .app import app

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
    logger.info(f"Lambda event: {event}")

    # Process the request through Mangum/FastAPI
    response = handler(event, context)

    # Log the response for debugging
    logger.info(f"Lambda response status: {response.get('statusCode')}")

    return response
