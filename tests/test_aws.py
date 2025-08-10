"""Test AWS Lambda handler."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from chat_api.aws import lambda_handler


@pytest.fixture
def lambda_context() -> MagicMock:
    """Mock Lambda context."""
    context = MagicMock()
    context.request_id = "test-request-id"
    context.function_name = "chat-api"
    context.memory_limit_in_mb = 128
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:chat-api"
    return context


@pytest.fixture
def api_gateway_event() -> dict[str, Any]:
    """Mock API Gateway event."""
    return {
        "version": "2.0",
        "routeKey": "POST /chat",
        "rawPath": "/chat",
        "rawQueryString": "",
        "headers": {
            "content-type": "application/json",
            "x-request-id": "test-request-123",
        },
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "api-id",
            "domainName": "api.example.com",
            "domainPrefix": "api",
            "http": {
                "method": "POST",
                "path": "/chat",
                "protocol": "HTTP/1.1",
                "sourceIp": "192.168.1.1",
                "userAgent": "test-agent",
            },
            "requestId": "request-id",
            "routeKey": "POST /chat",
            "stage": "$default",
            "time": "01/Jan/2025:00:00:00 +0000",
            "timeEpoch": 1735689600,
        },
        "body": '{"user_id": "test-user", "content": "Hello Lambda"}',
        "isBase64Encoded": False,
    }


@pytest.mark.asyncio
async def test_lambda_handler_success(
    api_gateway_event: dict[str, Any], lambda_context: MagicMock
) -> None:
    """Test successful Lambda invocation."""
    with patch("chat_api.aws.handler") as mock_handler:
        # Mock Mangum handler response
        mock_handler.return_value = {
            "statusCode": 200,
            "headers": {"content-type": "application/json"},
            "body": '{"id": "msg-123", "content": "Response from Lambda"}',
        }

        response = lambda_handler(api_gateway_event, lambda_context)

        assert response["statusCode"] == 200
        assert "body" in response
        mock_handler.assert_called_once_with(api_gateway_event, lambda_context)


@pytest.mark.asyncio
async def test_lambda_handler_error(
    api_gateway_event: dict[str, Any], lambda_context: MagicMock
) -> None:
    """Test Lambda handler error handling."""
    with patch("chat_api.aws.handler") as mock_handler:
        # Mock handler raising an exception
        mock_handler.side_effect = Exception("Handler error")

        with pytest.raises(Exception, match="Handler error"):
            lambda_handler(api_gateway_event, lambda_context)


@pytest.mark.asyncio
async def test_lambda_handler_health_check(lambda_context: MagicMock) -> None:
    """Test Lambda health check endpoint."""
    health_event = {
        "version": "2.0",
        "routeKey": "GET /health",
        "rawPath": "/health",
        "rawQueryString": "",
        "headers": {},
        "requestContext": {
            "http": {
                "method": "GET",
                "path": "/health",
            },
        },
        "isBase64Encoded": False,
    }

    with patch("chat_api.aws.handler") as mock_handler:
        mock_handler.return_value = {
            "statusCode": 200,
            "headers": {"content-type": "application/json"},
            "body": '{"status": "healthy"}',
        }

        response = lambda_handler(health_event, lambda_context)

        assert response["statusCode"] == 200
        assert "healthy" in response["body"]


@pytest.mark.asyncio
async def test_lambda_handler_base64_body(lambda_context: MagicMock) -> None:
    """Test Lambda handler with base64 encoded body."""
    import base64

    body_content = '{"user_id": "test", "content": "Base64 test"}'
    encoded_body = base64.b64encode(body_content.encode()).decode()

    event = {
        "version": "2.0",
        "routeKey": "POST /chat",
        "rawPath": "/chat",
        "headers": {"content-type": "application/json"},
        "requestContext": {
            "http": {"method": "POST", "path": "/chat"},
        },
        "body": encoded_body,
        "isBase64Encoded": True,
    }

    with patch("chat_api.aws.handler") as mock_handler:
        mock_handler.return_value = {
            "statusCode": 200,
            "body": '{"success": true}',
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200
        # Verify Mangum was called with the event
        mock_handler.assert_called_once()


@pytest.mark.asyncio
async def test_lambda_handler_invalid_json(lambda_context: MagicMock) -> None:
    """Test Lambda handler with invalid JSON body."""
    event = {
        "version": "2.0",
        "routeKey": "POST /chat",
        "rawPath": "/chat",
        "headers": {"content-type": "application/json"},
        "requestContext": {
            "http": {"method": "POST", "path": "/chat"},
        },
        "body": "invalid json {",
        "isBase64Encoded": False,
    }

    with patch("chat_api.aws.handler") as mock_handler:
        mock_handler.return_value = {
            "statusCode": 400,
            "body": '{"detail": "Invalid JSON"}',
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400


@pytest.mark.asyncio
async def test_lambda_handler_cors_headers(lambda_context: MagicMock) -> None:
    """Test Lambda handler includes CORS headers."""
    event = {
        "version": "2.0",
        "routeKey": "OPTIONS /chat",
        "rawPath": "/chat",
        "headers": {"origin": "https://example.com"},
        "requestContext": {
            "http": {"method": "OPTIONS", "path": "/chat"},
        },
    }

    with patch("chat_api.aws.handler") as mock_handler:
        mock_handler.return_value = {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
            "body": "",
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200
        assert "Access-Control-Allow-Origin" in response.get("headers", {})


@pytest.mark.asyncio
async def test_lambda_cold_start_logging(
    api_gateway_event: dict[str, Any], lambda_context: MagicMock
) -> None:
    """Test Lambda cold start is logged."""
    with patch("chat_api.aws.handler") as mock_handler, patch("chat_api.aws.logger") as mock_logger:
        mock_handler.return_value = {"statusCode": 200, "body": "{}"}

        lambda_handler(api_gateway_event, lambda_context)

        # Check that event was logged (at least once)
        assert mock_logger.info.call_count >= 1
