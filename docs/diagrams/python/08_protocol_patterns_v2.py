#!/usr/bin/env python3
"""Protocol Patterns - Visual duck typing instead of code dumps."""

from diagram_helpers import COLORS
from diagrams import Cluster, Diagram, Edge
from diagrams.aws.database import Dynamodb
from diagrams.aws.ml import Sagemaker
from diagrams.generic.blank import Blank
from diagrams.generic.storage import Storage
from diagrams.onprem.inmemory import Redis
from diagrams.programming.language import Python

with Diagram(
    "Protocol Pattern (Visual Duck Typing)",
    filename="08_protocol_patterns_v2",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "11",
        "bgcolor": "white",
        "pad": "0.5",
        "nodesep": "0.5",
        "ranksep": "0.8",
    },
):
    # Service at the top
    service = Python("ChatService")

    # Visual Protocol Contracts (no code, just method icons)
    with Cluster(
        "Protocols (Interfaces)",
        graph_attr={"bgcolor": "#EDE9FE", "style": "rounded", "penwidth": "2"},
    ):
        # Repository Protocol (visual methods)
        with Cluster("Repository", graph_attr={"bgcolor": "white", "style": "rounded"}):
            repo_protocol = Storage("Repository")
            repo_methods = Blank("💾 save\n📚 history\n❤️ health")
            repo_protocol >> Edge(style="invis") >> repo_methods

        # Cache Protocol (visual methods)
        with Cluster("Cache", graph_attr={"bgcolor": "white", "style": "rounded"}):
            cache_protocol = Storage("Cache")
            cache_methods = Blank("📥 get\n📤 set\n❤️ health")
            cache_protocol >> Edge(style="invis") >> cache_methods

        # LLM Protocol (visual methods)
        with Cluster("LLM", graph_attr={"bgcolor": "white", "style": "rounded"}):
            llm_protocol = Sagemaker("LLM")
            llm_methods = Blank("🤖 complete\n❤️ health")
            llm_protocol >> Edge(style="invis") >> llm_methods

    # Visual Duck Typing - "If it quacks like a duck..."
    with Cluster("🦆 Duck Typing", graph_attr={"bgcolor": "#F0FDF4", "style": "dashed"}):
        duck = Blank("If it has these methods\n→ It IS this type")

    # Concrete Implementations (visual, no code)
    with Cluster("Implementations", graph_attr={"bgcolor": "#F9FAFB", "style": "rounded"}):
        # Repository implementations
        with Cluster("Repositories", graph_attr={"style": "invis"}):
            sqlite = Storage("SQLite")
            sqlite_icon = Blank("📁")
            dynamo = Dynamodb("DynamoDB")
            dynamo_icon = Blank("☁️")

            sqlite >> Edge(style="invis") >> sqlite_icon
            dynamo >> Edge(style="invis") >> dynamo_icon

        # Cache implementations
        with Cluster("Caches", graph_attr={"style": "invis"}):
            redis_impl = Redis("Redis")
            redis_icon = Blank("🔴")
            memory = Storage("Memory")
            memory_icon = Blank("🧠")

            redis_impl >> Edge(style="invis") >> redis_icon
            memory >> Edge(style="invis") >> memory_icon

        # LLM implementations
        with Cluster("LLMs", graph_attr={"style": "invis"}):
            openrouter = Sagemaker("OpenRouter")
            openrouter_icon = Blank("🌐")
            gemini = Sagemaker("Gemini")
            gemini_icon = Blank("✨")

            openrouter >> Edge(style="invis") >> openrouter_icon
            gemini >> Edge(style="invis") >> gemini_icon

    # Visual Factory Pattern (selection logic)
    with Cluster("Factory Selection", graph_attr={"bgcolor": "#FEF3C7", "style": "rounded"}):
        env_check = Blank("🔍 Check ENV")

        # Visual conditions
        conditions = [
            Blank("Lambda? → DynamoDB"),
            Blank("Redis URL? → Redis"),
            Blank("Provider? → LLM"),
        ]

        env_check >> Edge(style="invis") >> conditions[0]
        for i in range(len(conditions) - 1):
            conditions[i] >> Edge(style="invis") >> conditions[i + 1]

    # Dependency arrows (visual duck typing)
    service >> Edge(color=COLORS["auth"], style="bold", label="needs") >> repo_protocol
    service >> Edge(color=COLORS["auth"], style="bold", label="needs") >> cache_protocol
    service >> Edge(color=COLORS["auth"], style="bold", label="needs") >> llm_protocol

    # Implementation arrows (they "implement" by having the methods)
    repo_protocol >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty") >> sqlite
    repo_protocol >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty") >> dynamo

    cache_protocol >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty") >> redis_impl
    cache_protocol >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty") >> memory

    llm_protocol >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty") >> openrouter
    llm_protocol >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty") >> gemini

    # Factory creates implementations
    env_check >> Edge(color=COLORS["warning"], style="dotted") >> sqlite
    env_check >> Edge(color=COLORS["warning"], style="dotted") >> dynamo
    env_check >> Edge(color=COLORS["warning"], style="dotted") >> redis_impl
    env_check >> Edge(color=COLORS["warning"], style="dotted") >> memory

    # Benefits (visual icons)
    with Cluster("Benefits", graph_attr={"bgcolor": "#DCFCE7", "style": "rounded"}):
        benefits = Blank("🔌 Pluggable\n" "🧪 Testable\n" "🔄 Swappable\n" "🚫 No coupling")
