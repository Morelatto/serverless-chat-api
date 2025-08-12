#!/usr/bin/env python3
"""Error Handling - Unified error response strategy."""

import sys

sys.path.append("../shared")
from custom_icons import FastAPI, Pydantic, Slowapi, get_icon
from diagram_styles import COLORS
from diagrams import Diagram, Edge

with Diagram(
    "Error Handling Strategy",
    filename="05_error_handling",
    show=False,
    direction="LR",
    graph_attr={
        "fontsize": "14",
        "bgcolor": "white",
        "pad": "0.5",
        "rankdir": "LR",
        "dpi": "150",
    },
):
    # Error sources
    auth_err = get_icon("jwt", "Auth\nFailed")
    rate_err = Slowapi("Rate\nLimit")
    validate_err = Pydantic("Invalid\nData")
    external_err = get_icon("litellm", "LLM\nDown")

    # Central handler
    handler = FastAPI("Error\nHandler")

    # Client response with proper badges
    client = get_icon("user", "Client")

    # Error flows to handler - thin lines for errors
    auth_err >> Edge(label="401", color="#ef4444", penwidth="1") >> handler
    rate_err >> Edge(label="429", color="#f59e0b", penwidth="1") >> handler
    validate_err >> Edge(label="422", color="#f59e0b", penwidth="1") >> handler
    external_err >> Edge(label="503", color="#8b5cf6", penwidth="1") >> handler

    # Unified response - thicker for main path
    handler >> Edge(label="HTTP Error\nResponse", color=COLORS["error"], penwidth="3") >> client
