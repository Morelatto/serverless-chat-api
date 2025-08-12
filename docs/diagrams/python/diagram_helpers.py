#!/usr/bin/env python3
"""Helper functions and constants for consistent diagram styling."""

from diagrams import Edge

# Professional color palette - no emojis, semantic meaning through color
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


def get_semantic_icon(concept: str):
    """Get the most semantically appropriate icon for a concept."""
    from diagrams.aws.analytics import DataPipeline
    from diagrams.aws.compute import Lambda
    from diagrams.aws.database import Dynamodb, ElastiCache
    from diagrams.aws.integration import SimpleQueueServiceSqs as SQS
    from diagrams.aws.management import Cloudwatch, SystemsManager
    from diagrams.aws.ml import Sagemaker
    from diagrams.aws.network import ElasticLoadBalancing
    from diagrams.aws.security import (
        CertificateManager,
        SecretsManager,
        Shield,
    )
    from diagrams.aws.security import (
        IdentityAndAccessManagementIam as IAM,
    )
    from diagrams.aws.storage import SimpleStorageServiceS3Bucket
    from diagrams.generic.database import SQL
    from diagrams.generic.device import Mobile
    from diagrams.onprem.analytics import Spark
    from diagrams.onprem.ci import Jenkins
    from diagrams.onprem.client import User
    from diagrams.onprem.compute import Server
    from diagrams.onprem.container import Docker
    from diagrams.onprem.inmemory import Redis
    from diagrams.onprem.monitoring import Grafana, Prometheus
    from diagrams.onprem.network import Nginx
    from diagrams.onprem.security import Trivy, Vault
    from diagrams.programming.framework import FastAPI
    from diagrams.programming.language import Bash, Python

    icons = {
        # Authentication & Security
        "jwt": CertificateManager,  # Certificate/token management
        "auth": IAM,  # Authentication
        "auth_check": Shield,  # Auth validation
        "secret": SecretsManager,  # Secret storage
        "security": Trivy,  # Security scanning
        "vault": Vault,  # Secure storage
        # Rate Limiting & Load Balancing
        "rate_limit": ElasticLoadBalancing,  # Rate limiting
        "throttle": Nginx,  # Request throttling
        # Validation & Processing
        "validate": SystemsManager,  # System validation
        "transform": DataPipeline,  # Data transformation
        "process": Lambda,  # Processing function
        # Monitoring & Metrics
        "monitor": Prometheus,  # Monitoring
        "metrics": Cloudwatch,  # Metrics collection
        "dashboard": Grafana,  # Dashboards
        # Storage & Caching
        "cache": ElastiCache,  # Cache service
        "redis": Redis,  # Redis cache
        "memory_cache": Spark,  # In-memory processing
        "database": SQL,  # Database
        "dynamodb": Dynamodb,  # DynamoDB
        "storage": SimpleStorageServiceS3Bucket,  # Storage
        # Services & APIs
        "api": FastAPI,  # API service
        "service": Server,  # Generic service
        "llm": Sagemaker,  # ML/LLM service
        "queue": SQS,  # Message queue
        # Languages & Protocols
        "python": Python,  # Python code
        "bash": Bash,  # Scripts/protocols
        "protocol": Jenkins,  # CI/protocol pattern
        # Client & User
        "user": User,  # User/client
        "client": Mobile,  # Client device
        # Containers
        "docker": Docker,  # Docker container
        "container": Docker,  # Generic container
    }

    return icons.get(concept, Server)  # Default to Server if not found


# Edge styles for different relationship types
def style_edge(edge_type: str) -> dict:
    """Get consistent edge styling based on type."""
    styles = {
        "success": {"color": COLORS["success"], "style": "solid", "penwidth": "2.0"},
        "error": {"color": COLORS["error"], "style": "solid", "penwidth": "2.0"},
        "warning": {"color": COLORS["warning"], "style": "dashed", "penwidth": "1.5"},
        "cache": {"color": COLORS["cache"], "style": "dashed", "penwidth": "1.5"},
        "auth": {"color": COLORS["auth"], "style": "solid", "penwidth": "2.0"},
        "api": {"color": COLORS["api"], "style": "solid", "penwidth": "1.5"},
        "async": {"color": COLORS["muted"], "style": "dashed", "penwidth": "1.0"},
        "implements": {"color": COLORS["info"], "style": "dashed", "arrowhead": "empty"},
        "depends": {"color": COLORS["external"], "style": "solid", "arrowhead": "vee"},
    }
    return styles.get(edge_type, {"color": COLORS["muted"]})


def success_edge(label: str = "") -> Edge:
    """Create a success path edge (green, solid)."""
    return Edge(label=label, **style_edge("success"))


def error_edge(label: str = "") -> Edge:
    """Create an error path edge (red, solid)."""
    return Edge(label=label, **style_edge("error"))


def warning_edge(label: str = "") -> Edge:
    """Create a warning/rate limit edge (amber, dashed)."""
    return Edge(label=label, **style_edge("warning"))


def auth_edge(label: str = "") -> Edge:
    """Create an authentication edge (teal, solid)."""
    return Edge(label=label, **style_edge("auth"))


def cache_edge(label: str = "") -> Edge:
    """Create a cache-related edge (amber, dashed)."""
    return Edge(label=label, **style_edge("cache"))


def api_edge(label: str = "") -> Edge:
    """Create an API call edge (indigo, solid)."""
    return Edge(label=label, **style_edge("api"))


# Cluster styles for different sections
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
    return styles.get(cluster_type, {"bgcolor": "white", "style": "rounded"})
