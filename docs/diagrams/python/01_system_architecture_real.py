#!/usr/bin/env python3
"""System Architecture - YOUR ACTUAL Stack."""

from custom_icons import (
    DictCache,
    FastAPI,
    Jose,
    LiteLLM,
    Loguru,
    Pydantic,
    Slowapi,
    Tenacity,
    get_icon,
)
from diagram_helpers import COLORS, cluster_style
from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.onprem.client import Client
from diagrams.onprem.inmemory import Redis
from diagrams.programming.language import Python

with Diagram(
    "Chat API - Actual Architecture",
    filename="01_system_architecture_real",
    show=False,
    direction="LR",
    graph_attr={
        "fontsize": "14",
        "bgcolor": "white",
        "pad": "0.5",
        "rankdir": "LR",
    },
):
    # External actors
    client = Client("Client\nApplication")

    # YOUR FastAPI Application
    with Cluster("FastAPI Application", graph_attr=cluster_style("api")):
        with Cluster("Security & Middleware"):
            jwt_auth = Jose("JWT Auth\n(python-jose)")
            rate_limiter = Slowapi("Rate Limiter\n(slowapi)")
            request_id = Python("Request ID\nMiddleware")

        app = FastAPI("FastAPI\nApp")

        with Cluster("Endpoints"):
            login = FastAPI("/login")
            chat = FastAPI("/chat")
            history = FastAPI("/history")
            health = FastAPI("/health")

    # YOUR Business Logic
    with Cluster("Service Layer", graph_attr=cluster_style("business")):
        chat_service = Python("ChatService")
        validation = Pydantic("Pydantic\nValidation")
        retry_logic = Tenacity("Tenacity\nRetry")
        logging = Loguru("Loguru\nLogging")

    # YOUR Data Access Layer (Protocols)
    with Cluster("Protocol Pattern", graph_attr=cluster_style("data")):
        with Cluster("Protocols"):
            repo_protocol = Python("Repository\nProtocol")
            cache_protocol = Python("Cache\nProtocol")
            llm_protocol = Python("LLMProvider\nProtocol")

        with Cluster("Implementations"):
            # YOUR actual implementations
            sqlite_impl = get_icon("aiosqlite", "SQLite\n(aiosqlite)")
            dynamo_impl = Dynamodb("DynamoDB\n(aioboto3)")
            redis_impl = Redis("Redis")
            memory_impl = DictCache("Dict\nCache")

    # YOUR LLM Integration (via litellm)
    with Cluster("LLM Providers (via litellm)", graph_attr=cluster_style("external")):
        litellm_lib = LiteLLM("litellm")
        openrouter = get_icon("openrouter", "OpenRouter")
        gemini = get_icon("gemini", "Gemini")

        litellm_lib >> openrouter
        litellm_lib >> gemini

    # YOUR Deployment
    with Cluster("Deployment"):
        with Cluster("Lambda"):
            mangum_adapter = get_icon("mangum", "Mangum\nAdapter")
            lambda_func = Lambda("Lambda\nFunction")
            mangum_adapter >> lambda_func

        with Cluster("Local"):
            uvicorn = Python("Uvicorn\nServer")

    # Main request flow (YOUR actual flow)
    client >> Edge(label="HTTPS", color=COLORS["external"]) >> app
    app >> jwt_auth >> rate_limiter >> request_id

    # Endpoint routing
    app >> login
    app >> chat
    app >> history
    app >> health

    # Service connections
    chat >> chat_service
    history >> chat_service
    chat_service >> validation
    chat_service >> retry_logic
    chat_service >> logging

    # Protocol usage
    chat_service >> Edge(label="uses", color=COLORS["auth"]) >> repo_protocol
    chat_service >> Edge(label="uses", color=COLORS["auth"]) >> cache_protocol
    chat_service >> Edge(label="uses", color=COLORS["auth"]) >> llm_protocol

    # Implementation selection (YOUR factory pattern)
    repo_protocol >> Edge(style="dashed") >> sqlite_impl
    repo_protocol >> Edge(style="dashed") >> dynamo_impl
    cache_protocol >> Edge(style="dashed") >> redis_impl
    cache_protocol >> Edge(style="dashed") >> memory_impl
    llm_protocol >> Edge(style="dashed") >> litellm_lib

    # Deployment connections
    app >> Edge(style="dotted", label="Lambda") >> mangum_adapter
    app >> Edge(style="dotted", label="Local") >> uvicorn
