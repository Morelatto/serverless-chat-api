#!/usr/bin/env python3
"""Error Handling - What could go wrong?"""

import sys

sys.path.append("../shared")
from custom_icons import FastAPI, Jose, LiteLLM, Pydantic, Slowapi, StatusCode
from diagrams import Cluster, Diagram, Edge

with Diagram(
    "Error Handling",
    filename="05_error_handling",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "14",
        "bgcolor": "white",
        "pad": "0.5",
        "rankdir": "TB",
        "dpi": "150",
    },
):
    # Error sources grouped by type
    with Cluster("Auth Errors"):
        auth_errors = Jose("JWT\nErrors")

    with Cluster("Rate Limits"):
        rate_errors = Slowapi("Too Many\nRequests")

    with Cluster("Validation"):
        validation_errors = Pydantic("Invalid\nInput")

    with Cluster("External"):
        external_errors = LiteLLM("Service\nFailure")

    # Central handler (the funnel)
    handler = FastAPI("Exception\nMiddleware")

    # HTTP responses with proper status code icons
    with Cluster("Client Errors", graph_attr={"bgcolor": "#FFEBEE"}):
        resp_401 = StatusCode(401, "401\nUnauthorized")
        resp_422 = StatusCode(422, "422\nValidation")
        resp_429 = StatusCode(429, "429\nRate Limited")

    with Cluster("Server Errors", graph_attr={"bgcolor": "#F3E5F5"}):
        resp_503 = StatusCode(503, "503\nUnavailable")

    # All errors flow to handler
    auth_errors >> Edge(color="#ef4444") >> handler  # Red for auth
    rate_errors >> Edge(color="#f59e0b") >> handler  # Orange for rate limit
    validation_errors >> Edge(color="#f59e0b") >> handler  # Orange for validation
    external_errors >> Edge(color="#8b5cf6") >> handler  # Purple for server errors

    # Handler returns appropriate response with semantic colors
    handler >> Edge(color="#ef4444") >> resp_401
    handler >> Edge(color="#f59e0b") >> resp_422
    handler >> Edge(color="#f59e0b") >> resp_429
    handler >> Edge(color="#8b5cf6") >> resp_503
