#!/usr/bin/env python3
"""Generate simple, focused architecture diagrams - each answering ONE question."""

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import LambdaFunction
from diagrams.aws.database import DynamodbTable
from diagrams.aws.network import APIGateway
from diagrams.aws.security import SecretsManager
from diagrams.generic.database import SQL
from diagrams.generic.storage import Storage
from diagrams.onprem.client import Users
from diagrams.onprem.container import Docker
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.network import Internet  # For external APIs
from diagrams.programming.flowchart import (
    Action,  # For processing steps
    Decision,
    Document,
)
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


def create_1_static_structure():
    """Q: What are the main components and their relationships?"""

    with Diagram(
        "1. Static Structure",
        filename="01_static_structure",
        outformat="png",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        show=False,
        direction="TB",
    ):
        # Simple, flat structure - no protocols shown
        client = Users("Client")

        with Cluster("Application"):
            api = FastAPI("API")
            service = Python("Service")

        with Cluster("Storage"):
            database = SQL("Database")
            cache = Storage("Cache")

        with Cluster("External"):
            llm = Internet("LLM API")  # External API service

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
        filename="02_request_flow",
        outformat="png",
        graph_attr={**GRAPH_ATTR, "rankdir": "LR"},
        node_attr=NODE_ATTR,
        show=False,
        direction="LR",
    ):
        # Linear flow - no branching
        req = Users("Request")
        validate = Document("Validate")  # Validation step
        cache = Storage("Cache?")
        llm = Internet("LLM")  # External LLM API
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
        filename="03_deployments",
        outformat="png",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        show=False,
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
        filename="04_data_flow",
        outformat="png",
        graph_attr={**GRAPH_ATTR, "rankdir": "LR"},
        node_attr=NODE_ATTR,
        show=False,
        direction="LR",
    ):
        # Data formats at each stage
        json_in = Document("JSON\nRequest")  # Input document
        python_obj = Action("Python\nDict")  # Processing step
        prompt = Document("LLM\nPrompt")  # Formatted prompt
        completion = Document("LLM\nResponse")  # API response
        db_record = Storage("DB\nRecord")  # Stored data
        json_out = Document("JSON\nResponse")  # Output document

        json_in >> Edge(label="parse") >> python_obj
        python_obj >> Edge(label="format") >> prompt
        prompt >> Edge(label="API call") >> completion
        completion >> Edge(label="+ metadata") >> db_record
        db_record >> Edge(label="serialize") >> json_out


def create_5_error_paths():
    """Q: What happens when things fail?"""

    with Diagram(
        "5. Error Handling",
        filename="05_error_handling",
        outformat="png",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        show=False,
        direction="TB",
    ):
        request = Users("Request")

        with Cluster("Failure Points"):
            validation = Document("Validation\nError")  # Input error
            rate_limit = Decision("Rate Limit\nExceeded")  # Decision point
            llm_fail = Internet("LLM API\nTimeout")  # External failure
            db_fail = SQL("Database\nError")  # Storage failure

        error_response = Document("Error\nResponse")  # Error output

        # All failures lead to error response
        request >> [validation, rate_limit, llm_fail, db_fail]
        [validation, rate_limit, llm_fail, db_fail] >> error_response


def create_6_dependencies():
    """Q: What depends on what at runtime?"""

    with Diagram(
        "6. Runtime Dependencies",
        filename="06_dependencies",
        outformat="png",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        show=False,
        direction="BT",  # Bottom to top for dependencies
    ):
        # Core dependencies
        config = Document("Config")  # Configuration file

        with Cluster("Services"):
            api = FastAPI("API")
            service = Python("Service")

        with Cluster("Resources"):
            db = SQL("Database")
            cache = Storage("Cache")
            llm = Internet("LLM Client")  # External API client

        # Dependencies point upward
        config >> [api, service, db, cache, llm]
        [db, cache, llm] >> service
        service >> api


def create_7_aws_infrastructure():
    """Q: What AWS services are used in production?"""

    with Diagram(
        "7. AWS Infrastructure",
        filename="07_aws_infrastructure",
        outformat="png",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        show=False,
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


def create_8_protocol_abstraction():
    """Q: How do protocols enable flexibility?"""

    with Diagram(
        "8. Protocol Pattern",
        filename="08_protocols",
        outformat="png",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        show=False,
        direction="TB",
    ):
        service = Python("Service")

        with Cluster("Protocol"):
            protocol = Document("Repository\nProtocol")  # Interface definition

        with Cluster("Implementations"):
            sqlite = SQL("SQLite")
            dynamo = DynamodbTable("DynamoDB")

        # Service depends on protocol (uses abstraction)
        service >> Edge(label="uses") >> protocol

        # Protocol defines contract for implementations
        # Using UML-style "realizes" relationship (implementations realize the protocol)
        protocol >> Edge(label="defines", style="dashed") >> sqlite
        protocol >> Edge(label="defines", style="dashed") >> dynamo


if __name__ == "__main__":
    print("🎨 Generating simple, focused diagrams...")
    print("   Each diagram answers ONE question\n")

    diagrams = [
        ("Static Structure", create_1_static_structure, "What are the components?"),
        ("Request Flow", create_2_request_flow, "How does a request flow?"),
        ("Deployments", create_3_deployment_environments, "Where does it run?"),
        ("Data Flow", create_4_data_flow, "How is data transformed?"),
        ("Error Handling", create_5_error_paths, "What happens on failure?"),
        ("Dependencies", create_6_dependencies, "What depends on what?"),
        ("AWS Infrastructure", create_7_aws_infrastructure, "What AWS services?"),
        ("Protocols", create_8_protocol_abstraction, "How do protocols work?"),
    ]

    for name, func, question in diagrams:
        func()
        print(f"✅ {name}: {question}")

    print("\n📊 Simple diagram set complete!")
    print("   - 8 focused diagrams")
    print("   - Each answers ONE question")
    print("   - No overcomplicated visuals")
    print("   - Clear and minimal")
