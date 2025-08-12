#!/usr/bin/env python3
"""Custom icon system for actual project components."""

from pathlib import Path

from diagrams import Node


def create_placeholder_icon(name: str, color: str = "#4A5568") -> str:
    """Create a placeholder SVG icon for missing custom icons."""
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
    <rect width="100" height="100" fill="{color}" rx="10"/>
    <text x="50" y="55" text-anchor="middle" fill="white" font-family="Arial" font-size="12" font-weight="bold">
        {name[:8]}
    </text>
</svg>"""

    # Create icons directory if it doesn't exist
    icons_dir = Path("./icons")
    icons_dir.mkdir(exist_ok=True)

    # Save placeholder
    icon_path = icons_dir / f"{name.lower().replace(' ', '_')}.svg"
    icon_path.write_text(svg_content)

    return str(icon_path)


class ProjectIcon(Node):
    """Custom icon for project components."""

    def __init__(self, label: str, icon_path: str | None = None, **kwargs):
        if icon_path and Path(icon_path).exists():
            super().__init__(label, image=icon_path, **kwargs)
        else:
            # Create placeholder if icon doesn't exist
            placeholder = create_placeholder_icon(label.split("\n")[0])
            super().__init__(label, image=placeholder, **kwargs)


# Define project-specific icons with proper colors
ICON_REGISTRY = {
    # Core Framework
    "fastapi": {"color": "#009688", "label": "FastAPI"},
    "mangum": {"color": "#FF6B6B", "label": "Mangum"},
    "pydantic": {"color": "#E92063", "label": "Pydantic"},
    # Authentication & Security
    "jwt": {"color": "#000000", "label": "JWT"},
    "jose": {"color": "#2E7D32", "label": "jose"},
    "slowapi": {"color": "#FF9800", "label": "Slowapi"},
    # LLM Providers
    "litellm": {"color": "#7C3AED", "label": "LiteLLM"},
    "gemini": {"color": "#4285F4", "label": "Gemini"},
    "openrouter": {"color": "#10B981", "label": "OpenRouter"},
    # Storage & Cache
    "aiosqlite": {"color": "#003B57", "label": "aiosqlite"},
    "dynamodb": {"color": "#FF9900", "label": "DynamoDB"},
    "protocol": {"color": "#3776AB", "label": "Protocol"},
    "dict": {"color": "#4B5563", "label": "Dict"},
    "redis": {"color": "#DC382D", "label": "Redis"},
    # Utilities
    "tenacity": {"color": "#F59E0B", "label": "Tenacity"},
    "loguru": {"color": "#00ACC1", "label": "Loguru"},
    "pytest": {"color": "#0A9EDC", "label": "pytest"},
    # Middleware & Handlers
    "middleware": {"color": "#6366F1", "label": "Middleware"},
    "handler": {"color": "#EF4444", "label": "Handler"},
    "endpoint": {"color": "#059669", "label": "Endpoint"},
    # Generic
    "user": {"color": "#1F2937", "label": "User"},
    "request": {"color": "#3B82F6", "label": "Request"},
    "response": {"color": "#10B981", "label": "Response"},
}


def get_icon(component: str, label: str | None = None) -> ProjectIcon:
    """Get a project icon with automatic placeholder generation."""
    config = ICON_REGISTRY.get(component, {"color": "#6B7280", "label": component})

    # Check if actual icon exists
    icon_path = f"./icons/{component}.png"
    if not Path(icon_path).exists():
        icon_path = f"./icons/{component}.svg"
        if not Path(icon_path).exists():
            # Create placeholder
            icon_path = create_placeholder_icon(config["label"], config["color"])

    return ProjectIcon(label or config["label"], icon_path)


# Convenience functions for common components
def FastAPI(label: str = "FastAPI") -> ProjectIcon:
    return get_icon("fastapi", label)


def JWT(label: str = "JWT") -> ProjectIcon:
    return get_icon("jwt", label)


def Jose(label: str = "python-jose") -> ProjectIcon:
    return get_icon("jose", label)


def Slowapi(label: str = "Rate Limit") -> ProjectIcon:
    return get_icon("slowapi", label)


def LiteLLM(label: str = "LiteLLM") -> ProjectIcon:
    return get_icon("litellm", label)


def Tenacity(label: str = "Retry") -> ProjectIcon:
    return get_icon("tenacity", label)


def Protocol(label: str = "Protocol") -> ProjectIcon:
    return get_icon("protocol", label)


def Pydantic(label: str = "Validate") -> ProjectIcon:
    return get_icon("pydantic", label)


def Loguru(label: str = "Logger") -> ProjectIcon:
    return get_icon("loguru", label)


def DictCache(label: str = "Memory") -> ProjectIcon:
    return get_icon("dict", label)


def Handler(label: str = "Handler") -> ProjectIcon:
    return get_icon("handler", label)


def Middleware(label: str = "Middleware") -> ProjectIcon:
    return get_icon("middleware", label)
