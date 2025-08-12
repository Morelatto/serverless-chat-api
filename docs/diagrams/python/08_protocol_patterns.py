#!/usr/bin/env python3
"""Protocol Patterns - Repository and Cache abstraction patterns."""

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.database import Dynamodb
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.programming.flowchart import Document
from diagrams.programming.language import Python

COLORS = {
    "protocol": "#6f42c1",
    "implementation": "#17a2b8",
    "runtime": "#28a745",
    "abstract": "#ffc107",
}

with Diagram(
    "Protocol Pattern Implementation",
    filename="08_protocol_patterns",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "11",
        "bgcolor": "white",
        "pad": "0.5",
        "splines": "ortho",
    },
):
    # Service Layer
    with Cluster("Service Layer", graph_attr={"bgcolor": "#f0f8ff"}):
        chat_service = Python("ChatService")
        service_code = Document(
            "class ChatService:\n"
            "  def __init__(self,\n"
            "    repository: Repository,\n"
            "    cache: Cache,\n"
            "    llm: LLMProvider\n"
            "  )"
        )

    # Protocol Definitions
    with Cluster("Protocol Definitions (Abstract)", graph_attr={"bgcolor": "#fff9e6"}):
        repo_protocol = Document(
            "class Repository(Protocol):\n"
            "  async def startup() -> None\n"
            "  async def shutdown() -> None\n"
            "  async def save(**kwargs) -> None\n"
            "  async def get_history() -> list\n"
            "  async def health_check() -> bool"
        )

        cache_protocol = Document(
            "class Cache(Protocol):\n"
            "  async def startup() -> None\n"
            "  async def shutdown() -> None\n"
            "  async def get(key) -> dict | None\n"
            "  async def set(key, value, ttl) -> None\n"
            "  async def health_check() -> bool"
        )

        llm_protocol = Document(
            "class LLMProvider(Protocol):\n"
            "  async def complete(prompt) -> dict\n"
            "  async def health_check() -> bool\n"
            "  @property\n"
            "  def name() -> str"
        )

    # Repository Implementations
    with Cluster("Repository Implementations", graph_attr={"bgcolor": "#e8f5e9"}):
        sqlite_impl = Python("SQLiteRepository")
        sqlite_details = Document(
            "Uses aiosqlite\n" "Local file storage\n" "SQL queries\n" "Indexes for performance"
        )
        sqlite_db = PostgreSQL("SQLite DB")

        dynamo_impl = Python("DynamoDBRepository")
        dynamo_details = Document(
            "Uses aioboto3\n" "AWS managed\n" "NoSQL operations\n" "Auto-scaling"
        )
        dynamo_db = Dynamodb("DynamoDB")

        sqlite_impl >> sqlite_details >> sqlite_db
        dynamo_impl >> dynamo_details >> dynamo_db

    # Cache Implementations
    with Cluster("Cache Implementations", graph_attr={"bgcolor": "#ffe6e6"}):
        redis_impl = Python("RedisCache")
        redis_details = Document("Uses redis-py\n" "Network cache\n" "TTL support\n" "Distributed")
        redis_cache = Redis("Redis")

        memory_impl = Python("InMemoryCache")
        memory_details = Document("Python dict\n" "Process-local\n" "LRU eviction\n" "Fast access")
        memory_cache = Python("Dict Cache")

        redis_impl >> redis_details >> redis_cache
        memory_impl >> memory_details >> memory_cache

    # LLM Implementations
    with Cluster("LLM Provider Implementations", graph_attr={"bgcolor": "#f0f0f0"}):
        openrouter_impl = Python("OpenRouterProvider")
        openrouter_details = Document(
            "Uses litellm\n" "Multiple models\n" "Retry logic\n" "Rate limiting"
        )

        gemini_impl = Python("GeminiProvider")
        gemini_details = Document("Uses litellm\n" "Google AI\n" "Retry logic\n" "Token tracking")

        openrouter_impl >> openrouter_details
        gemini_impl >> gemini_details

    # Factory Functions
    with Cluster("Factory Pattern", graph_attr={"bgcolor": "#e6f3ff"}):
        repo_factory = Document(
            "def create_repository():\n"
            "  if is_lambda:\n"
            "    return DynamoDBRepository()\n"
            "  else:\n"
            "    return SQLiteRepository()"
        )

        cache_factory = Document(
            "def create_cache():\n"
            "  if settings.redis_url:\n"
            "    return RedisCache()\n"
            "  else:\n"
            "    return InMemoryCache()"
        )

        llm_factory = Document(
            "def create_llm_provider():\n"
            "  if provider == 'gemini':\n"
            "    return GeminiProvider()\n"
            "  else:\n"
            "    return OpenRouterProvider()"
        )

    # Connection flow
    chat_service >> Edge(label="Depends on", color=COLORS["protocol"]) >> repo_protocol
    chat_service >> Edge(label="Depends on", color=COLORS["protocol"]) >> cache_protocol
    chat_service >> Edge(label="Depends on", color=COLORS["protocol"]) >> llm_protocol

    # Protocol to implementation
    (
        repo_protocol
        >> Edge(label="Implements", style="dashed", color=COLORS["abstract"])
        >> sqlite_impl
    )
    (
        repo_protocol
        >> Edge(label="Implements", style="dashed", color=COLORS["abstract"])
        >> dynamo_impl
    )

    (
        cache_protocol
        >> Edge(label="Implements", style="dashed", color=COLORS["abstract"])
        >> redis_impl
    )
    (
        cache_protocol
        >> Edge(label="Implements", style="dashed", color=COLORS["abstract"])
        >> memory_impl
    )

    (
        llm_protocol
        >> Edge(label="Implements", style="dashed", color=COLORS["abstract"])
        >> openrouter_impl
    )
    (
        llm_protocol
        >> Edge(label="Implements", style="dashed", color=COLORS["abstract"])
        >> gemini_impl
    )

    # Factory to implementation
    repo_factory >> Edge(label="Creates", color=COLORS["runtime"]) >> sqlite_impl
    repo_factory >> Edge(label="Creates", color=COLORS["runtime"]) >> dynamo_impl

    cache_factory >> Edge(label="Creates", color=COLORS["runtime"]) >> redis_impl
    cache_factory >> Edge(label="Creates", color=COLORS["runtime"]) >> memory_impl

    llm_factory >> Edge(label="Creates", color=COLORS["runtime"]) >> openrouter_impl
    llm_factory >> Edge(label="Creates", color=COLORS["runtime"]) >> gemini_impl

    # Benefits box
    with Cluster("Benefits of Protocol Pattern", graph_attr={"bgcolor": "#fff"}):
        benefits = Document(
            "✓ Loose coupling\n"
            "✓ Easy testing (mock protocols)\n"
            "✓ Runtime selection\n"
            "✓ No circular imports\n"
            "✓ Clear contracts\n"
            "✓ Type safety with mypy"
        )
