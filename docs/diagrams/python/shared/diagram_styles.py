#!/usr/bin/env python3
"""Minimal styling for diagrams - just what's actually used."""

# Professional color palette - semantic meaning through color
COLORS = {
    # Status colors
    "success": "#22c55e",  # Green - authenticated/valid
    "error": "#ef4444",  # Red - unauthorized/failed
    "warning": "#f59e0b",  # Amber - rate limited/cached
    "info": "#3b82f6",  # Blue - processing/active
    "external": "#8b5cf6",  # Purple - external services
    "muted": "#6b7280",  # Gray - inactive/secondary
    # Semantic colors
    "auth": "#059669",  # Teal - authentication/security
    "cache": "#f59e0b",  # Amber - cached responses
    "database": "#14b8a6",  # Cyan - data storage
    "validate": "#ec4899",  # Pink - validation
    "api": "#6366f1",  # Indigo - API calls
}


def cluster_style(cluster_type: str) -> dict:
    """Get consistent cluster styling."""
    styles = {
        "auth": {"bgcolor": "#f0fdf4", "style": "rounded", "penwidth": "2"},
        "api": {"bgcolor": "#eff6ff", "style": "rounded", "penwidth": "2"},
        "business": {"bgcolor": "#fefce8", "style": "rounded", "penwidth": "1.5"},
        "data": {"bgcolor": "#f0fdfa", "style": "rounded", "penwidth": "1.5"},
        "external": {"bgcolor": "#faf5ff", "style": "dashed", "penwidth": "1"},
        "error": {"bgcolor": "#fef2f2", "style": "solid", "penwidth": "2"},
        "cache": {"bgcolor": "#fffbeb", "style": "rounded", "penwidth": "1.5"},
        "monitor": {"bgcolor": "#f3f4f6", "style": "rounded", "penwidth": "1"},
    }
    return styles.get(cluster_type, {"style": "rounded"})
