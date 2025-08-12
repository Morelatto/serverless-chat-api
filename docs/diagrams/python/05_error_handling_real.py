#!/usr/bin/env python3
"""Error Handling - YOUR ACTUAL Implementation."""

from custom_icons import (
    FastAPI,
    Handler,
    Loguru,
    Middleware,
    Pydantic,
    Slowapi,
    Tenacity,
)
from diagram_helpers import COLORS, cluster_style
from diagrams import Cluster, Diagram, Edge
from diagrams.programming.language import Python

with Diagram(
    "Error Handling - Actual Implementation",
    filename="05_error_handling_real",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "11",
        "bgcolor": "white",
        "pad": "0.5",
        "rankdir": "TB",
        "nodesep": "0.3",
        "ranksep": "0.5",
        "splines": "ortho",
    },
):
    # Request Entry
    request = FastAPI("Request")

    # Your ACTUAL Error Classes (from exceptions.py)
    with Cluster("ChatAPIError Hierarchy", graph_attr=cluster_style("error")):
        base_error = Python("ChatAPIError")
        auth_error = Handler("AuthError\n401")
        validation_error = Handler("ValidationError\n400")
        rate_limit_error = Handler("RateLimitError\n429")
        provider_error = Handler("ProviderError\n503")
        not_found = Handler("NotFoundError\n404")

        # Your inheritance structure
        base_error >> Edge(style="dashed") >> auth_error
        base_error >> Edge(style="dashed") >> validation_error
        base_error >> Edge(style="dashed") >> rate_limit_error
        base_error >> Edge(style="dashed") >> provider_error
        base_error >> Edge(style="dashed") >> not_found

    # Detection Points in YOUR code
    with Cluster("Where Errors Occur", graph_attr=cluster_style("monitor")):
        # Your actual validation points
        jwt_middleware = Middleware("get_current_user()")
        slowapi_check = Slowapi("@limiter.limit()")
        pydantic_val = Pydantic("ChatMessage")
        llm_call = Python("llm_provider.complete()")
        db_operation = Python("repository.save()")

    # Your Exception Handlers (from api.py)
    with Cluster("FastAPI Exception Handlers", graph_attr=cluster_style("api")):
        chat_api_handler = Handler("@app.exception_handler\n(ChatAPIError)")
        validation_handler = Handler("@app.exception_handler\n(RequestValidationError)")
        rate_limit_handler = Handler("@app.exception_handler\n(RateLimitExceeded)")
        generic_handler = Handler("@app.exception_handler\n(Exception)")

    # Request ID Tracking (YOUR middleware)
    with Cluster("Request Tracking", graph_attr=cluster_style("business")):
        request_id = Middleware("RequestIDMiddleware")
        logger = Loguru("loguru.logger")

        request_id >> logger

    # Retry Logic (YOUR Tenacity implementation)
    with Cluster("Retry Strategy (Tenacity)", graph_attr=cluster_style("cache")):
        tenacity_retry = Tenacity("@retry")
        retry_config = Python("stop_after_attempt(3)\nwait_exponential()")

        tenacity_retry >> retry_config

    # Connect error flows based on YOUR code
    request >> request_id

    # Auth errors
    jwt_middleware >> Edge(color=COLORS["error"], label="No token") >> auth_error
    auth_error >> chat_api_handler

    # Rate limit errors
    slowapi_check >> Edge(color=COLORS["warning"], label="Too many") >> rate_limit_error
    rate_limit_error >> rate_limit_handler

    # Validation errors
    pydantic_val >> Edge(color=COLORS["validate"], label="Invalid") >> validation_error
    validation_error >> validation_handler

    # Provider errors (with retry)
    llm_call >> Edge(color=COLORS["external"], label="Failed") >> provider_error
    provider_error >> tenacity_retry
    tenacity_retry >> Edge(style="dashed", label="Retry 3x") >> llm_call

    # Database errors
    db_operation >> Edge(color=COLORS["database"], label="Failed") >> provider_error

    # All errors get logged
    for handler in [chat_api_handler, validation_handler, rate_limit_handler, generic_handler]:
        handler >> Edge(color=COLORS["muted"], style="dotted") >> logger

    # Response format (YOUR actual response)
    with Cluster("Error Response Format", graph_attr=cluster_style("data")):
        response = Python("JSONResponse(\n  error=str,\n  request_id=str\n)")

        logger >> response
