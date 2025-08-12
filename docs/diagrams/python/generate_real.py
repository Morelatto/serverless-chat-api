#!/usr/bin/env python3
"""Generate diagrams that reflect the ACTUAL implementation."""

import subprocess
import sys
from pathlib import Path

# List of REAL implementation diagrams
REAL_DIAGRAMS = [
    "01_system_architecture_real.py",
    "03_authentication_flow_real.py",
    "05_error_handling_real.py",
    "08_protocol_patterns_real.py",
]

# Icon placeholder instructions
ICON_INSTRUCTIONS = """
📌 REPLACE THESE PLACEHOLDER ICONS:
=====================================
The following SVG placeholders were created in ./icons/
Replace them with actual logos/icons:

1. fastapi.svg    → FastAPI official logo (teal)
2. jwt.svg        → JWT.io logo (black/white shield)
3. jose.svg       → python-jose icon (green lock)
4. slowapi.svg    → Rate limit icon (speedometer)
5. litellm.svg    → LiteLLM logo (purple)
6. gemini.svg     → Google Gemini logo (blue)
7. openrouter.svg → OpenRouter logo (green)
8. aiosqlite.svg  → SQLite logo with async badge
9. tenacity.svg   → Retry icon (circular arrows)
10. loguru.svg    → Loguru logo (cyan)
11. pydantic.svg  → Pydantic logo (pink)
12. mangum.svg    → Mangum adapter icon
13. protocol.svg  → Python Protocol icon
14. dict.svg      → Dictionary/hash table icon

Download from:
- FastAPI: https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png
- JWT: https://jwt.io/img/pic_logo.svg
- Pydantic: https://docs.pydantic.dev/logo-white.svg
- LiteLLM: https://github.com/BerriAI/litellm (logo from repo)
- Others: Create simple, clear icons that represent the concept
"""


def main():
    """Generate all REAL implementation diagrams."""
    print("🎯 Generating REAL Implementation Diagrams")
    print("=" * 50)
    print("These diagrams show YOUR ACTUAL code, not generic AWS!")
    print("=" * 50)

    success_count = 0
    failed = []

    for diagram in REAL_DIAGRAMS:
        diagram_path = Path(diagram)
        if not diagram_path.exists():
            print(f"  ❌ {diagram} not found")
            failed.append(diagram)
            continue

        print(f"  Generating {diagram}...", end=" ")
        try:
            subprocess.run(  # noqa: S603
                [sys.executable, diagram],
                capture_output=True,
                text=True,
                check=True,
            )
            png_file = diagram.replace(".py", ".png")
            if Path(png_file).exists():
                size_kb = Path(png_file).stat().st_size / 1024
                print(f"✓ ({size_kb:.1f} KB)")
                success_count += 1
            else:
                print("❌ (PNG not created)")
                failed.append(diagram)
        except subprocess.CalledProcessError as e:
            print(f"❌ (Error: {e.stderr.strip()})")
            failed.append(diagram)

    print("=" * 50)
    print(f"✅ Successfully generated: {success_count}/{len(REAL_DIAGRAMS)} diagrams")

    if failed:
        print(f"❌ Failed diagrams: {', '.join(failed)}")

    print("\n📁 Generated files:")
    for diagram in REAL_DIAGRAMS:
        png_file = diagram.replace(".py", ".png")
        if Path(png_file).exists():
            print(f"  • {png_file}")

    print("\n" + ICON_INSTRUCTIONS)

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
