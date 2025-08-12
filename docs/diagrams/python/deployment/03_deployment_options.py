#!/usr/bin/env python3
"""Deployment Options - How does it adapt?"""

import sys

sys.path.append("../shared")
from custom_icons import DictCache, FastAPI, get_icon
from diagram_styles import COLORS
from diagrams import Cluster, Diagram, Edge
from diagrams.generic.blank import Blank

with Diagram(
    "Deployment Options",
    filename="03_deployment_options",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "14",
        "bgcolor": "white",
        "pad": "0.5",
        "rankdir": "TB",
        "dpi": "150",
    },
):
    # Same FastAPI code with note
    with Cluster(
        "Same Code, Different Configs", graph_attr={"bgcolor": "#E8F4FD", "style": "rounded,filled"}
    ):
        api = FastAPI("FastAPI Application")

    # Three deployment columns with environment labels
    with Cluster("Development", graph_attr={"bgcolor": "#FFF9E6"}):
        local_server = get_icon("python", "Uvicorn")
        local_db = get_icon("sqlite", "SQLite")
        local_cache = DictCache("Dict")
        local_cost = Blank("$0/mo")
        local_server >> local_db
        local_server >> local_cache

    with Cluster("Staging", graph_attr={"bgcolor": "#E6F3FF"}):
        docker_server = get_icon("docker", "Gunicorn")
        docker_db = get_icon("postgres", "PostgreSQL")
        docker_cache = get_icon("redis", "Redis")
        docker_cost = Blank("$50/mo")
        docker_server >> docker_db
        docker_server >> docker_cache

    with Cluster("Production", graph_attr={"bgcolor": "#FFE6F0"}):
        lambda_server = get_icon("mangum", "Mangum")
        lambda_db = get_icon("dynamodb", "DynamoDB")
        lambda_cache = get_icon("redis", "ElastiCache")
        lambda_cost = Blank("$0.20/1M")
        lambda_server >> lambda_db
        lambda_server >> lambda_cache

    # API deploys to all three
    api >> Edge(label="dev", color=COLORS["info"]) >> local_server
    api >> Edge(label="stage", color=COLORS["info"]) >> docker_server
    api >> Edge(label="prod", color=COLORS["info"]) >> lambda_server
