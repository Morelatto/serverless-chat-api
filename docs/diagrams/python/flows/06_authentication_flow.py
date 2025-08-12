#!/usr/bin/env python3
"""Authentication Flow - Complete JWT lifecycle."""

import sys

sys.path.append("../shared")
from custom_icons import FastAPI, Jose, RequestIcon, ResponseIcon, get_icon
from diagram_styles import COLORS
from diagrams import Diagram, Edge
from diagrams.onprem.client import User

with Diagram(
    "JWT Authentication Flow",
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
    # Login flow
    user = User("User")
    login = FastAPI("POST\n/login")
    validate_creds = get_icon("lock", "Validate\nCredentials")
    generate = Jose("Generate\nJWT")
    token = ResponseIcon("Token\n30min TTL")

    # Request flow
    request = RequestIcon("API\nRequest")
    check = Jose("Verify\nJWT")
    extract = Jose("Extract\nUser ID")
    proceed = FastAPI("Process\nRequest")

    # Token expiry
    expired = get_icon("clock", "Token\nExpired")
    refresh = Jose("Refresh\nToken")

    # Login sequence
    user >> Edge(label="username/pass", color=COLORS["api"]) >> login
    login >> validate_creds
    validate_creds >> Edge(label="Valid", color=COLORS["success"]) >> generate
    generate >> Edge(label="JWT", color=COLORS["auth"]) >> token
    token >> Edge(color=COLORS["success"], penwidth="2") >> user

    # Request with token
    user >> Edge(label="Bearer token", color=COLORS["auth"], style="dashed") >> request
    request >> check
    check >> Edge(label="Valid", color=COLORS["success"]) >> extract
    extract >> proceed

    # Token refresh flow
    check >> Edge(label="Expired", color=COLORS["warning"]) >> expired
    expired >> refresh
    refresh >> Edge(label="New token", color=COLORS["auth"]) >> token
