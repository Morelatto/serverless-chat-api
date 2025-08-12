#!/usr/bin/env python3
"""Startup Sequence - Fast initialization with critical path highlighted."""

import sys

sys.path.append("../shared")
from custom_icons import DictCache, FastAPI, get_icon
from diagram_styles import COLORS
from diagrams import Cluster, Diagram, Edge

with Diagram(
    "⚡ Fast Startup (50ms)",
    filename="09_startup_sequence",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "16",
        "bgcolor": "white",
        "pad": "0.5",
        "rankdir": "TB",
        "dpi": "150",
    },
):
    # Critical path - thicker lines
    start = get_icon("power", "START")
    config = get_icon("settings", "Config")

    with Cluster("Parallel Init", graph_attr={"bgcolor": "#F0F8FF", "style": "dashed"}):
        db = get_icon("sqlite", "DB")
        cache = DictCache("Cache")
        llm = get_icon("litellm", "LLM")

    api = FastAPI("API")
    ready = get_icon("check", "READY")

    # Critical path - THICK lines
    start >> Edge(color=COLORS["info"], penwidth="4") >> config

    # Parallel init - MEDIUM lines
    config >> Edge(color=COLORS["database"], penwidth="2") >> db
    config >> Edge(color=COLORS["cache"], penwidth="2") >> cache
    config >> Edge(color=COLORS["external"], penwidth="2") >> llm

    # Convergence - THICK again
    db >> Edge(color=COLORS["api"], penwidth="3") >> api
    cache >> Edge(color=COLORS["api"], penwidth="3") >> api
    llm >> Edge(color=COLORS["api"], penwidth="3") >> api

    # Final - VERY THICK with prominent timing
    api >> Edge(label="✨ 50ms", color=COLORS["success"], penwidth="5", fontsize="20") >> ready
