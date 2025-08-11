#!/usr/bin/env python3
"""Generate improved architecture diagrams with standardized patterns and correct icons."""

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import LambdaFunction
from diagrams.aws.database import DynamodbTable
from diagrams.aws.devtools import XRay  # For tracing
from diagrams.aws.management import Cloudwatch
from diagrams.aws.network import (
    APIGateway,
    CloudFront,  # For CDN/API layer
)
from diagrams.aws.security import SecretsManager

# Custom icons representation
from diagrams.gcp.ml import AIHub as Gemini

# Generic icons for better representation
from diagrams.generic.database import SQL  # Generic SQL for SQLite
from diagrams.generic.network import Firewall  # For rate limiting
from diagrams.generic.storage import Storage

# OnPrem and cloud icons
from diagrams.onprem.client import Users
from diagrams.onprem.container import Docker
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.logging import FluentBit  # For logging
from diagrams.onprem.monitoring import Prometheus  # For monitoring

# Better icons for abstractions and protocols
from diagrams.programming.flowchart import Decision, Document
from diagrams.programming.framework import FastAPI
from diagrams.programming.language import Python
from diagrams.saas.chat import Discord  # Better than Internet for chat API

# Standard color semantics
COLORS = {
    "external": "#2196F3",  # Blue: External systems/APIs
    "application": "#4CAF50",  # Green: Your application code
    "infrastructure": "#FF9800",  # Orange: Infrastructure/Storage
    "security": "#F44336",  # Red: Security/Auth components
    "protocol": "#9E9E9E",  # Gray: Protocols/Interfaces
    "success": "#4CAF50",  # Green: Success path
    "error": "#F44336",  # Red: Error path
    "cache": "#00BCD4",  # Cyan: Cache hit
}

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


def create_logical_architecture():
    """Create logical architecture without deployment concerns."""

    with Diagram(
        "Chat API - Logical Architecture",
        filename="01_logical_architecture",
        outformat="png",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
        show=False,
        direction="TB",
    ):
        # API Clients
        clients = Users("API Clients")

        # API Layer with cross-cutting concerns
        with Cluster("API Layer", graph_attr={"bgcolor": "#E3F2FD"}):
            api = FastAPI("FastAPI")
            rate_limiter = Firewall("Rate Limiter")
            validator = Document("Pydantic\nValidation")

        # Application Core
        with Cluster("Application Core", graph_attr={"bgcolor": "#E8F5E9"}):
            handlers = Python("Request\nHandlers")
            service = Python("Chat\nService")
            serializer = Document("JSON\nSerializer")

        # Protocol Layer (using interface stereotype)
        with Cluster(
            "<<interface>>\nProtocol Abstractions",
            graph_attr={"bgcolor": "#F5F5F5", "style": "dashed"},
        ):
            repo_protocol = Document("Repository\nProtocol")
            cache_protocol = Document("Cache\nProtocol")
            llm_protocol = Document("LLM Provider\nProtocol")

        # Concrete Implementations
        with Cluster("Implementations", graph_attr={"bgcolor": "#FFF3E0"}):
            with Cluster("Storage"):
                sqlite_impl = SQL("SQLite\nRepository")
                dynamo_impl = DynamodbTable("DynamoDB\nRepository")

            with Cluster("Cache"):
                memory_impl = Storage("Memory\nCache")
                redis_impl = Redis("Redis\nCache")

            with Cluster("LLM Providers"):
                gemini_impl = Gemini("Gemini\nProvider")
                openrouter_impl = Discord("OpenRouter\nProvider")

        # Cross-cutting concerns
        with Cluster("Cross-Cutting", graph_attr={"bgcolor": "#F3E5F5"}):
            logger = FluentBit("Structured\nLogging")
            metrics = Prometheus("Metrics")
            health = Document("Health\nChecks")

        # Request flow with proper sequence
        clients >> Edge(label="1", color=COLORS["external"]) >> api
        api >> Edge(label="2") >> rate_limiter
        rate_limiter >> Edge(label="3") >> validator
        validator >> Edge(label="4") >> handlers
        handlers >> Edge(label="5", color=COLORS["application"]) >> service
        service >> Edge(label="6") >> serializer

        # Protocol implementations (correct direction)
        (
            service
            >> Edge(label="uses", style="dashed")
            >> [repo_protocol, cache_protocol, llm_protocol]
        )

        # Implementations satisfy protocols
        (
            sqlite_impl
            >> Edge(label="implements", style="dotted", color=COLORS["protocol"])
            >> repo_protocol
        )
        (
            dynamo_impl
            >> Edge(label="implements", style="dotted", color=COLORS["protocol"])
            >> repo_protocol
        )

        (
            memory_impl
            >> Edge(label="implements", style="dotted", color=COLORS["protocol"])
            >> cache_protocol
        )
        (
            redis_impl
            >> Edge(label="implements", style="dotted", color=COLORS["protocol"])
            >> cache_protocol
        )

        (
            gemini_impl
            >> Edge(label="implements", style="dotted", color=COLORS["protocol"])
            >> llm_protocol
        )
        (
            openrouter_impl
            >> Edge(label="implements", style="dotted", color=COLORS["protocol"])
            >> llm_protocol
        )

        # Cross-cutting aspect connections
        [handlers, service] >> Edge(style="dotted", color=COLORS["protocol"]) >> logger
        service >> Edge(style="dotted", color=COLORS["protocol"]) >> metrics
        api >> Edge(style="dotted", color=COLORS["protocol"]) >> health


