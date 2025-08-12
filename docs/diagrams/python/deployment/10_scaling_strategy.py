#!/usr/bin/env python3
"""Scaling Strategy - Progressive scaling from local to serverless."""

import sys

sys.path.append("../shared")
from custom_icons import FastAPI, get_icon
from diagram_styles import COLORS
from diagrams import Cluster, Diagram, Edge
from diagrams.generic.blank import Blank

with Diagram(
    "Scaling Journey: 1 → ∞ Users",
    filename="10_scaling_strategy",
    show=False,
    direction="LR",
    graph_attr={
        "fontsize": "16",
        "bgcolor": "white",
        "pad": "0.5",
        "rankdir": "LR",
        "dpi": "150",
    },
):
    # Development
    with Cluster("🏠 LOCAL (Dev)", graph_attr={"bgcolor": "#FFF9E6"}):
        local = FastAPI("1 instance")
        local_info = Blank("1 user\n10 req/s\n$0")
        local >> local_info

    # Staging
    with Cluster("🐳 DOCKER (Stage)", graph_attr={"bgcolor": "#E6F3FF"}):
        docker = get_icon("docker", "3 replicas")
        docker_info = Blank("100 users\n1K req/s\n$50/mo")
        docker >> docker_info

    # Production
    with Cluster("☁️ LAMBDA (Prod)", graph_attr={"bgcolor": "#FFE6F0"}):
        lambda_auto = get_icon("lambda", "Auto-scale")
        lambda_info = Blank("∞ users\n10K+ req/s\n$0.20/1M req")
        lambda_auto >> lambda_info

    # Scaling progression with increasing thickness
    local >> Edge(label="GROW", color=COLORS["info"], penwidth="2") >> docker
    docker >> Edge(label="SCALE", color=COLORS["success"], penwidth="4") >> lambda_auto
