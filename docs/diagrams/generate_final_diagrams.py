#!/usr/bin/env python3
"""Generate final architecture diagrams with custom icons and proper flowchart shapes."""

from pathlib import Path
from urllib.request import urlretrieve

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import LambdaFunction
from diagrams.aws.database import DynamodbTable
from diagrams.aws.network import APIGateway
from diagrams.aws.security import SecretsManager
from diagrams.custom import Custom
from diagrams.generic.database import SQL
from diagrams.generic.storage import Storage
from diagrams.onprem.client import Users
from diagrams.onprem.container import Docker
from diagrams.onprem.inmemory import Redis
from diagrams.programming.flowchart import Action, Decision, Document, InputOutput, Preparation
from diagrams.programming.framework import FastAPI
from diagrams.programming.language import Python

# Minimal, consistent styling
GRAPH_ATTR = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.5",
    "nodesep": "0.8",
    "ranksep": "1.0",
    "splines": "ortho",
}

NODE_ATTR = {
    "fontsize": "11",
    "shape": "box",
    "style": "rounded,filled",
    "fillcolor": "#f9f9f9",
    "height": "0.6",
}


def download_icons():
    """Download custom icons for better diagram representation."""
    icons_dir = Path("../icons")
    icons_dir.mkdir(exist_ok=True)

    # Free icons from Flaticon (remember to attribute in production)
    icon_urls = {
        "validate.png": "https://cdn-icons-png.flaticon.com/512/1828/1828640.png",  # Checkmark
        "config.png": "https://cdn-icons-png.flaticon.com/512/2099/2099058.png",  # Gear
        "error.png": "https://cdn-icons-png.flaticon.com/512/564/564619.png",  # Warning
        "api.png": "https://cdn-icons-png.flaticon.com/512/1493/1493169.png",  # API/Cloud
        "cache.png": "https://cdn-icons-png.flaticon.com/512/2285/2285636.png",  # Cache/Memory
    }

    for filename, url in icon_urls.items():
        icon_path = icons_dir / filename
        if not icon_path.exists():
            try:
                urlretrieve(url, str(icon_path))  # noqa: S310
                print(f"✅ Downloaded: {filename}")
            except (OSError, ValueError, TimeoutError) as e:
                print(f"⚠️  Could not download {filename}: {e}")
                # Create a placeholder file so the Custom() calls don't fail
                icon_path.write_text("placeholder")
        else:
            print(f"✅ Found existing: {filename}")


def create_1_static_structure():
    """Q: What are the main components and their relationships?"""

    with Diagram(
        "1. Static Structure",
        show=False,  # Remove filename to avoid custom icon issues
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        direction="TB",
    ):
        # Simple, flat structure
        client = Users("Client")

        with Cluster("Application"):
            api = FastAPI("API")
            service = Python("Service")

        with Cluster("Storage"):
            database = SQL("Database")
            cache = Storage("Cache")

        with Cluster("External"):
            llm = Custom("LLM API", "../icons/api.png")  # Custom API icon

        # Simple relationships
        client >> api
        api >> service
        service >> database
        service >> cache
        service >> llm


def create_2_request_flow():
    """Q: How does a single request flow through the system?"""

    with Diagram(
        "2. Request Flow",
        show=False,
        graph_attr={**GRAPH_ATTR, "rankdir": "LR"},
        node_attr=NODE_ATTR,
        direction="LR",
    ):
        # Linear flow with custom icons
        req = Users("Request")
        validate = Custom("Validate", "../icons/validate.png")  # Custom checkmark
        cache = Custom("Cache", "../icons/cache.png")  # Custom cache icon
        llm = Custom("LLM", "../icons/api.png")  # Custom API icon
        save = SQL("Save")
        resp = Users("Response")

        # Main path only
        req >> Edge(label="POST /chat") >> validate
        validate >> Edge(label="valid") >> cache
        cache >> Edge(label="miss") >> llm
        llm >> Edge(label="text") >> save
        save >> resp


def create_3_deployment_environments():
    """Q: How is the system deployed in different environments?"""

    with Diagram(
        "3. Deployment Environments",
        show=False,
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        direction="TB",
    ):
        with Cluster("Local"):
            local_app = Python("Python")
            local_db = SQL("SQLite")

        with Cluster("Docker"):
            docker = Docker("Container")
            docker_db = SQL("SQLite")

        with Cluster("AWS"):
            lambda_fn = LambdaFunction("Lambda")
            dynamo = DynamodbTable("DynamoDB")

        # No connections - just showing options
        local_app - local_db
        docker - docker_db
        lambda_fn - dynamo


