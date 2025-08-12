#!/usr/bin/env python3
"""Error Handling Matrix - All failure modes and responses."""

from diagrams import Cluster, Diagram, Edge
from diagrams.programming.flowchart import (
    Action,
    Decision,
    Document,
    StartEnd,
)

COLORS = {
    "auth": "#6f42c1",
    "validation": "#ffc107",
    "rate": "#dc3545",
    "service": "#17a2b8",
    "server": "#6c757d",
}

with Diagram(
    "Complete Error Handling Matrix",
    filename="05_error_handling",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "11",
        "bgcolor": "white",
        "pad": "0.5",
        "ranksep": "0.75",
    },
):
    request = StartEnd("Incoming\nRequest")

    # Error detection points
    with Cluster("Error Detection Layer"):
        auth_check = Decision("Auth\nCheck")
        rate_check = Decision("Rate\nCheck")
        validation_check = Decision("Validation\nCheck")
        service_check = Decision("Service\nCheck")
        llm_check = Decision("LLM\nCheck")
        storage_check = Decision("Storage\nCheck")

    # Error types with responses
    with Cluster("4xx Client Errors", graph_attr={"bgcolor": "#ffe6e6"}):
        # 401 Unauthorized
        auth_errors = Document(
            "401 Unauthorized\n"
            "• No Authorization header\n"
            "• Invalid Bearer token\n"
            "• Expired JWT\n"
            "• Missing 'sub' claim"
        )

        # 400 Bad Request
        validation_errors = Document(
            "400 Bad Request\n"
            "• Empty content\n"
            "• Content > 10000 chars\n"
            "• Invalid user_id\n"
            "• Malicious content\n"
            "• Invalid JSON"
        )

        # 429 Too Many Requests
        rate_errors = Document(
            "429 Too Many Requests\n"
            "• Exceeded 60/minute\n"
            "Headers:\n"
            "• Retry-After: seconds\n"
            "• X-RateLimit-Remaining"
        )

    with Cluster("5xx Server Errors", graph_attr={"bgcolor": "#e6f3ff"}):
        # 503 Service Unavailable
        service_errors = Document(
            "503 Service Unavailable\n"
            "• LLM provider down\n"
            "• Database unreachable\n"
            "• Cache connection failed\n"
            "• Timeout errors"
        )

        # 500 Internal Server Error
        server_errors = Document(
            "500 Internal Server Error\n"
            "• Unhandled exceptions\n"
            "• Configuration errors\n"
            "• Dependency failures"
        )

    # Error handling mechanisms
    with Cluster("Error Handlers", graph_attr={"bgcolor": "#f0f8ff"}):
        exception_handler = Action(
            "FastAPI Exception Handlers:\n"
            "• ChatAPIError → JSON\n"
            "• RequestValidationError → 400\n"
            "• HTTPException → Status code"
        )

        middleware_handler = Action(
            "Middleware Handlers:\n"
            "• add_request_id\n"
            "• Log with context\n"
            "• Correlation tracking"
        )

        retry_handler = Action(
            "Retry Logic (Tenacity):\n"
            "• stop_after_attempt(3)\n"
            "• wait_exponential\n"
            "• retry_if_exception"
        )

    # Response formatting
    with Cluster("Error Response Format"):
        error_format = Document(
            "{\n"
            '  "detail": "Error message",\n'
            '  "type": "ErrorClassName",\n'
            '  "request_id": "uuid",\n'
            '  "timestamp": "ISO8601"\n'
            "}"
        )

        headers = Document(
            "Response Headers:\n"
            "• X-Request-ID\n"
            "• WWW-Authenticate (401)\n"
            "• Retry-After (429)\n"
            "• Content-Type: application/json"
        )

    # Flow connections
    request >> auth_check
    auth_check >> Edge(label="Fail", color=COLORS["auth"]) >> auth_errors
    auth_check >> Edge(label="Pass") >> rate_check

    rate_check >> Edge(label="Exceed", color=COLORS["rate"]) >> rate_errors
    rate_check >> Edge(label="OK") >> validation_check

    validation_check >> Edge(label="Invalid", color=COLORS["validation"]) >> validation_errors
    validation_check >> Edge(label="Valid") >> service_check

    service_check >> llm_check
    service_check >> storage_check

    llm_check >> Edge(label="Error", color=COLORS["service"]) >> service_errors
    storage_check >> Edge(label="Error", color=COLORS["service"]) >> service_errors

    # All errors go through handlers
    auth_errors >> exception_handler
    validation_errors >> exception_handler
    rate_errors >> exception_handler
    service_errors >> retry_handler >> exception_handler
    server_errors >> exception_handler

    exception_handler >> middleware_handler >> error_format >> headers

    # Monitoring
    with Cluster("Error Monitoring", graph_attr={"bgcolor": "#fff9e6"}):
        logging = Action(
            "Loguru Logging:\n"
            "• ERROR level for 5xx\n"
            "• WARNING for 4xx\n"
            "• Stack traces\n"
            "• Request context"
        )

        metrics = Action(
            "Metrics (Future):\n"
            "• Error rate by type\n"
            "• Response times\n"
            "• Provider failures\n"
            "• Cache hit ratio"
        )

    headers >> logging >> metrics
