#!/usr/bin/env python3
"""System Overview - Production deployment with cache dominance."""

import sys

sys.path.append("../shared")
from custom_icons import FastAPI, LiteLLM, get_icon
from diagram_styles import COLORS
from diagrams import Diagram, Edge
from diagrams.onprem.client import Client

with Diagram(
    "Chat API System (Production)",
    filename="01_system_overview",
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
    # Add environment context
    env_label = "🚀 PRODUCTION: AWS Lambda + DynamoDB + ElastiCache"

    # Simple horizontal flow
    client = Client("Users")
    api = FastAPI("API")
    cache = get_icon("redis", "Redis\nCache")
    database = get_icon("dynamodb", "DynamoDB")
    llm = LiteLLM("LLM\nProviders")

    # Main flow with clear visual hierarchy
    client >> Edge(label="HTTPS", color=COLORS["api"], penwidth="3") >> api

    # Cache dominates (90% of traffic)
    api >> Edge(label="90% HIT", color=COLORS["success"], penwidth="8") >> cache

    # Database for persistence
    api >> Edge(color=COLORS["database"], penwidth="2") >> database

    # LLM only for misses (10% of traffic)
    api >> Edge(label="10% MISS", color=COLORS["external"], penwidth="1", style="dashed") >> llm
