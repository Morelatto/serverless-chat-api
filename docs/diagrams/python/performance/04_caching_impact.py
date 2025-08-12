#!/usr/bin/env python3
"""Caching Impact - What's the performance impact?"""

import sys

sys.path.append("../shared")
from custom_icons import CacheHitIcon, CacheMissIcon, DictCache, LiteLLM, RequestIcon, ResponseIcon
from diagram_styles import COLORS
from diagrams import Diagram, Edge

with Diagram(
    "Caching Impact",
    filename="04_caching_impact",
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
    # Request arrives at cache
    request = RequestIcon("Request")
    cache = DictCache("Cache\nCheck")

    # Fast path - cache hit
    hit = CacheHitIcon("HIT")
    cached = ResponseIcon("17ms\n$0.0001")

    # Slow path - cache miss
    miss = CacheMissIcon("MISS")
    llm = LiteLLM("LLM Call\n800ms")
    store = DictCache("Store")
    generated = ResponseIcon("820ms\n$0.002")

    # Response
    response = ResponseIcon("Response")

    # Flow with visual weight showing traffic distribution
    request >> cache

    # 90% hit - very thick green line
    cache >> Edge(label="90%", color=COLORS["success"], penwidth="7") >> hit
    hit >> cached
    cached >> Edge(color=COLORS["success"], penwidth="6") >> response

    # 10% miss - very thin orange line
    cache >> Edge(label="10%", color=COLORS["warning"], penwidth="1", style="dashed") >> miss
    miss >> llm >> store >> generated
    generated >> Edge(color=COLORS["warning"], penwidth="1") >> response
