#!/usr/bin/env python3
"""Data Transformations - JSON to Response pipeline with validation."""

from diagrams import Cluster, Diagram, Edge
from diagrams.programming.flowchart import (
    Action,
    Decision,
    Document,
    InputOutput,
    PredefinedProcess,
)
from diagrams.programming.language import Python

COLORS = {
    "transform": "#17a2b8",
    "validate": "#6f42c1",
    "error": "#dc3545",
    "success": "#28a745",
    "cache": "#ffc107",
}

with Diagram(
    "Data Transformation Pipeline",
    filename="04_data_transformations",
    show=False,
    direction="LR",
    graph_attr={
        "fontsize": "12",
        "bgcolor": "white",
        "pad": "0.5",
        "rankdir": "LR",
    },
):
    # Input stages
    raw_input = InputOutput("Raw HTTP\nRequest")

    # Transformation stages
    with Cluster("1. Request Parsing"):
        parse_json = Action("Parse JSON\nBody")
        extract_headers = Action("Extract\nHeaders")
        merge_params = Action("Merge Path\nParameters")

    with Cluster("2. Pydantic Validation"):
        pydantic_model = Python("ChatMessage\nModel")
        field_validators = Action("Field\nValidators")
        sanitize = Action("Sanitize:\n- Strip whitespace\n- Remove scripts\n- Check length")

    with Cluster("3. Business Logic"):
        check_cache = Decision("Cache\nCheck")
        cache_key_gen = Action("Generate Key:\nSHA256(user_id + content)")
        llm_prompt = Action("Build Prompt:\n- System message\n- User content\n- Context")

    with Cluster("4. LLM Processing"):
        llm_request = Document("LLM Request:\n{model, messages,\ntemperature}")
        llm_response = Document("LLM Response:\n{content, usage,\nmodel}")
        retry_logic = PredefinedProcess("Retry with\nTenacity")

    with Cluster("5. Response Building"):
        create_response = Action(
            "ChatResponse:\n- id: UUID\n- content: str\n- timestamp: UTC\n- cached: bool"
        )
        add_metadata = Action("Add Metadata:\n- model used\n- tokens consumed\n- request_id")

    with Cluster("6. Storage"):
        save_record = PredefinedProcess("MessageRecord:\n- All fields\n- JSON usage")
        update_cache = PredefinedProcess("Cache Entry:\n- TTL: 3600s\n- Key: SHA256")

    # Output
    json_response = InputOutput("HTTP Response\n200 OK")
    error_response = InputOutput("Error Response\n4xx/5xx")

    # Main flow
    raw_input >> parse_json >> pydantic_model
    extract_headers >> pydantic_model
    merge_params >> pydantic_model

    pydantic_model >> field_validators >> sanitize

    # Validation branch
    sanitize >> Edge(label="Valid", color=COLORS["success"]) >> cache_key_gen
    sanitize >> Edge(label="Invalid", color=COLORS["error"]) >> error_response

    # Cache flow
    cache_key_gen >> check_cache
    check_cache >> Edge(label="Hit", color=COLORS["cache"]) >> create_response
    check_cache >> Edge(label="Miss", color=COLORS["transform"]) >> llm_prompt

    # LLM flow
    llm_prompt >> llm_request >> retry_logic >> llm_response
    llm_response >> save_record
    llm_response >> update_cache
    llm_response >> create_response

    # Final response
    create_response >> add_metadata >> json_response

    # Error path
    retry_logic >> Edge(label="Failed", color=COLORS["error"], style="dashed") >> error_response
