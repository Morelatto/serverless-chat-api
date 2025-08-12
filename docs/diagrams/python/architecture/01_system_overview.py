#!/usr/bin/env python3
"""System Overview - What does this system do?"""

import sys

sys.path.append("../shared")
from custom_icons import DictCache, FastAPI, LiteLLM, get_icon
from diagram_styles import COLORS
from diagrams import Diagram, Edge
from diagrams.onprem.client import Client

with Diagram(
    "Chat API System",
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
    # Simple horizontal flow
    client = Client("Client")
    api = FastAPI("FastAPI")
    cache = DictCache("Cache")
    database = get_icon("aiosqlite", "SQLite")
    llm = LiteLLM("LLM")

    # Main flow
    client >> Edge(label="HTTPS", color=COLORS["api"], penwidth="2") >> api

    # API connections with much stronger visual hierarchy
    api >> Edge(label="90%", color=COLORS["cache"], penwidth="7") >> cache  # Very thick for 90%
    api >> Edge(color=COLORS["database"], penwidth="2") >> database
    (
        api >> Edge(label="10%", color=COLORS["external"], penwidth="1", style="dashed") >> llm
    )  # Very thin for 10%
