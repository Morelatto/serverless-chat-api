#!/usr/bin/env python3
"""Generate all v3 professional diagrams."""

import subprocess
import sys
from pathlib import Path

# List of v3 diagrams
V3_DIAGRAMS = [
    "03_authentication_flow_v3.py",
    "05_error_handling_v3.py",
    "08_protocol_patterns_v3.py",
]


def main():
    """Generate all v3 diagrams."""
    print("🎨 Generating Professional v3 Diagrams")
    print("=" * 40)

    success_count = 0
    failed = []

    for diagram in V3_DIAGRAMS:
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

    print("=" * 40)
    print(f"✅ Successfully generated: {success_count}/{len(V3_DIAGRAMS)} diagrams")

    if failed:
        print(f"❌ Failed diagrams: {', '.join(failed)}")
        return 1

    print("\n📁 Generated files:")
    for diagram in V3_DIAGRAMS:
        png_file = diagram.replace(".py", ".png")
        if Path(png_file).exists():
            print(f"  • {png_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
