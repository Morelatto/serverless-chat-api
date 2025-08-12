#!/usr/bin/env python3
"""Deployment Architecture - Local, Docker, and Lambda configurations."""

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.network import APIGateway, CloudFront
from diagrams.aws.storage import S3
from diagrams.generic.database import SQL
from diagrams.generic.os import Ubuntu
from diagrams.onprem.client import Client
from diagrams.onprem.compute import Server
from diagrams.onprem.container import Docker
from diagrams.onprem.inmemory import Redis
from diagrams.programming.framework import FastAPI

COLORS = {
    "local": "#28a745",
    "docker": "#2496ed",
    "aws": "#ff9900",
    "network": "#6c757d",
}

with Diagram(
    "Multi-Environment Deployment Architecture",
    filename="07_deployment_architecture",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "12",
        "bgcolor": "white",
        "pad": "0.8",
        "compound": "true",
    },
):
    # Clients
    dev_client = Client("Developer")
    staging_client = Client("QA Team")
    prod_client = Client("End Users")

    # Local Development
    with Cluster("Local Development", graph_attr={"bgcolor": "#e8f5e9"}):
        local_machine = Ubuntu("Dev Machine")

        with Cluster("Python Environment"):
            venv = Server("Virtual Env\n(.venv)")
            local_app = FastAPI("FastAPI\nuvicorn")
            local_sqlite = SQL("SQLite\nFile DB")
            local_cache = Server("In-Memory\nCache")

        with Cluster("Development Tools"):
            hot_reload = Server("Hot Reload\n--reload")
            debugger = Server("Debugger\npdb/ipdb")
            tests = Server("pytest\nUnit Tests")

        local_machine >> venv >> local_app
        local_app >> Edge(color=COLORS["local"]) >> local_sqlite
        local_app >> Edge(color=COLORS["local"]) >> local_cache
        local_app >> hot_reload
        local_app >> debugger
        venv >> tests

    # Docker Deployment
    with Cluster("Docker Container", graph_attr={"bgcolor": "#e6f3ff"}):
        docker_host = Docker("Docker Host")

        with Cluster("Container Stack"):
            docker_app = FastAPI("FastAPI\nContainer")
            docker_sqlite = SQL("SQLite\nVolume")
            docker_redis = Redis("Redis\nContainer")

        with Cluster("Docker Config"):
            dockerfile = Server("Dockerfile\nMulti-stage")
            compose = Server("docker-compose\nOrchestration")
            volumes = Server("Volumes\nPersistence")

        docker_host >> compose >> docker_app
        docker_app >> Edge(color=COLORS["docker"]) >> docker_sqlite
        docker_app >> Edge(color=COLORS["docker"]) >> docker_redis
        dockerfile >> docker_app
        volumes >> docker_sqlite

    # AWS Lambda Deployment
    with Cluster("AWS Production", graph_attr={"bgcolor": "#fff3e0"}):
        with Cluster("API Layer"):
            api_gw = APIGateway("API Gateway\nREST API")
            cloudfront = CloudFront("CloudFront\nCDN")

        with Cluster("Compute Layer"):
            lambda_func = Lambda("Lambda Function\nMangum Handler")
            lambda_layers = Lambda("Lambda Layers\nDependencies")

        with Cluster("Data Layer"):
            dynamodb = Dynamodb("DynamoDB\nChat History")
            s3_logs = S3("S3 Bucket\nLogs")

        with Cluster("Configuration"):
            env_vars = Server("Environment\nVariables")
            iam_role = Server("IAM Role\nPermissions")
            secrets = Server("Secrets Manager\nAPI Keys")

        cloudfront >> api_gw >> lambda_func
        lambda_func >> Edge(color=COLORS["aws"]) >> dynamodb
        lambda_func >> Edge(color=COLORS["aws"]) >> s3_logs
        lambda_layers >> lambda_func
        env_vars >> lambda_func
        iam_role >> lambda_func
        secrets >> lambda_func

    # External Services (shared)
    with Cluster("External Services", graph_attr={"bgcolor": "#f0f0f0"}):
        openrouter = Server("OpenRouter\nAPI")
        gemini = Server("Gemini\nAPI")
        monitoring = Server("CloudWatch\nMonitoring")

    # Client connections
    dev_client >> Edge(label="localhost:8000", color=COLORS["local"]) >> local_app
    staging_client >> Edge(label="docker:8000", color=COLORS["docker"]) >> docker_app
    prod_client >> Edge(label="HTTPS", color=COLORS["aws"]) >> cloudfront

    # External service connections
    local_app >> Edge(style="dashed", label="API calls") >> openrouter
    docker_app >> Edge(style="dashed", label="API calls") >> gemini
    lambda_func >> Edge(style="dashed", label="API calls") >> openrouter
    lambda_func >> Edge(style="dashed", label="Metrics") >> monitoring

    # CI/CD Pipeline hint
    with Cluster("CI/CD Pipeline", graph_attr={"bgcolor": "#ffebee"}):
        github = Server("GitHub\nActions")
        build = Server("Build\n& Test")
        deploy = Server("Deploy\nto AWS")

        github >> build >> deploy >> lambda_func
