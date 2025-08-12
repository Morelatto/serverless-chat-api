#!/usr/bin/env python3
"""Custom icon system for actual project components."""

from pathlib import Path

from diagrams.custom import Custom


def get_icon_path(name: str) -> str:
    """Get the absolute path to an icon file (PNG preferred for compatibility)."""
    # Use absolute path to ensure diagrams can find the icons
    icons_dir = Path(__file__).parent / "icons"

    # Try PNG first (better compatibility with graphviz)
    png_path = icons_dir / f"{name}.png"
    if png_path.exists():
        return str(png_path.absolute())

    # Fall back to SVG
    svg_path = icons_dir / f"{name}.svg"
    if svg_path.exists():
        return str(svg_path.absolute())

    # Check for placeholder
    placeholder_path = icons_dir / f"{name}_placeholder.png"
    if placeholder_path.exists():
        return str(placeholder_path.absolute())

    # Create placeholder if needed
    return create_placeholder_icon(name)


def create_placeholder_icon(name: str, color: str = "#4A5568") -> str:
    """Create a placeholder PNG icon for missing custom icons."""
    from PIL import Image, ImageDraw, ImageFont

    icons_dir = Path(__file__).parent / "icons"
    icons_dir.mkdir(exist_ok=True)

    # Create a 100x100 image
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle
    draw.rounded_rectangle([5, 5, 95, 95], radius=10, fill=color)

    # Add text
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 12
        )
    except OSError:
        font = ImageFont.load_default()

    text = name[:8]
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (100 - text_width) // 2
    text_y = (100 - text_height) // 2
    draw.text((text_x, text_y), text, fill="white", font=font)

    # Save as PNG
    icon_path = icons_dir / f"{name}_placeholder.png"
    img.save(str(icon_path))

    return str(icon_path.absolute())


# Convenience functions for creating Custom nodes with actual downloaded icons
def FastAPI(label: str = "FastAPI") -> Custom:
    """FastAPI framework icon."""
    return Custom(label, get_icon_path("fastapi"))


def JWT(label: str = "JWT") -> Custom:
    """JSON Web Token icon."""
    return Custom(label, get_icon_path("jwt"))


def Jose(label: str = "python-jose") -> Custom:
    """Python-jose library icon."""
    return Custom(label, get_icon_path("jose"))


def Slowapi(label: str = "Rate Limit") -> Custom:
    """Slowapi rate limiting icon."""
    return Custom(label, get_icon_path("slowapi"))


def LiteLLM(label: str = "LiteLLM") -> Custom:
    """LiteLLM abstraction library icon."""
    return Custom(label, get_icon_path("litellm"))


def Tenacity(label: str = "Retry") -> Custom:
    """Tenacity retry logic icon."""
    return Custom(label, get_icon_path("tenacity"))


def Protocol(label: str = "Protocol") -> Custom:
    """Python typing.Protocol icon."""
    return Custom(label, get_icon_path("protocol"))


def Pydantic(label: str = "Validate") -> Custom:
    """Pydantic validation icon."""
    return Custom(label, get_icon_path("pydantic"))


def Loguru(label: str = "Logger") -> Custom:
    """Loguru logging library icon."""
    return Custom(label, get_icon_path("loguru"))


def DictCache(label: str = "Memory") -> Custom:
    """In-memory dict cache icon."""
    return Custom(label, get_icon_path("dict"))


def Handler(label: str = "Handler") -> Custom:
    """Exception handler icon."""
    return Custom(label, get_icon_path("handler"))


def Middleware(label: str = "Middleware") -> Custom:
    """Middleware component icon."""
    return Custom(label, get_icon_path("middleware"))


def get_icon(component: str, label: str | None = None) -> Custom:
    """Get a custom icon for any component by name."""
    # Direct mapping - component name matches icon file name
    return Custom(label or component, get_icon_path(component))


# New specific icon functions for better semantic clarity
def RequestIcon(label: str = "Request") -> Custom:
    """Request/input icon."""
    return Custom(label, get_icon_path("request"))


def ResponseIcon(label: str = "Response") -> Custom:
    """Response/output icon."""
    return Custom(label, get_icon_path("response"))


def CacheHitIcon(label: str = "Hit") -> Custom:
    """Cache hit success icon."""
    return Custom(label, get_icon_path("cache-hit"))


def CacheMissIcon(label: str = "Miss") -> Custom:
    """Cache miss icon."""
    return Custom(label, get_icon_path("cache-miss"))


def StatusCode(code: int, label: str | None = None) -> Custom:
    """HTTP status code badge icon."""
    return Custom(label or str(code), get_icon_path(str(code)))