def create_request_processing_flow():
    """Create detailed request processing with error paths and data transformations."""

    with Diagram(
        "Chat API - Request Processing Flow",
        filename="02_request_processing",
        outformat="png",
        graph_attr={**GRAPH_ATTR, "rankdir": "LR"},
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
        show=False,
        direction="LR",
    ):
        # Input
        client = Users("Client")

        # Validation Layer
        with Cluster("1. Input Validation"):
            validate = Document("Pydantic\nValidation")
            rate_check = Firewall("Rate Limit\nCheck")

        # Transform Layer
        with Cluster("2. Transform"):
            deserialize = Document("JSON\nDeserialize")
            normalize = Document("Normalize\nInput")

        # Cache Layer
        with Cluster("3. Cache Check"):
            cache_key = Document("Generate\nCache Key")
            cache_lookup = Redis("Cache\nLookup")
            cache_data = Storage("Cached\nData")

        # LLM Processing
        with Cluster("4. LLM Processing"):
            llm_primary = Gemini("Primary:\nGemini")
            llm_fallback = Discord("Fallback:\nOpenRouter")
            parse_response = Document("Parse LLM\nResponse")

        # Persistence
        with Cluster("5. Persistence"):
            save_db = DynamodbTable("Save to\nDatabase")
            update_cache = Redis("Update\nCache")

        # Response Formation
        with Cluster("6. Response"):
            serialize = Document("JSON\nSerialize")
            response = Users("Response")

        # Error Handling
        error = Document("Error\nHandler")

        # Main flow with sequence numbers
        client >> Edge(label="1", color=COLORS["external"]) >> validate
        validate >> Edge(label="2a: valid") >> rate_check
        validate >> Edge(label="2b: invalid", color=COLORS["error"]) >> error

        rate_check >> Edge(label="3a: ok") >> deserialize
        rate_check >> Edge(label="3b: exceeded", color=COLORS["error"]) >> error

        deserialize >> Edge(label="4") >> normalize
        normalize >> Edge(label="5") >> cache_key
        cache_key >> Edge(label="6") >> cache_lookup

        # Cache hit path (fast)
        cache_lookup >> Edge(label="7a: HIT", color=COLORS["cache"], style="bold") >> cache_data
        cache_data >> Edge(label="8a", color=COLORS["cache"]) >> serialize

        # Cache miss path
        cache_lookup >> Edge(label="7b: MISS", style="dashed") >> llm_primary
        llm_primary >> Edge(label="8b: success", color=COLORS["success"]) >> parse_response
        llm_primary >> Edge(label="8c: fail", color=COLORS["error"], style="dashed") >> llm_fallback
        llm_fallback >> Edge(label="9a: success") >> parse_response
        llm_fallback >> Edge(label="9b: fail", color=COLORS["error"]) >> error

        parse_response >> Edge(label="10") >> save_db
        save_db >> Edge(label="11") >> update_cache
        update_cache >> Edge(label="12") >> serialize

        serialize >> Edge(label="13", color=COLORS["success"]) >> response
        error >> Edge(label="error", color=COLORS["error"]) >> response


