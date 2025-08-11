#!/usr/bin/env python3
"""Generate final set of crucial architecture diagrams with proper icons."""

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import LambdaFunction
from diagrams.aws.database import DynamodbTable
from diagrams.aws.management import Cloudwatch
from diagrams.aws.management import SystemsManagerParameterStore as Config
from diagrams.aws.network import APIGateway
from diagrams.aws.security import SecretsManager

# Custom for OpenRouter
# Google Cloud for Gemini
from diagrams.gcp.ml import AIHub as Gemini
from diagrams.generic.compute import Rack

# Generic icons for protocols and components
from diagrams.generic.database import SQL
from diagrams.generic.storage import Storage

# OnPrem and Generic icons
from diagrams.onprem.client import Users
from diagrams.onprem.container import Docker
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.network import Internet
from diagrams.onprem.vcs import Git as ConfigFile
from diagrams.programming.flowchart import Decision

# Programming and framework icons
from diagrams.programming.framework import FastAPI
from diagrams.programming.language import Python

# Consistent styling
GRAPH_ATTR = {
    "fontsize": "16",
    "fontname": "Arial",
    "bgcolor": "#ffffff",
    "pad": "0.8",
    "nodesep": "1.0",
    "ranksep": "1.5",
    "splines": "ortho",
    "compound": "true",
}

NODE_ATTR = {
    "fontsize": "12",
    "fontname": "Arial",
    "shape": "box",
    "style": "rounded,filled",
    "fillcolor": "#ffffff",
}

EDGE_ATTR = {
    "fontsize": "10",
    "fontname": "Arial",
}


def create_system_architecture():
    """Create the main system architecture diagram - CRUCIAL."""

    with Diagram(
        "Chat API - System Architecture",
        filename="01_system_architecture",
        outformat="png",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
        show=False,
        direction="TB",
    ):
        # Clients
        clients = Users("API Clients")

        # API Layer
        with Cluster("API Gateway", graph_attr={"bgcolor": "#E3F2FD"}):
            api = FastAPI("FastAPI")

        # Core Application
        with Cluster("Application Core", graph_attr={"bgcolor": "#E8F5E9"}):
            chat_service = Python("ChatService")

            with Cluster("Dependency Injection"):
                factory = Python("ServiceFactory")

        # Protocol Layer
        with Cluster("Protocol Abstractions", graph_attr={"bgcolor": "#FFF3E0"}):
            protocols = Rack("Repository | Cache | LLM Provider")

        # Implementations
        with Cluster("Storage", graph_attr={"bgcolor": "#F3E5F5"}):
            sqlite = SQL("SQLite")
            dynamodb = DynamodbTable("DynamoDB")

        with Cluster("Cache", graph_attr={"bgcolor": "#E0F2F1"}):
            memory = Storage("In-Memory")
            redis = Redis("Redis")

        # External Services
        with Cluster("LLM Providers", graph_attr={"bgcolor": "#E8EAF6"}):
            gemini = Gemini("Gemini")
            openrouter = Internet("OpenRouter")  # Using Internet icon as placeholder

        # Main flow
        clients >> Edge(color="#1976D2", style="bold") >> api
        api >> chat_service
        chat_service >> factory
        factory >> Edge(style="dashed", label="creates") >> protocols

        # Implementation connections
        protocols >> Edge(style="dotted", label="dev") >> [sqlite, memory]
        protocols >> Edge(style="dotted", label="prod") >> [dynamodb, redis]
        protocols >> Edge(color="#4CAF50", label="primary") >> gemini
        protocols >> Edge(color="#FF9800", label="fallback") >> openrouter


def create_aws_production():
    """Create AWS production deployment - CRUCIAL."""

    with Diagram(
        "Chat API - AWS Production",
        filename="02_aws_production",
        outformat="png",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
        show=False,
        direction="TB",
    ):
        # Entry
        users = Users("Clients")

        with Cluster("AWS Infrastructure", graph_attr={"bgcolor": "#FFF8E1"}):
            # API Gateway
            gateway = APIGateway("API Gateway")

            # Compute
            with Cluster("Compute"):
                lambda_fn = LambdaFunction("Lambda\nContainer")

            # Data Layer
            with Cluster("Data Layer"):
                dynamodb = DynamodbTable("DynamoDB")
                redis = Redis("ElastiCache")

            # Security & Monitoring
            with Cluster("Operations"):
                secrets = SecretsManager("Secrets")
                logs = Cloudwatch("CloudWatch")

        # External
        llm = Internet("LLM APIs")

        # Flow with numbered steps
        users >> Edge(label="1", color="#1976D2", style="bold") >> gateway
        gateway >> Edge(label="2") >> lambda_fn
        lambda_fn >> Edge(label="3") >> dynamodb
        lambda_fn >> Edge(label="4", style="dashed") >> redis
        lambda_fn >> Edge(label="5", color="#4CAF50", style="bold") >> llm

        # Operations
        lambda_fn >> Edge(style="dotted") >> [secrets, logs]