def create_4_data_flow():
    """Q: How does data transform through the system?"""

    with Diagram(
        "4. Data Transformations",
        show=False,
        graph_attr={**GRAPH_ATTR, "rankdir": "LR"},
        node_attr=NODE_ATTR,
        direction="LR",
    ):
        # Proper flowchart shapes for data vs operations
        json_in = InputOutput("JSON\nRequest")  # Data format
        parse = Action("Parse")  # Operation
        python_obj = InputOutput("Python\nDict")  # Data format
        format_op = Action("Format")  # Operation
        prompt = InputOutput("LLM\nPrompt")  # Data format
        llm_call = Action("LLM Call")  # Operation
        completion = InputOutput("LLM\nResponse")  # Data format
        add_meta = Action("Add Metadata")  # Operation
        db_record = InputOutput("DB\nRecord")  # Data format
        serialize = Action("Serialize")  # Operation
        json_out = InputOutput("JSON\nResponse")  # Data format

        # Clear data transformation flow
        json_in >> parse >> python_obj >> format_op >> prompt
        prompt >> llm_call >> completion >> add_meta >> db_record
        db_record >> serialize >> json_out


def create_5_error_handling():
    """Q: What happens when things fail?"""

    with Diagram(
        "5. Error Handling",
        show=False,
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        direction="TB",
    ):
        request = Users("Request")

        with Cluster("Failure Points"):
            validation = Custom("Validation\nError", "../icons/error.png")  # Custom error icon
            rate_limit = Decision("Rate Limit\nExceeded")  # Decision diamond
            llm_fail = Custom("LLM API\nTimeout", "../icons/error.png")  # Custom error icon
            db_fail = Preparation("Database\nError")  # Preparation hexagon

        error_response = Document("Error\nResponse")

        # All failures lead to error response
        request >> [validation, rate_limit, llm_fail, db_fail]
        [validation, rate_limit, llm_fail, db_fail] >> error_response


def create_6_dependencies():
    """Q: What depends on what at runtime?"""

    with Diagram(
        "6. Runtime Dependencies",
        show=False,
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        direction="BT",  # Bottom to top for dependencies
    ):
        # Core dependencies
        config = Custom("Config", "../icons/config.png")  # Custom gear icon

        with Cluster("Services"):
            api = FastAPI("API")
            service = Python("Service")

        with Cluster("Resources"):
            db = SQL("Database")
            cache = Storage("Cache")
            llm = Custom("LLM Client", "../icons/api.png")  # Custom API icon

        # Dependencies point upward
        config >> [api, service, db, cache, llm]
        [db, cache, llm] >> service
        service >> api


def create_7_aws_infrastructure():
    """Q: What AWS services are used in production?"""

    with Diagram(
        "7. AWS Infrastructure",
        show=False,
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        direction="TB",
    ):
        gateway = APIGateway("API Gateway")
        lambda_fn = LambdaFunction("Lambda")
        dynamodb = DynamodbTable("DynamoDB")
        redis = Redis("ElastiCache")
        secrets = SecretsManager("Secrets")

        # Simple connections
        gateway >> lambda_fn
        lambda_fn >> [dynamodb, redis, secrets]


def create_8_protocol_pattern():
    """Q: How do protocols enable flexibility?"""

    with Diagram(
        "8. Protocol Pattern",
        show=False,
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        direction="TB",
    ):
        service = Python("Service")

        with Cluster("Protocol"):
            protocol = Document("Repository\nProtocol")

        with Cluster("Implementations"):
            sqlite = SQL("SQLite")
            dynamo = DynamodbTable("DynamoDB")

        # Service uses protocol
        service >> Edge(label="uses") >> protocol

        # Implementations implement protocol (correct direction)
        sqlite >> Edge(label="implements", style="dashed") >> protocol
        dynamo >> Edge(label="implements", style="dashed") >> protocol


if __name__ == "__main__":
    print("🎨 Generating final diagrams with custom icons...")

    # Download icons first
    download_icons()

    print("\n📊 Generating diagrams...")
    diagrams = [
        ("Static Structure", create_1_static_structure),
        ("Request Flow", create_2_request_flow),
        ("Deployments", create_3_deployment_environments),
        ("Data Flow", create_4_data_flow),
        ("Error Handling", create_5_error_handling),
        ("Dependencies", create_6_dependencies),
        ("AWS Infrastructure", create_7_aws_infrastructure),
        ("Protocols", create_8_protocol_pattern),
    ]

    for name, func in diagrams:
        try:
            func()
            print(f"✅ Generated: {name}")
        except (OSError, ValueError, ImportError) as e:
            print(f"❌ Failed to generate {name}: {e}")

    print("\n📊 Final diagram set complete!")
    print("   - 8 focused diagrams")
    print("   - Custom icons for key concepts")
    print("   - Proper flowchart shapes")
    print("   - Professional presentation")
