#!/usr/bin/env python3
"""Data Flow - Clean architecture layers."""

import sys

sys.path.append("../shared")
from custom_icons import DictCache, LiteLLM, Pydantic, get_icon
from diagram_styles import COLORS
from diagrams import Cluster, Diagram, Edge

with Diagram(
    "Data Flow Architecture",
    filename="07_data_flow",
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
    # Input layer
    with Cluster("Input Layer", graph_attr={"bgcolor": "#E3F2FD"}):
        json_in = get_icon("data", "JSON\nRequest")
        pydantic_in = Pydantic("ChatRequest\nModel")

    # Business layer
    with Cluster("Business Layer", graph_attr={"bgcolor": "#FFF9E6"}):
        service = get_icon("state", "Chat\nService")
        cache_key = get_icon("hash", "MD5\nHash")
        cache_check = DictCache("Cache\nLookup")

    # External layer
    with Cluster("External Layer", graph_attr={"bgcolor": "#FFE6F0"}):
        llm_request = LiteLLM("LLM\nAdapter")
        provider = get_icon("openai", "OpenAI\nAnthropic\nGoogle")

    # Output layer
    with Cluster("Output Layer", graph_attr={"bgcolor": "#E8F5E9"}):
        pydantic_out = Pydantic("ChatResponse\nModel")
        json_out = get_icon("data", "JSON\nResponse")

    # Data flow with transformations
    json_in >> Edge(label="Parse", color=COLORS["validate"]) >> pydantic_in
    pydantic_in >> Edge(label="Validate", color=COLORS["validate"]) >> service

    # Cache path
    service >> Edge(label="Generate key", color=COLORS["info"]) >> cache_key
    cache_key >> cache_check
    cache_check >> Edge(label="HIT", color=COLORS["success"], penwidth="3") >> pydantic_out

    # LLM path
    cache_check >> Edge(label="MISS", color=COLORS["warning"], style="dashed") >> llm_request
    llm_request >> Edge(label="Transform", color=COLORS["external"]) >> provider
    provider >> Edge(label="Response", color=COLORS["external"]) >> pydantic_out

    # Output
    pydantic_out >> Edge(label="Serialize", color=COLORS["success"]) >> json_out