def create_request_flow():
    """Create request processing flow - CRUCIAL."""

    with Diagram(
        "Chat API - Request Flow",
        filename="03_request_flow",
        outformat="png",
        graph_attr={**GRAPH_ATTR, "rankdir": "LR"},
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
        show=False,
        direction="LR",
    ):
        # Start
        client = Users("Client")

        # Processing stages
        with Cluster("1. Validation"):
            validate = FastAPI("Validate\n& Rate Limit")

        with Cluster("2. Cache Check"):
            cache = Redis("Cache")

        with Cluster("3. LLM Processing"):
            primary = Gemini("Gemini")
            fallback = Internet("OpenRouter")

        with Cluster("4. Persistence"):
            db = DynamodbTable("Save")

        # End
        response = Users("Response")

        # Main flow
        client >> validate
        validate >> cache

        # Cache hit (fast path)
        cache >> Edge(label="HIT", color="#4CAF50", style="bold") >> response

        # Cache miss
        cache >> Edge(label="MISS", style="dashed") >> primary
        primary >> Edge(label="fail", color="#F44336", style="dashed") >> fallback
        primary >> Edge(label="success", color="#4CAF50") >> db
        fallback >> db
        db >> response


def create_local_development():
    """Create local development setup - CRUCIAL."""

    with Diagram(
        "Chat API - Local Development",
        filename="04_local_development",
        outformat="png",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
        show=False,
        direction="TB",
    ):
        # Developer
        dev = Users("Developer")

        with Cluster("Local Environment"):
            # Application
            with Cluster("Application", graph_attr={"bgcolor": "#E8F5E9"}):
                python = Python("Python 3.11")
                fastapi = FastAPI("FastAPI\nDev Server")

            # Storage
            with Cluster("Local Storage", graph_attr={"bgcolor": "#FFF3E0"}):
                sqlite = SQL("SQLite")
                cache = Storage("Memory Cache")

        # Docker alternative
        with Cluster("Docker Option", graph_attr={"bgcolor": "#E3F2FD"}):
            docker = Docker("Docker\nCompose")

        # External
        llm = Internet("LLM APIs")

        # Connections
        dev >> python >> fastapi
        fastapi >> [sqlite, cache]
        fastapi >> Edge(color="#4CAF50", style="bold") >> llm

        dev >> Edge(label="OR", style="dashed") >> docker
        docker >> Edge(style="dashed") >> fastapi


def create_dependency_injection():
    """Create dependency injection diagram - CRUCIAL for understanding."""

    with Diagram(
        "Chat API - Dependency Injection",
        filename="05_dependency_injection",
        outformat="png",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
        show=False,
        direction="TB",
    ):
        # Configuration
        with Cluster("Configuration", graph_attr={"bgcolor": "#F5F5F5"}):
            env = Config("Environment\nVariables")

        # Factory
        with Cluster("ServiceFactory", graph_attr={"bgcolor": "#E1BEE7"}):
            factory = Rack("DI Container")
            detect = Decision("Environment\nDetection")

        # Protocols (using interface-like representations)
        with Cluster("Protocol Interfaces", graph_attr={"bgcolor": "#BBDEFB"}):
            repo_proto = SQL("Repository\nProtocol")
            cache_proto = Storage("Cache\nProtocol")
            llm_proto = Internet("LLM Provider\nProtocol")

        # Implementations
        with Cluster("Local Implementations", graph_attr={"bgcolor": "#C8E6C9"}):
            local_sqlite = SQL("SQLite")
            local_memory = Storage("In-Memory")
            local_mock = ConfigFile("Mock LLM")

        with Cluster("Production Implementations", graph_attr={"bgcolor": "#FFE0B2"}):
            prod_dynamo = DynamodbTable("DynamoDB")
            prod_redis = Redis("Redis")
            prod_gemini = Gemini("Gemini API")

        # Service
        with Cluster("Service Layer", graph_attr={"bgcolor": "#F3E5F5"}):
            service = Python("ChatService")

        # Configuration flow
        env >> factory
        factory >> detect

        # Environment detection branches
        detect >> Edge(label="if LOCAL", style="dashed", color="#4CAF50") >> local_sqlite
        detect >> Edge(style="dashed", color="#4CAF50") >> local_memory
        detect >> Edge(style="dashed", color="#4CAF50") >> local_mock

        detect >> Edge(label="if AWS", style="dashed", color="#FF9800") >> prod_dynamo
        detect >> Edge(style="dashed", color="#FF9800") >> prod_redis
        detect >> Edge(style="dashed", color="#FF9800") >> prod_gemini

        # Protocol implementations
        repo_proto >> Edge(style="dotted") >> local_sqlite
        repo_proto >> Edge(style="dotted") >> prod_dynamo

        cache_proto >> Edge(style="dotted") >> local_memory
        cache_proto >> Edge(style="dotted") >> prod_redis

        llm_proto >> Edge(style="dotted") >> local_mock
        llm_proto >> Edge(style="dotted") >> prod_gemini

        # Service creation
        factory >> Edge(label="creates", style="bold", color="#7C4DFF") >> service
        [repo_proto, cache_proto, llm_proto] >> Edge(label="injects", style="dotted") >> service


if __name__ == "__main__":
    print("🎨 Generating final crucial diagrams with proper icons...")

    # Generate only the crucial diagrams
    diagrams = [
        ("System Architecture", create_system_architecture),
        ("AWS Production", create_aws_production),
        ("Request Flow", create_request_flow),
        ("Local Development", create_local_development),
        ("Dependency Injection", create_dependency_injection),
    ]

    for name, func in diagrams:
        func()
        print(f"✅ Generated: {name}")

    print("\n📊 Final diagram set complete!")
    print("   5 crucial diagrams with proper technology icons")
    print("   Clear separation of concerns")
    print("   Production-ready documentation")
