#!/usr/bin/env python3
"""Request Journey - Why is it fast?"""

import sys

sys.path.append("../shared")
from custom_icons import DictCache, FastAPI, Jose, LiteLLM, Pydantic, ResponseIcon, Slowapi
from diagram_styles import COLORS
from diagrams import Diagram, Edge
from diagrams.onprem.client import User

with Diagram(
    "Request Journey",
    filename="02_request_journey",
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
    # Request flow
    user = User("User")
    api = FastAPI("API")
    auth = Jose("Auth")  # Use Jose icon for JWT auth
    rate = Slowapi("Rate Limit")
    validate = Pydantic("Validate")  # Use Pydantic for validation
    cache = DictCache("Cache")

    # Cache hit path (dominant)
    hit_return = ResponseIcon("Return\n17ms")  # Use Response icon

    # Cache miss path
    llm = LiteLLM("LLM")
    store = DictCache("Store")
    miss_return = ResponseIcon("Return\n820ms")  # Use Response icon

    # Main pipeline
    user >> Edge(color=COLORS["api"]) >> api
    api >> auth >> rate >> validate >> cache

    # Split at cache - make visual weight difference more dramatic
    cache >> Edge(label="90% HIT", color=COLORS["success"], penwidth="6") >> hit_return
    cache >> Edge(label="10% MISS", color=COLORS["warning"], penwidth="1", style="dashed") >> llm

    # Miss path continues
    llm >> store >> miss_return

    # Both paths return to user
    hit_return >> Edge(color=COLORS["success"], penwidth="5") >> user
    miss_return >> Edge(color=COLORS["warning"], penwidth="1") >> user
