#!/usr/bin/env python3
"""Scaling Strategy - From 1 to infinity users."""

import sys

sys.path.append("../shared")
from custom_icons import FastAPI, get_icon
from diagram_styles import COLORS
from diagrams import Cluster, Diagram, Edge
from diagrams.generic.blank import Blank

with Diagram(
    "Scaling Strategy",
    filename="10_scaling_strategy",
    show=False,
    direction="LR",
    graph_attr={
        "fontsize": "14",
        "bgcolor": "white",
        "pad": "0.5",
        "rankdir": "LR",
        "dpi": "150",
    },
):
    # Local Development
    with Cluster("🏠 LOCAL", graph_attr={"bgcolor": "#FFF9E6"}):
        local_users = get_icon("user", "1 User")
        local_api = FastAPI("1 Instance")
        local_metrics = Blank("10 req/s\n17ms p50\n$0")

        local_users >> Edge(penwidth="1") >> local_api
        local_api >> local_metrics

    # Docker/Kubernetes
    with Cluster("🐳 DOCKER", graph_attr={"bgcolor": "#E6F3FF"}):
        docker_users = get_icon("users", "100 Users")
        docker_lb = get_icon("nginx", "Load\nBalancer")

        with Cluster("Replicas"):
            docker_api1 = FastAPI("API-1")
            docker_api2 = FastAPI("API-2")
            docker_api3 = FastAPI("API-3")

        docker_metrics = Blank("1000 req/s\n15ms p50\n$50/mo")

        docker_users >> Edge(penwidth="2") >> docker_lb
        docker_lb >> docker_api1
        docker_lb >> docker_api2
        docker_lb >> docker_api3
        docker_api2 >> docker_metrics

    # AWS Lambda
    with Cluster("☁️ LAMBDA", graph_attr={"bgcolor": "#FFE6F0"}):
        lambda_users = get_icon("world", "∞ Users")
        lambda_gw = get_icon("aws", "API\nGateway")

        with Cluster("Auto-scaling"):
            lambda_fn1 = get_icon("mangum", "λ")
            lambda_fn2 = get_icon("mangum", "λ")
            lambda_fn3 = get_icon("mangum", "λ")
            lambda_more = Blank("...")

        lambda_metrics = Blank("10K+ req/s\n12ms p50\n$0.20/1M")

        lambda_users >> Edge(penwidth="4") >> lambda_gw
        lambda_gw >> lambda_fn1
        lambda_gw >> lambda_fn2
        lambda_gw >> lambda_fn3
        lambda_gw >> lambda_more
        lambda_fn2 >> lambda_metrics

    # Scaling path
    (
        local_metrics
        >> Edge(label="Scale up", color=COLORS["info"], style="dashed", penwidth="2")
        >> docker_lb
    )
    (
        docker_metrics
        >> Edge(label="Scale out", color=COLORS["info"], style="dashed", penwidth="2")
        >> lambda_gw
    )
