#!/usr/bin/env python3
"""Custom icon system for actual project components."""

from pathlib import Path

from diagrams.custom import Custom


def get_icon_path(name: str) -> str:
    """Get the path to an icon file, checking multiple extensions."""
    icons_dir = Path("./icons")

    # Check for different file extensions
    for ext in [".svg", ".png", ".jpg", ".jpeg"]:
        icon_path = icons_dir / f"{name}{ext}"
        if icon_path.exists():
            return str(icon_path)

    # Fallback to placeholder if not found
    return create_placeholder_icon(name)


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
    icon_path = icons_dir / f"{name}_placeholder.svg"
    icon_path.write_text(svg_content)

    return str(icon_path)


# Icon mapping to actual downloaded files
ICON_MAP = {
    # Core Framework (downloaded from Simple Icons)
    "fastapi": "fastapi",  # fastapi.svg
    "python": "python",  # python.svg
    "pydantic": "pydantic",  # pydantic.svg
    "pytest": "pytest",  # pytest.svg
    # Authentication & Security
    "jwt": "jwt",  # jwt.svg (JSON Web Tokens)
    "jose": "jose",  # Using placeholder
    # Rate Limiting (using Flaticon)
    "slowapi": "slowapi",  # slowapi.png (lightning icon)
    # LLM Providers
    "litellm": "litellm",  # litellm.svg (OpenAI logo as placeholder)
    "gemini": "gemini",  # Failed download, will use placeholder
    "openrouter": "openrouter",  # openrouter.svg (OpenAI logo)
    # Storage & Cache
    "aiosqlite": "sqlite",  # sqlite.svg
    "sqlite": "sqlite",  # sqlite.svg
    "dynamodb": "dynamodb",  # dynamodb.svg
    "redis": "redis",  # redis.svg
    "dict": "dict",  # dict.png (brackets icon)
    # AWS Services
    "lambda": "aws",  # aws.svg
    "aws": "aws",  # aws.svg
    # Utilities (using Flaticon)
    "tenacity": "tenacity",  # tenacity.png (retry icon)
    "loguru": "loguru",  # loguru.png (document icon)
    "protocol": "protocol",  # protocol.png (plug icon)
    # Middleware & Handlers
    "middleware": "middleware",  # Using placeholder
    "handler": "handler",  # Using placeholder
    "mangum": "mangum",  # Using placeholder
}


# Convenience functions for creating Custom nodes
def FastAPI(label: str = "FastAPI") -> Custom:
    return Custom(label, get_icon_path(ICON_MAP.get("fastapi", "fastapi")))


def JWT(label: str = "JWT") -> Custom:
    return Custom(label, get_icon_path(ICON_MAP.get("jwt", "jwt")))


def Jose(label: str = "python-jose") -> Custom:
    return Custom(label, get_icon_path(ICON_MAP.get("jose", "jose")))


def Slowapi(label: str = "Rate Limit") -> Custom:
    return Custom(label, get_icon_path(ICON_MAP.get("slowapi", "slowapi")))


def LiteLLM(label: str = "LiteLLM") -> Custom:
    return Custom(label, get_icon_path(ICON_MAP.get("litellm", "litellm")))


def Tenacity(label: str = "Retry") -> Custom:
    return Custom(label, get_icon_path(ICON_MAP.get("tenacity", "tenacity")))


def Protocol(label: str = "Protocol") -> Custom:
    return Custom(label, get_icon_path(ICON_MAP.get("protocol", "protocol")))


def Pydantic(label: str = "Validate") -> Custom:
    return Custom(label, get_icon_path(ICON_MAP.get("pydantic", "pydantic")))


def Loguru(label: str = "Logger") -> Custom:
    return Custom(label, get_icon_path(ICON_MAP.get("loguru", "loguru")))


def DictCache(label: str = "Memory") -> Custom:
    return Custom(label, get_icon_path(ICON_MAP.get("dict", "dict")))


def Handler(label: str = "Handler") -> Custom:
    return Custom(label, get_icon_path(ICON_MAP.get("handler", "handler")))


def Middleware(label: str = "Middleware") -> Custom:
    return Custom(label, get_icon_path(ICON_MAP.get("middleware", "middleware")))


def get_icon(component: str, label: str | None = None) -> Custom:
    """Get a custom icon for any component."""
    icon_name = ICON_MAP.get(component, component)
    return Custom(label or component, get_icon_path(icon_name))