def create_deployment_aws():
    """AWS production deployment architecture."""

    with Diagram(
        "Chat API - AWS Production Deployment",
        filename="03_aws_deployment",
        outformat="png",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
        show=False,
        direction="TB",
    ):
        # External
        users = Users("API Clients")

        with Cluster("AWS Cloud", graph_attr={"bgcolor": "#FFF8E1"}):
            # Edge Layer
            with Cluster("Edge Layer"):
                cdn = CloudFront("CloudFront\nCDN")
                gateway = APIGateway("API Gateway\n[1..n]")

            # Compute Layer (showing cardinality)
            with Cluster("Compute Layer"):
                lambda_fn = LambdaFunction("Lambda\n[1..100]\n(Concurrent)")

            # Data Layer
            with Cluster("Data Layer"):
                dynamodb = DynamodbTable("DynamoDB\n[On-Demand]")
                elasticache = Redis("ElastiCache\n[2 nodes]")

            # Security & Operations
            with Cluster("Security & Operations"):
                secrets = SecretsManager("Secrets\nManager")
                cloudwatch = Cloudwatch("CloudWatch\nLogs & Metrics")
                xray = XRay("X-Ray\nTracing")

        # External Services
        with Cluster("External LLM Services", graph_attr={"bgcolor": "#E8EAF6"}):
            gemini_api = Gemini("Google\nGemini API")
            openrouter_api = Discord("OpenRouter\nAPI")

        # Connections with cardinality
        users >> Edge(label="HTTPS", color=COLORS["external"]) >> cdn
        cdn >> Edge(label="1..*") >> gateway
        gateway >> Edge(label="1..100", color=COLORS["application"]) >> lambda_fn

        # Lambda connections
        lambda_fn >> Edge(label="1", color=COLORS["infrastructure"]) >> dynamodb
        lambda_fn >> Edge(label="0..1", style="dashed") >> elasticache
        lambda_fn >> Edge(label="1", color=COLORS["security"]) >> secrets
        lambda_fn >> Edge(label="*") >> cloudwatch
        lambda_fn >> Edge(label="*", style="dotted") >> xray

        # External API calls
        lambda_fn >> Edge(label="1", color=COLORS["external"], style="bold") >> gemini_api
        lambda_fn >> Edge(label="0..1", color=COLORS["external"], style="dashed") >> openrouter_api


def create_deployment_local():
    """Local development deployment."""

    with Diagram(
        "Chat API - Local Development Deployment",
        filename="04_local_deployment",
        outformat="png",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
        show=False,
        direction="TB",
    ):
        # Developer
        dev = Users("Developer")

        with Cluster("Development Machine"):
            # Direct Python
            with Cluster("Native Python", graph_attr={"bgcolor": "#E8F5E9"}):
                python = Python("Python 3.11+\n[uv]")
                fastapi_dev = FastAPI("FastAPI\n[--reload]")
                sqlite = SQL("SQLite\n[file]")
                memory = Storage("Dict Cache\n[in-memory]")

            # Docker option
            with Cluster("Docker Alternative", graph_attr={"bgcolor": "#E3F2FD"}):
                docker = Docker("Docker\nCompose")
                container_api = FastAPI("Container\nAPI")
                container_db = SQL("Container\nSQLite")

        # External Services (same as prod)
        with Cluster("External Services", graph_attr={"bgcolor": "#E8EAF6"}):
            llm_apis = Discord("LLM APIs\n(Gemini/OpenRouter)")

        # Development tools
        with Cluster("Development Tools", graph_attr={"bgcolor": "#F3E5F5"}):
            pytest = Document("Pytest\n[tests]")
            coverage = Document("Coverage\n[80%+]")
            linter = Document("Ruff\n[lint]")

        # Connections
        dev >> Edge(label="1", color=COLORS["application"]) >> python
        python >> Edge(label="2") >> fastapi_dev
        fastapi_dev >> Edge(label="3a") >> sqlite
        fastapi_dev >> Edge(label="3b") >> memory
        fastapi_dev >> Edge(label="4", color=COLORS["external"]) >> llm_apis

        # Docker alternative
        dev >> Edge(label="OR", style="dashed", color=COLORS["protocol"]) >> docker
        docker >> Edge(label="2") >> container_api
        container_api >> Edge(label="3") >> container_db
        container_api >> Edge(label="4", color=COLORS["external"]) >> llm_apis

        # Testing connections
        pytest >> Edge(style="dotted") >> [fastapi_dev, sqlite, memory]
        coverage >> Edge(style="dotted") >> pytest
        linter >> Edge(style="dotted") >> python


