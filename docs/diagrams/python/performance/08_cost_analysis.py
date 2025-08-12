#!/usr/bin/env python3
"""Cost Analysis - Business value of caching."""

import sys

sys.path.append("../shared")
from custom_icons import DictCache, LiteLLM, get_icon
from diagram_styles import COLORS
from diagrams import Cluster, Diagram, Edge
from diagrams.generic.blank import Blank

with Diagram(
    "Cost Analysis: 85% Savings",
    filename="08_cost_analysis",
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
    # Daily traffic
    with Cluster("1 Million Requests/Day", graph_attr={"bgcolor": "#F0F0F0"}):
        requests = get_icon("input", "1M Daily\nRequests")

    # Without cache scenario
    with Cluster("WITHOUT CACHE ❌", graph_attr={"bgcolor": "#FFEBEE"}):
        all_llm = LiteLLM("100%\nto LLM")
        cost_nocache = get_icon("money", "$2,000\nper day")
        time_nocache = get_icon("slow", "800ms\naverage")

        all_llm >> cost_nocache
        all_llm >> time_nocache

    # With cache scenario
    with Cluster("WITH CACHE ✅", graph_attr={"bgcolor": "#E8F5E9"}):
        cache_split = DictCache("90% Hit\n10% Miss")

        with Cluster("Cache Hits", graph_attr={"bgcolor": "#F1F8E9"}):
            hits = get_icon("cache-hit", "900K\nHits")
            cost_hits = get_icon("money", "$90")
            time_hits = get_icon("fast", "17ms")

        with Cluster("Cache Misses", graph_attr={"bgcolor": "#FFF9E6"}):
            misses = get_icon("cache-miss", "100K\nMisses")
            cost_misses = get_icon("money", "$200")
            time_misses = get_icon("slow", "820ms")

        cache_split >> Edge(label="90%", color=COLORS["success"], penwidth="5") >> hits
        cache_split >> Edge(label="10%", color=COLORS["warning"], penwidth="1") >> misses
        hits >> cost_hits
        hits >> time_hits
        misses >> cost_misses
        misses >> time_misses

    # Savings calculation
    with Cluster(
        "💰 SAVINGS", graph_attr={"bgcolor": "#E1F5FE", "style": "rounded,filled", "penwidth": "2"}
    ):
        total = Blank("Total: $290/day\nSavings: $1,710/day\n85% Cost Reduction")

    # Flow
    requests >> Edge(label="No cache", color=COLORS["error"], penwidth="2") >> all_llm
    requests >> Edge(label="With cache", color=COLORS["success"], penwidth="4") >> cache_split

    cost_nocache >> Edge(color=COLORS["error"], style="dashed") >> total
    cost_hits >> Edge(color=COLORS["success"], style="dashed") >> total
    cost_misses >> Edge(color=COLORS["warning"], style="dashed") >> total
