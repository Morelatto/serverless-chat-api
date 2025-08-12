#!/usr/bin/env python3
"""Startup Sequence - Initialization order."""

import sys

sys.path.append("../shared")
from custom_icons import DictCache, FastAPI, get_icon
from diagram_styles import COLORS
from diagrams import Diagram, Edge

with Diagram(
    "Startup Sequence",
    filename="09_startup_sequence",
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
    # Startup sequence steps
    start = get_icon("power", "Start")
    env = get_icon("settings", "Load\n.env")
    config = get_icon("settings", "Parse\nConfig")

    # Initialize components
    init_db = get_icon("aiosqlite", "Init\nDatabase")
    init_cache = DictCache("Init\nCache")
    init_llm = get_icon("litellm", "Init\nLLM Client")

    # Create services
    create_service = get_icon("state", "Create\nService")
    setup_routes = FastAPI("Setup\nRoutes")
    setup_middleware = get_icon("middleware", "Setup\nMiddleware")

    # Start server
    start_api = FastAPI("Start\nAPI")
    ready = get_icon("check", "Ready\nPort 8000")

    # Sequential flow with timing
    start >> Edge(label="0ms", color=COLORS["info"]) >> env
    env >> Edge(label="+5ms", color=COLORS["info"]) >> config

    # Parallel initialization
    config >> Edge(label="+10ms", color=COLORS["database"]) >> init_db
    config >> Edge(label="+2ms", color=COLORS["cache"]) >> init_cache
    config >> Edge(label="+15ms", color=COLORS["external"]) >> init_llm

    # Service creation
    init_db >> create_service
    init_cache >> create_service
    init_llm >> create_service

    # API setup
    create_service >> Edge(label="+5ms", color=COLORS["api"]) >> setup_routes
    setup_routes >> Edge(label="+3ms", color=COLORS["api"]) >> setup_middleware
    setup_middleware >> Edge(label="+10ms", color=COLORS["api"]) >> start_api

    # Ready
    start_api >> Edge(label="Total: 50ms", color=COLORS["success"], penwidth="2") >> ready
