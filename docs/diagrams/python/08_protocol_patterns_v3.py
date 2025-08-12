#!/usr/bin/env python3
"""Protocol Patterns - Professional service icons, no text."""

from diagram_helpers import COLORS, cluster_style
from diagrams import Cluster, Diagram, Edge
from diagrams.aws.analytics import DataPipeline
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb, ElastiCache
from diagrams.aws.integration import SimpleQueueServiceSqs as SQS
from diagrams.aws.ml import Sagemaker
from diagrams.aws.storage import SimpleStorageServiceS3Bucket as S3
from diagrams.generic.database import SQL
from diagrams.onprem.ci import Jenkins
from diagrams.onprem.inmemory import Redis
from diagrams.programming.language import Bash, Python

with Diagram(
    "Protocol Pattern Architecture",
    filename="08_protocol_patterns_v3",
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
    # Service at the top
    service = Python("ChatService")

    # Protocol Contracts using CI/Pipeline icons
    with Cluster("Protocols", graph_attr=cluster_style("api")):
        # Repository Protocol
        with Cluster("Repository", graph_attr={"bgcolor": "white", "style": "rounded"}):
            repo_protocol = Jenkins("Repository")
            repo_contract = DataPipeline("")
            repo_protocol >> Edge(style="invis") >> repo_contract

        # Cache Protocol
        with Cluster("Cache", graph_attr={"bgcolor": "white", "style": "rounded"}):
            cache_protocol = Jenkins("Cache")
            cache_contract = SQS("")
            cache_protocol >> Edge(style="invis") >> cache_contract

        # LLM Protocol
        with Cluster("LLM", graph_attr={"bgcolor": "white", "style": "rounded"}):
            llm_protocol = Jenkins("LLM")
            llm_contract = Lambda("")
            llm_protocol >> Edge(style="invis") >> llm_contract

    # Duck Typing visualization with Python
    with Cluster("Duck Typing", graph_attr=cluster_style("business")):
        duck_type = Python("Type Check")
        interface_check = Bash("Interface")
        duck_type >> Edge(color=COLORS["info"], style="dashed") >> interface_check

    # Concrete Implementations
    with Cluster("Implementations", graph_attr=cluster_style("data")):
        # Repository implementations
        with Cluster("Repositories", graph_attr={"style": "invis"}):
            sqlite = SQL("SQLite")
            dynamo = Dynamodb("DynamoDB")

        # Cache implementations
        with Cluster("Caches", graph_attr={"style": "invis"}):
            redis_impl = Redis("Redis")
            memory = ElastiCache("Memory")

        # LLM implementations
        with Cluster("LLMs", graph_attr={"style": "invis"}):
            openrouter = Sagemaker("OpenRouter")
            gemini = Sagemaker("Gemini")

    # Factory Pattern using Lambda
    with Cluster("Factory", graph_attr=cluster_style("cache")):
        env_check = Lambda("Factory")

        # Condition checks
        check_env = S3("ENV")
        select_impl = DataPipeline("Select")

        env_check >> Edge(style="invis") >> check_env >> Edge(style="invis") >> select_impl

    # Service dependencies (needs protocols)
    service >> Edge(color=COLORS["auth"], style="bold", penwidth="2") >> repo_protocol
    service >> Edge(color=COLORS["auth"], style="bold", penwidth="2") >> cache_protocol
    service >> Edge(color=COLORS["auth"], style="bold", penwidth="2") >> llm_protocol

    # Protocols implemented by concrete classes (UML-style inheritance)
    (
        repo_protocol
        >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty", penwidth="2")
        >> sqlite
    )
    (
        repo_protocol
        >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty", penwidth="2")
        >> dynamo
    )

    (
        cache_protocol
        >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty", penwidth="2")
        >> redis_impl
    )
    (
        cache_protocol
        >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty", penwidth="2")
        >> memory
    )

    (
        llm_protocol
        >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty", penwidth="2")
        >> openrouter
    )
    (
        llm_protocol
        >> Edge(color=COLORS["success"], style="dashed", arrowhead="empty", penwidth="2")
        >> gemini
    )

    # Factory creates implementations
    select_impl >> Edge(color=COLORS["warning"], style="dotted") >> sqlite
    select_impl >> Edge(color=COLORS["warning"], style="dotted") >> dynamo
    select_impl >> Edge(color=COLORS["warning"], style="dotted") >> redis_impl
    select_impl >> Edge(color=COLORS["warning"], style="dotted") >> memory
    select_impl >> Edge(color=COLORS["warning"], style="dotted") >> openrouter
    select_impl >> Edge(color=COLORS["warning"], style="dotted") >> gemini

    # Duck typing checks
    for impl in [sqlite, dynamo, redis_impl, memory, openrouter, gemini]:
        impl >> Edge(color=COLORS["validate"], style="dotted", penwidth="1") >> interface_check
