#!/usr/bin/env python3
"""Request Flow Diagram - Complete request processing with proper shapes."""

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.ml import Sagemaker
from diagrams.generic.database import SQL
from diagrams.onprem.inmemory import Redis
from diagrams.programming.flowchart import (
    Action,
    Decision,
    Document,
    InputOutput,
    PredefinedProcess,
    StartEnd,
)

# Color scheme
COLORS = {
    "success": "#28a745",
    "error": "#dc3545",
    "cache_hit": "#ffc107",
    "cache_miss": "#6c757d",
    "validation": "#6f42c1",
    "external": "#007bff",
}

with Diagram(
    "Complete Request Flow with JWT",
    filename="02_request_flow",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "12",
        "bgcolor": "white",
        "pad": "0.5",
        "splines": "ortho",
    },
):
    # Input/Output nodes
    start = StartEnd("HTTP Request")
    request_input = InputOutput("JSON Body:\n{content: str}\nHeader: Bearer token")
    response_output = InputOutput("JSON Response:\n{id, content, timestamp}")
    end = StartEnd("HTTP Response")

    # Decision nodes
    auth_check = Decision("JWT\nValid?")
    rate_check = Decision("Rate Limit\nOK?")
    cache_check = Decision("Cache\nHit?")
    validation_check = Decision("Content\nValid?")

    # Processing nodes
    extract_user = Action("Extract user_id\nfrom JWT")
    validate_content = Action("Validate & Sanitize\nContent")
    generate_cache_key = Action("Generate\nCache Key")
    check_cache = PredefinedProcess("Query Cache")
    call_llm = PredefinedProcess("Call LLM API")
    save_to_db = PredefinedProcess("Save to Database")
    update_cache = PredefinedProcess("Update Cache")
    build_response = Action("Build Response\nObject")

    # Error nodes
    auth_error = Document("401 Unauthorized")
    rate_error = Document("429 Too Many\nRequests")
    validation_error = Document("400 Bad Request")
    llm_error = Document("503 Service\nUnavailable")

    # External systems
    with Cluster("External Systems"):
        cache = Redis("Redis/Memory\nCache")
        database = SQL("SQLite/DynamoDB")
        llm = Sagemaker("LLM Provider")

    # Main success flow
    start >> request_input >> Edge(color=COLORS["validation"]) >> auth_check

    # Authentication flow
    auth_check >> Edge(label="Yes", color=COLORS["success"]) >> extract_user
    auth_check >> Edge(label="No", color=COLORS["error"]) >> auth_error >> end

    # Rate limiting
    extract_user >> rate_check
    rate_check >> Edge(label="Yes", color=COLORS["success"]) >> validate_content
    rate_check >> Edge(label="No", color=COLORS["error"]) >> rate_error >> end

    # Validation
    validate_content >> validation_check
    validation_check >> Edge(label="Yes", color=COLORS["success"]) >> generate_cache_key
    validation_check >> Edge(label="No", color=COLORS["error"]) >> validation_error >> end

    # Cache flow
    generate_cache_key >> check_cache
    check_cache >> Edge(style="dashed", color=COLORS["cache_hit"]) >> cache
    cache >> Edge(style="dashed") >> cache_check

    # Cache hit path
    cache_check >> Edge(label="Hit", color=COLORS["cache_hit"]) >> build_response

    # Cache miss path
    cache_check >> Edge(label="Miss", color=COLORS["cache_miss"]) >> call_llm
    call_llm >> Edge(style="dashed", color=COLORS["external"]) >> llm
    llm >> Edge(style="dashed", color=COLORS["external"]) >> call_llm

    # Save and cache update
    call_llm >> save_to_db
    save_to_db >> Edge(style="dashed") >> database
    save_to_db >> update_cache
    update_cache >> Edge(style="dashed", color=COLORS["cache_hit"]) >> cache
    update_cache >> build_response

    # Final response
    build_response >> response_output >> end

    # LLM error handling
    call_llm >> Edge(label="Error", color=COLORS["error"], style="dotted") >> llm_error
    llm_error >> end
