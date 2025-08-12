#!/usr/bin/env python3
"""Cost Analysis - 85% savings through intelligent caching."""

import sys

sys.path.append("../shared")
from custom_icons import DictCache, LiteLLM
from diagram_styles import COLORS
from diagrams import Diagram, Edge
from diagrams.generic.blank import Blank

with Diagram(
    "💰 85% Cost Reduction",
    filename="08_cost_analysis",
    show=False,
    direction="LR",
    graph_attr={
        "fontsize": "18",
        "bgcolor": "white",
        "pad": "0.5",
        "rankdir": "LR",
        "dpi": "150",
    },
):
    # Input
    requests = Blank("1M requests/day")

    # Without cache (top path)
    no_cache = LiteLLM("100% LLM")
    cost_high = Blank("$2,000/day ❌")

    # With cache (bottom path)
    cache = DictCache("90% cached")
    cost_low = Blank("$290/day ✅")

    # Savings
    savings = Blank("💰 Save $1,710/day")

    # Flow - thickness shows cost
    requests >> Edge(label="NO CACHE", color=COLORS["error"], penwidth="7") >> no_cache
    no_cache >> Edge(color=COLORS["error"], penwidth="7") >> cost_high

    requests >> Edge(label="WITH CACHE", color=COLORS["success"], penwidth="2") >> cache
    cache >> Edge(color=COLORS["success"], penwidth="2") >> cost_low

    # Show savings
    cost_high >> Edge(style="dashed", color=COLORS["info"]) >> savings
    cost_low >> Edge(style="dashed", color=COLORS["info"]) >> savings