def create_dependency_injection_flow():
    """Show how dependency injection works at runtime."""

    with Diagram(
        "Chat API - Dependency Injection Flow",
        filename="05_dependency_injection",
        outformat="png",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
        show=False,
        direction="TB",
    ):
        # Configuration Source
        with Cluster("Configuration"):
            env_vars = Document("Environment\nVariables")
            config = Python("Settings\nClass")

        # Factory Pattern
        with Cluster("Factory Pattern", graph_attr={"bgcolor": "#E1BEE7"}):
            factory = Python("ServiceFactory")
            env_detect = Decision("Environment\nDetection")

            # Factory methods
            create_repo = Document("create_repository()")
            create_cache = Document("create_cache()")
            create_llm = Document("create_llm_provider()")

        # Protocols (interfaces)
        with Cluster(
            "<<interface>>\nProtocols", graph_attr={"bgcolor": "#F5F5F5", "style": "dashed"}
        ):
            i_repo = Document("Repository\nProtocol")
            i_cache = Document("Cache\nProtocol")
            i_llm = Document("LLMProvider\nProtocol")

        # Concrete Implementations
        with Cluster("Concrete Implementations"):
            # Repository implementations
            with Cluster("Repository", graph_attr={"bgcolor": "#FFF3E0"}):
                sqlite_repo = SQL("SQLiteRepository")
                dynamo_repo = DynamodbTable("DynamoDBRepository")

            # Cache implementations
            with Cluster("Cache", graph_attr={"bgcolor": "#E0F2F1"}):
                memory_cache = Storage("MemoryCache")
                redis_cache = Redis("RedisCache")

            # LLM implementations
            with Cluster("LLM", graph_attr={"bgcolor": "#E8EAF6"}):
                gemini_provider = Gemini("GeminiProvider")
                openrouter_provider = Discord("OpenRouterProvider")

        # Service Layer
        with Cluster("Service Layer", graph_attr={"bgcolor": "#C8E6C9"}):
            app_state = Python("App State")
            chat_service = Python("ChatService")

        # Configuration flow
        env_vars >> Edge(label="1: load", color=COLORS["application"]) >> config
        config >> Edge(label="2: init") >> factory
        factory >> Edge(label="3: detect") >> env_detect

        # Factory method invocations
        env_detect >> Edge(label="4a: LOCAL", style="dashed") >> create_repo
        env_detect >> Edge(label="4b: LOCAL", style="dashed") >> create_cache
        env_detect >> Edge(label="4c: LOCAL", style="dashed") >> create_llm

        # Factory creates concrete implementations
        create_repo >> Edge(label="5a: if LOCAL", color=COLORS["success"]) >> sqlite_repo
        create_repo >> Edge(label="5b: if AWS", color=COLORS["infrastructure"]) >> dynamo_repo

        create_cache >> Edge(label="6a: if LOCAL", color=COLORS["success"]) >> memory_cache
        create_cache >> Edge(label="6b: if REDIS", color=COLORS["infrastructure"]) >> redis_cache

        create_llm >> Edge(label="7a: primary", color=COLORS["external"]) >> gemini_provider
        (
            create_llm
            >> Edge(label="7b: fallback", color=COLORS["external"], style="dashed")
            >> openrouter_provider
        )

        # Implementations satisfy protocols
        (
            [sqlite_repo, dynamo_repo]
            >> Edge(label="implements", style="dotted", color=COLORS["protocol"])
            >> i_repo
        )
        (
            [memory_cache, redis_cache]
            >> Edge(label="implements", style="dotted", color=COLORS["protocol"])
            >> i_cache
        )
        (
            [gemini_provider, openrouter_provider]
            >> Edge(label="implements", style="dotted", color=COLORS["protocol"])
            >> i_llm
        )

        # Injection into app state
        factory >> Edge(label="8: inject", color=COLORS["application"], style="bold") >> app_state
        [i_repo, i_cache, i_llm] >> Edge(label="9: provides", style="dotted") >> app_state

        # Service uses injected dependencies
        app_state >> Edge(label="10: uses", color=COLORS["application"]) >> chat_service


