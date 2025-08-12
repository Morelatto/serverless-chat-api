#!/usr/bin/env python3
"""Protocol Patterns - YOUR ACTUAL typing.Protocol Implementation."""

from custom_icons import (
    DictCache,
    LiteLLM,
    Protocol,
    get_icon,
)
from diagram_helpers import COLORS, cluster_style
from diagrams import Cluster, Diagram, Edge
from diagrams.aws.database import Dynamodb
from diagrams.onprem.inmemory import Redis
from diagrams.programming.language import Python

with Diagram(
    "Protocol Pattern - Actual Python Implementation",
    filename="08_protocol_patterns_real",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "11",
        "bgcolor": "white",
        "pad": "0.5",
        "nodesep": "0.5",
        "ranksep": "0.8",
        "splines": "ortho",
    },
):
    # Your ChatService
    service = Python("ChatService")

    # YOUR ACTUAL Protocols (from protocols.py)
    with Cluster("typing.Protocol Definitions", graph_attr=cluster_style("api")):
        # Repository Protocol
        with Cluster("RepositoryProtocol", graph_attr={"bgcolor": "white", "style": "rounded"}):
            repo_protocol = Protocol("Protocol")
            repo_methods = Python(
                "async def save()\nasync def get_history()\nasync def health_check()"
            )
            repo_protocol >> Edge(style="invis") >> repo_methods

        # Cache Protocol
        with Cluster("CacheProtocol", graph_attr={"bgcolor": "white", "style": "rounded"}):
            cache_protocol = Protocol("Protocol")
            cache_methods = Python("async def get()\nasync def set()\nasync def health_check()")
            cache_protocol >> Edge(style="invis") >> cache_methods

        # LLM Protocol
        with Cluster("LLMProviderProtocol", graph_attr={"bgcolor": "white", "style": "rounded"}):
            llm_protocol = Protocol("Protocol")
            llm_methods = Python("async def complete()\nasync def health_check()")
            llm_protocol >> Edge(style="invis") >> llm_methods

    # YOUR ACTUAL Implementations
    with Cluster("Concrete Implementations", graph_attr=cluster_style("data")):
        # Repository implementations (YOUR code)
        with Cluster("Repositories"):
            sqlite = get_icon("aiosqlite", "SQLiteRepository")
            dynamo = Dynamodb("DynamoDBRepository")

        # Cache implementations (YOUR code)
        with Cluster("Caches"):
            redis_impl = Redis("RedisCache")
            memory = DictCache("InMemoryCache\n(dict)")

        # LLM implementations (YOUR code via litellm)
        with Cluster("LLM Providers"):
            openrouter = LiteLLM("OpenRouterProvider\n(via litellm)")
            gemini = LiteLLM("GeminiProvider\n(via litellm)")

    # YOUR Factory Functions (from factories.py)
    with Cluster("Factory Functions", graph_attr=cluster_style("cache")):
        create_repo = Python("create_repository()")
        create_cache = Python("create_cache()")
        create_llm = Python("create_llm_provider()")

        # YOUR environment checks
        env_checks = Python("if IS_LAMBDA:\n  DynamoDB\nelse:\n  SQLite")

        create_repo >> env_checks
        create_cache >> env_checks
        create_llm >> env_checks

    # How YOUR code actually works
    service >> Edge(color=COLORS["auth"], style="bold", label="uses") >> repo_protocol
    service >> Edge(color=COLORS["auth"], style="bold", label="uses") >> cache_protocol
    service >> Edge(color=COLORS["auth"], style="bold", label="uses") >> llm_protocol

    # Protocol satisfaction (duck typing in Python)
    (
        repo_protocol
        >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty", label="satisfies")
        >> sqlite
    )
    repo_protocol >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty") >> dynamo

    (
        cache_protocol
        >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty", label="satisfies")
        >> redis_impl
    )
    cache_protocol >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty") >> memory

    (
        llm_protocol
        >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty", label="satisfies")
        >> openrouter
    )
    llm_protocol >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty") >> gemini

    # Factory creates implementations
    env_checks >> Edge(color=COLORS["warning"], style="dotted") >> sqlite
    env_checks >> Edge(color=COLORS["warning"], style="dotted") >> dynamo
    env_checks >> Edge(color=COLORS["warning"], style="dotted") >> redis_impl
    env_checks >> Edge(color=COLORS["warning"], style="dotted") >> memory
    env_checks >> Edge(color=COLORS["warning"], style="dotted") >> openrouter
    env_checks >> Edge(color=COLORS["warning"], style="dotted") >> gemini

    # YOUR Dependency Injection (via FastAPI)
    with Cluster("FastAPI Dependency Injection", graph_attr=cluster_style("business")):
        depends = Python("Depends(get_chat_service)")
        singleton = Python("_service_instance")

        depends >> singleton >> service
