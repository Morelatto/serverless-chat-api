#!/usr/bin/env python3
"""Authentication Flow - JWT lifecycle with clear separation."""

import sys

sys.path.append("../shared")
from custom_icons import FastAPI, Pydantic, ResponseIcon, get_icon
from diagram_styles import COLORS
from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.client import User

with Diagram(
    "JWT Authentication Lifecycle",
    filename="06_authentication_flow",
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
    # User
    user = User("User")

    with Cluster("🔐 Login Flow", graph_attr={"bgcolor": "#E8F5E9"}):
        login = FastAPI("/login")
        validate = Pydantic("Validate")
        generate = get_icon("jwt", "Create JWT")

    with Cluster("🎫 Token (30min TTL)", graph_attr={"bgcolor": "#FFF3E0"}):
        token = ResponseIcon("JWT Token")

    with Cluster("📡 API Requests", graph_attr={"bgcolor": "#E3F2FD"}):
        request = FastAPI("API Call")
        verify = get_icon("jwt", "Verify JWT")
        process = get_icon("data", "Process")

    # Main login flow - THICK line for main path
    user >> Edge(label="credentials", color=COLORS["api"], penwidth="3") >> login
    login >> validate >> generate
    generate >> Edge(label="JWT", color=COLORS["success"], penwidth="4") >> token

    # API request flow - MEDIUM thickness
    token >> Edge(label="Bearer", color=COLORS["auth"], penwidth="2") >> request
    request >> verify
    verify >> Edge(label="✓", color=COLORS["success"], penwidth="2") >> process

    # Token refresh - THIN line for edge case
    (
        verify
        >> Edge(label="expired", color=COLORS["warning"], penwidth="1", style="dashed")
        >> generate
    )
