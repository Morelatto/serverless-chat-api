#!/usr/bin/env python3
"""Runtime Dependencies - Startup sequence and dependency graph."""

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.database import Dynamodb
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.programming.flowchart import (
    Action,
    Decision,
    PredefinedProcess,
    StartEnd,
)
from diagrams.programming.framework import FastAPI

COLORS = {
    "success": "#28a745",
    "init": "#17a2b8",
    "dependency": "#6f42c1",
    "optional": "#ffc107",
}

with Diagram(
    "Startup Dependencies & Initialization",
    filename="06_runtime_dependencies",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "12",
        "bgcolor": "white",
        "pad": "0.5",
        "rankdir": "TB",
    },
):
    start = StartEnd("Application\nStart")
    ready = StartEnd("Ready to\nServe")

    # Configuration phase
    with Cluster("1. Configuration Loading", graph_attr={"bgcolor": "#f0f8ff"}):
        load_env = Action("Load .env file")
        parse_settings = Action("Parse Settings\n(pydantic-settings)")
        validate_config = Decision("Config\nValid?")

        load_env >> parse_settings >> validate_config

    # Logging setup
    with Cluster("2. Logging Setup", graph_attr={"bgcolor": "#fff9e6"}):
        configure_logging = Action(
            "Configure Loguru:\n• Set log level\n• Add file handler\n• Format messages"
        )

    # Repository initialization
    with Cluster("3. Repository Layer", graph_attr={"bgcolor": "#e8f5e9"}):
        detect_repo = Decision("Database\nType?")

        sqlite_init = PredefinedProcess(
            "SQLite Init:\n• aiosqlite.connect()\n• Create tables\n• Create indexes"
        )
        sqlite_db = PostgreSQL("SQLite\nDatabase")

        dynamo_init = PredefinedProcess(
            "DynamoDB Init:\n• aioboto3 session\n• Check table exists\n• Configure TTL"
        )
        dynamo_db = Dynamodb("DynamoDB\nTable")

        detect_repo >> Edge(label="Local", color=COLORS["init"]) >> sqlite_init
        detect_repo >> Edge(label="Lambda", color=COLORS["init"]) >> dynamo_init

        sqlite_init >> Edge(style="dashed") >> sqlite_db
        dynamo_init >> Edge(style="dashed") >> dynamo_db

    # Cache initialization
    with Cluster("4. Cache Layer", graph_attr={"bgcolor": "#ffe6e6"}):
        detect_cache = Decision("Cache\nType?")

        redis_init = PredefinedProcess("Redis Init:\n• Connection pool\n• Test connection")
        redis_cache = Redis("Redis\nCache")

        memory_init = PredefinedProcess("Memory Init:\n• Create dict\n• Set max size")
        memory_cache = Action("In-Memory\nCache")

        detect_cache >> Edge(label="Redis URL", color=COLORS["optional"]) >> redis_init
        detect_cache >> Edge(label="No URL", color=COLORS["init"]) >> memory_init

        redis_init >> Edge(style="dashed") >> redis_cache
        memory_init >> Edge(style="dashed") >> memory_cache

    # LLM Provider setup
    with Cluster("5. LLM Provider", graph_attr={"bgcolor": "#f0f0f0"}):
        detect_llm = Decision("Provider\nType?")

        openrouter = PredefinedProcess(
            "OpenRouter:\n• Set API key\n• Configure model\n• Setup retry"
        )
        gemini = PredefinedProcess("Gemini:\n• Set API key\n• Configure model\n• Setup retry")

        detect_llm >> Edge(label="openrouter", color=COLORS["init"]) >> openrouter
        detect_llm >> Edge(label="gemini", color=COLORS["init"]) >> gemini

    # Service creation
    with Cluster("6. Service Layer", graph_attr={"bgcolor": "#fff3e0"}):
        create_service = Action(
            "Create ChatService:\n• Inject repository\n• Inject cache\n• Inject LLM provider"
        )
        service_singleton = Action("Store as\nSingleton")

    # FastAPI setup
    with Cluster("7. FastAPI Application", graph_attr={"bgcolor": "#e6f3ff"}):
        app = FastAPI("FastAPI App")
        add_middleware = Action("Add Middleware:\n• CORS\n• Request ID\n• Rate limiting")
        add_handlers = Action("Add Handlers:\n• Exception handlers\n• Validation handlers")
        mount_routes = Action("Mount Routes:\n• /chat\n• /history\n• /health\n• /login")

    # Dependency flow
    start >> load_env
    validate_config >> Edge(label="Valid", color=COLORS["success"]) >> configure_logging

    configure_logging >> detect_repo
    configure_logging >> detect_cache
    configure_logging >> detect_llm

    # All repos lead to service
    sqlite_init >> create_service
    dynamo_init >> create_service
    redis_init >> create_service
    memory_init >> create_service
    openrouter >> create_service
    gemini >> create_service

    create_service >> service_singleton >> app
    app >> add_middleware >> add_handlers >> mount_routes >> ready

    # Shutdown sequence
    with Cluster("8. Shutdown Sequence", graph_attr={"bgcolor": "#ffebee"}):
        shutdown_signal = StartEnd("SIGTERM")
        close_db = Action("Close DB\nConnections")
        close_cache = Action("Close Cache\nConnections")
        cleanup = Action("Cleanup\nResources")
        terminated = StartEnd("Terminated")

        shutdown_signal >> close_db >> close_cache >> cleanup >> terminated