def create_component_interactions():
    """Show component interactions and async/sync boundaries."""

    with Diagram(
        "Chat API - Component Interactions",
        filename="06_component_interactions",
        outformat="png",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
        show=False,
        direction="TB",
    ):
        # Component types with state indicators
        with Cluster("Stateless Components", graph_attr={"bgcolor": "#E8F5E9"}):
            handlers = Python("Handlers\n[async]")
            validators = Document("Validators\n[sync]")
            serializers = Document("Serializers\n[sync]")
            factory = Python("Factory\n[sync]")

        with Cluster("Stateful Components", graph_attr={"bgcolor": "#FFE0B2"}):
            app_state = Python("App State\n[singleton]")
            cache = Redis("Cache\n[async]")
            repository = DynamodbTable("Repository\n[async]")

        with Cluster("External Components", graph_attr={"bgcolor": "#E3F2FD"}):
            llm_provider = Discord("LLM Provider\n[async]")
            monitoring = Prometheus("Metrics\n[async]")

        # Async boundaries
        with Cluster("Async Boundary", graph_attr={"bgcolor": "#F5F5F5", "style": "dashed"}):
            async_queue = Document("Event Loop")

        # Interactions with async/sync indicators
        handlers >> Edge(label="async", color=COLORS["success"]) >> validators
        validators >> Edge(label="sync", color=COLORS["application"]) >> serializers

        handlers >> Edge(label="async", color=COLORS["success"], style="bold") >> cache
        handlers >> Edge(label="async", color=COLORS["success"], style="bold") >> repository
        handlers >> Edge(label="async", color=COLORS["external"], style="bold") >> llm_provider

        # State management
        factory >> Edge(label="creates\n[startup]", color=COLORS["application"]) >> app_state
        app_state >> Edge(label="holds\n[1]", style="dotted") >> [cache, repository, llm_provider]

        # Cross-cutting
        (
            [handlers, cache, repository, llm_provider]
            >> Edge(label="async", style="dotted", color=COLORS["protocol"])
            >> monitoring
        )

        # Async coordination
        (
            [cache, repository, llm_provider]
            >> Edge(label="await", style="dashed", color=COLORS["protocol"])
            >> async_queue
        )
        async_queue >> Edge(label="schedule", style="dashed", color=COLORS["protocol"]) >> handlers


if __name__ == "__main__":
    print("🎨 Generating improved architecture diagrams...")

    diagrams = [
        ("Logical Architecture", create_logical_architecture),
        ("Request Processing Flow", create_request_processing_flow),
        ("AWS Deployment", create_deployment_aws),
        ("Local Deployment", create_deployment_local),
        ("Dependency Injection", create_dependency_injection_flow),
        ("Component Interactions", create_component_interactions),
    ]

    for name, func in diagrams:
        func()
        print(f"✅ Generated: {name}")

    print("\n📊 Improved diagram set complete!")
    print("   - Fixed icon usage (generic SQL for SQLite)")
    print("   - Standardized protocol representation")
    print("   - Added error paths and sequence numbers")
    print("   - Separated logical from deployment concerns")
    print("   - Applied standard color semantics")
    print("   - Added cardinality and state indicators")
    print("   - Included missing components")
