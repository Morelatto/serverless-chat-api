#!/usr/bin/env python3
"""Data Flow - Simplified horizontal request processing."""

import sys

sys.path.append("../shared")
from custom_icons import DictCache, LiteLLM, Pydantic, get_icon
from diagram_styles import COLORS
from diagrams import Diagram, Edge

with Diagram(
    "Request Processing Flow",
    filename="07_data_flow",
    show=False,
    direction="LR",
    graph_attr={
        "fontsize": "14",
        "bgcolor": "white",
        "pad": "0.5",
        "rankdir": "LR",
        "dpi": "150",
        "nodesep": "0.8",
    },
):
    # Main flow components
    json_in = get_icon("input", "JSON")
    validate = Pydantic("Validate")
    cache = DictCache("Cache")
    llm = LiteLLM("LLM")
    response = get_icon("output", "Response")

    # Main flow - VERY THICK for 90% cached path
    json_in >> Edge(color=COLORS["api"], penwidth="2") >> validate
    validate >> Edge(color=COLORS["info"], penwidth="2") >> cache

    # Cache hit - SUPER THICK (90% of traffic)
    cache >> Edge(label="90% HIT", color=COLORS["success"], penwidth="7") >> response

    # Cache miss - THIN (10% of traffic)
    cache >> Edge(label="10% MISS", color=COLORS["external"], penwidth="1", style="dashed") >> llm
    llm >> Edge(color=COLORS["external"], penwidth="1") >> response
