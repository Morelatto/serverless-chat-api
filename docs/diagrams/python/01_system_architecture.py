#!/usr/bin/env python3
"""System Architecture Diagram - High-level component overview."""

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.ml import Sagemaker
from diagrams.generic.compute import Rack
from diagrams.generic.storage import Storage
from diagrams.onprem.client import Client
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.programming.framework import FastAPI
from diagrams.programming.language import Python

# Custom colors for consistency
COLORS = {
    "success": "#28a745",
    "error": "#dc3545",
    "cache": "#ffc107",
    "external": "#007bff",
    "security": "#6f42c1",
}

with Diagram(
    "Chat API System Architecture",
    filename="01_system_architecture",
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

    with Cluster("API Gateway Layer"):
        with Cluster("Security"):
            jwt_auth = Rack("JWT\nAuthentication")
            rate_limiter = Rack("Rate Limiter\n(slowapi)")

        api = FastAPI("FastAPI\nApplication")

    with Cluster("Business Logic Layer"):
        with Cluster("Services"):
            chat_service = Python("Chat\nService")
            validation = Python("Validation\nService")

        with Cluster("Middleware"):
            error_handler = Python("Error\nHandler")
            request_tracker = Python("Request ID\nTracker")

    with Cluster("Data Access Layer"):
        with Cluster("Repository Pattern"):
            repo_interface = Storage("Repository\nProtocol")
            cache_interface = Storage("Cache\nProtocol")

        with Cluster("Implementations"):
            sqlite_impl = PostgreSQL("SQLite\n(aiosqlite)")
            dynamo_impl = Dynamodb("DynamoDB\n(aioboto3)")
            redis_impl = Redis("Redis\nCache")
            memory_impl = Storage("In-Memory\nCache")

    with Cluster("External Services"):
        openrouter = Sagemaker("OpenRouter\nLLM")
        gemini = Sagemaker("Gemini\nLLM")

    with Cluster("Infrastructure"), Cluster("Deployment Targets"):
        local = Rack("Local\nDevelopment")
        docker = Rack("Docker\nContainer")
        aws_lambda = Lambda("AWS\nLambda")

    # Main request flow
    client >> Edge(label="HTTPS Request", color=COLORS["external"]) >> jwt_auth
    jwt_auth >> Edge(label="Authenticated", color=COLORS["security"]) >> rate_limiter
    rate_limiter >> Edge(label="Within Limit", color=COLORS["success"]) >> api

    # API to services
    api >> Edge(label="Process", style="bold") >> chat_service
    chat_service >> validation

    # Service to middleware
    chat_service >> error_handler
    chat_service >> request_tracker

    # Service to data layer
    chat_service >> Edge(label="Store", color=COLORS["success"]) >> repo_interface
    chat_service >> Edge(label="Cache", color=COLORS["cache"]) >> cache_interface

    # Repository implementations
    repo_interface >> Edge(style="dashed") >> sqlite_impl
    repo_interface >> Edge(style="dashed") >> dynamo_impl

    # Cache implementations
    cache_interface >> Edge(style="dashed") >> redis_impl
    cache_interface >> Edge(style="dashed") >> memory_impl

    # External service calls
    chat_service >> Edge(label="LLM Call", color=COLORS["external"]) >> openrouter
    chat_service >> Edge(label="LLM Call", color=COLORS["external"]) >> gemini

    # Deployment relationships
    api >> Edge(style="dotted", label="Deploys to") >> local
    api >> Edge(style="dotted", label="Deploys to") >> docker
    api >> Edge(style="dotted", label="Deploys to") >> aws_lambda
