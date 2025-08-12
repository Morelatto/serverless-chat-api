#!/usr/bin/env python3
"""JWT Authentication Flow - Visual, minimal text version."""

from diagram_helpers import COLORS, error_edge, success_edge
from diagrams import Cluster, Diagram, Edge
from diagrams.generic.compute import Rack
from diagrams.onprem.client import User
from diagrams.programming.flowchart import (
    Decision,
    Document,
    InputOutput,
    StartEnd,
)

with Diagram(
    "JWT Authentication Flow (Simplified)",
    filename="03_authentication_flow_v2",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "11",
        "bgcolor": "white",
        "pad": "0.3",
        "nodesep": "0.4",
        "ranksep": "0.8",
    },
):
    # Visual JWT Token Structure (minimal text)
    with Cluster("JWT Structure", graph_attr={"bgcolor": "#F0F9FF", "style": "rounded"}):
        jwt_visual = Rack("🔐 JWT Token")
        with Cluster("", graph_attr={"bgcolor": "transparent", "penwidth": "0"}):
            header = Document("HS256")
            payload = Document("user_id\n30min")
            signature = Document("HMAC")
        jwt_visual >> Edge(style="invis") >> header
        header >> Edge(style="invis") >> payload >> Edge(style="invis") >> signature

    # Login Flow (Token Creation)
    with Cluster("① Login", graph_attr={"bgcolor": "#DCFCE7"}):
        user = User("User")
        login = InputOutput("/login")
        create = Rack("Create")
        token_out = InputOutput("🎫")

        user >> login >> create >> token_out
        create >> Edge(color=COLORS["auth"], style="dashed") >> jwt_visual

    # Request Flow (Token Validation)
    with Cluster("② API Request", graph_attr={"bgcolor": "#FEF3C7"}):
        request = InputOutput("Request\n+ 🎫")

        # Decision chain with icons only
        checks = [
            Decision("🎫?"),  # Has token?
            Decision("Bearer?"),  # Is Bearer?
            Decision("✓?"),  # Valid signature?
            Decision("⏰?"),  # Not expired?
            Decision("👤?"),  # Has user_id?
        ]

        # Success path
        success = StartEnd("✅")

        # Error codes only (no text)
        errors = [
            Document("401"),
            Document("401"),
            Document("401"),
            Document("401"),
            Document("401"),
        ]

    # Connect validation chain
    request >> checks[0]
    for i in range(len(checks)):
        if i < len(checks) - 1:
            checks[i] >> success_edge("✓") >> checks[i + 1]
        else:
            checks[i] >> success_edge("✓") >> success
        checks[i] >> error_edge("✗") >> errors[i]

    # Visual legend (small, corner)
    with Cluster("", graph_attr={"bgcolor": "transparent", "style": "invis"}):
        legend = Document("🎫 = Bearer Token\n⏰ = 30min TTL\n👤 = user_id")

    # Usage Example (minimal)
    with Cluster("③ Protected Endpoint", graph_attr={"bgcolor": "#E0E7FF"}):
        endpoint = Document("@app.post('/chat')\nuser_id: Depends()")
        success >> Edge(color=COLORS["success"]) >> endpoint
