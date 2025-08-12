#!/usr/bin/env python3
"""Helper functions and constants for consistent diagram styling."""

from diagrams import Edge

# Improved color palette - more professional and accessible
COLORS = {
    # Primary actions
    "primary": "#0066CC",  # Main flow - strong blue
    "success": "#10B981",  # Success path - emerald green
    "error": "#EF4444",  # Error path - clear red
    "warning": "#F59E0B",  # Cache/warning - amber
    "info": "#3B82F6",  # External APIs - bright blue
    "muted": "#6B7280",  # Secondary elements - gray
    # Specific use cases
    "auth": "#7C3AED",  # Authentication - purple
    "cache": "#F59E0B",  # Cache operations - amber
    "database": "#059669",  # Database ops - teal
    "external": "#3B82F6",  # External services - blue
    "validate": "#EC4899",  # Validation - pink
}


# Edge styles for different relationship types
def style_edge(edge_type: str) -> dict:
    """Get consistent edge styling based on type."""
    styles = {
        "main": {"color": COLORS["primary"], "style": "bold", "penwidth": "2.0"},
        "success": {"color": COLORS["success"], "style": "solid"},
        "error": {"color": COLORS["error"], "style": "dotted", "penwidth": "1.5"},
        "cache": {"color": COLORS["cache"], "style": "dashed"},
        "async": {"color": COLORS["muted"], "style": "dashed"},
        "implements": {"color": COLORS["info"], "style": "dashed", "arrowhead": "empty"},
        "depends": {"color": COLORS["auth"], "style": "solid", "arrowhead": "vee"},
    }
    return styles.get(edge_type, {})


def success_edge(label: str = "") -> Edge:
    """Create a success path edge."""
    return Edge(label=label, **style_edge("success"))


def error_edge(label: str = "") -> Edge:
    """Create an error path edge."""
    return Edge(label=label, **style_edge("error"))


def cache_edge(label: str = "") -> Edge:
    """Create a cache-related edge."""
    return Edge(label=label, **style_edge("cache"))


def main_flow_edge(label: str = "") -> Edge:
    """Create a main flow edge."""
    return Edge(label=label, **style_edge("main"))


# Cluster styles for different sections
def cluster_style(cluster_type: str) -> dict:
    """Get consistent cluster styling."""
    styles = {
        "api": {"bgcolor": "#EFF6FF", "style": "rounded", "penwidth": "2"},
        "business": {"bgcolor": "#F0FDF4", "style": "rounded", "penwidth": "1.5"},
        "data": {"bgcolor": "#FEFCE8", "style": "rounded", "penwidth": "1.5"},
        "external": {"bgcolor": "#F3F4F6", "style": "dashed", "penwidth": "1"},
        "error": {"bgcolor": "#FEF2F2", "style": "solid", "penwidth": "2"},
        "security": {"bgcolor": "#FAF5FF", "style": "solid", "penwidth": "2"},
    }
    return styles.get(cluster_type, {"bgcolor": "white"})


# Simplified labels for common components
LABELS = {
    # Auth
    "jwt": "JWT",
    "token": "Token",
    "auth": "Auth",
    # Data
    "cache": "Cache",
    "db": "DB",
    "store": "Store",
    # Processing
    "validate": "Validate",
    "transform": "Transform",
    "process": "Process",
    # Errors - just codes
    "401": "401",
    "400": "400",
    "429": "429",
    "500": "500",
    "503": "503",
}


# Icon helper - returns the best icon for a concept
def get_icon(concept: str):
    """Get the most appropriate icon for a concept."""
    from diagrams.generic.blank import Blank
    from diagrams.generic.compute import Rack
    from diagrams.generic.storage import Storage
    from diagrams.onprem.inmemory import Redis
    from diagrams.onprem.network import Internet
    from diagrams.programming.flowchart import Document

    icons = {
        "sqlite": Storage,  # Better than PostgreSQL for SQLite
        "cache": Redis,
        "memory_cache": Blank,  # Simple for in-memory
        "llm": Internet,  # Better than Sagemaker
        "jwt": Rack,  # For now, until custom icons
        "protocol": Document,
        "error": Document,
    }

    return icons.get(concept, Blank)
