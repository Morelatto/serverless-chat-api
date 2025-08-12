#!/usr/bin/env python3
"""Error Handling Matrix - Visual grid instead of text walls."""

from diagram_helpers import COLORS
from diagrams import Cluster, Diagram, Edge
from diagrams.generic.blank import Blank
from diagrams.generic.compute import Rack
from diagrams.programming.flowchart import Decision, Document

with Diagram(
    "Error Handling Matrix (Visual)",
    filename="05_error_handling_v2",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "11",
        "bgcolor": "white",
        "pad": "0.5",
        "rankdir": "TB",
        "nodesep": "0.3",
        "ranksep": "0.5",
    },
):
    # Request entry point
    request = Rack("Request")

    # Error Detection Points (visual icons)
    with Cluster("Detection Points", graph_attr={"bgcolor": "#F9FAFB", "style": "rounded"}):
        detect_points = [
            Decision("🔐"),  # Auth
            Decision("⚡"),  # Rate
            Decision("✓"),  # Validation
            Decision("🌐"),  # LLM
            Decision("💾"),  # Storage
        ]

    # Visual Error Matrix (Grid Layout)
    with Cluster("Error Matrix", graph_attr={"bgcolor": "white", "style": "solid"}):
        # Column headers (error codes)
        with Cluster("Client Errors", graph_attr={"bgcolor": "#FEE2E2", "style": "rounded"}):
            err_400 = Document("400")
            err_401 = Document("401")
            err_429 = Document("429")

        with Cluster("Server Errors", graph_attr={"bgcolor": "#DBEAFE", "style": "rounded"}):
            err_500 = Document("500")
            err_503 = Document("503")

        # Visual connections showing which detection point triggers which error
        # Using different edge styles to show relationships

        # Auth → 401
        detect_points[0] >> Edge(color=COLORS["error"], style="bold") >> err_401

        # Rate → 429
        detect_points[1] >> Edge(color=COLORS["warning"], style="bold") >> err_429

        # Validation → 400
        detect_points[2] >> Edge(color=COLORS["validate"], style="bold") >> err_400

        # LLM → 503
        detect_points[3] >> Edge(color=COLORS["external"], style="bold") >> err_503

        # Storage → 503
        detect_points[4] >> Edge(color=COLORS["database"], style="bold") >> err_503

        # Any → 500 (dotted = rare)
        for point in detect_points:
            point >> Edge(color=COLORS["muted"], style="dotted") >> err_500

    # Response Headers (visual indicators)
    with Cluster("Response Headers", graph_attr={"bgcolor": "#F3F4F6", "style": "rounded"}):
        headers = Blank("📋")

        # Visual header indicators
        header_items = [
            Blank("🆔 X-Request-ID"),
            Blank("🔑 WWW-Auth (401)"),
            Blank("⏰ Retry-After (429)"),
        ]

        headers >> Edge(style="invis") >> header_items[0]
        for i in range(len(header_items) - 1):
            header_items[i] >> Edge(style="invis") >> header_items[i + 1]

    # Retry Logic (visual)
    with Cluster("Retry Strategy", graph_attr={"bgcolor": "#ECFDF5", "style": "rounded"}):
        retry_visual = Rack("🔄 3x")
        retry_details = Document("exp\nbackoff")
        retry_visual >> Edge(style="dashed") >> retry_details

    # Connect flow
    request >> detect_points[0]
    for i in range(len(detect_points) - 1):
        detect_points[i] >> Edge(color=COLORS["success"], label="✓") >> detect_points[i + 1]

    # Server errors get retry
    err_503 >> Edge(color=COLORS["info"], style="dashed") >> retry_visual

    # All errors get headers
    for err in [err_400, err_401, err_429, err_500, err_503]:
        err >> Edge(color=COLORS["muted"], style="dotted") >> headers

    # Minimal legend
    with Cluster("", graph_attr={"bgcolor": "transparent", "style": "invis"}):
        legend = Document("🔐 Auth  ⚡ Rate  ✓ Valid\n" "🌐 LLM   💾 Storage")
