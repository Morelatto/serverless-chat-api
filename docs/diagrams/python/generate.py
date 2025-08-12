#!/usr/bin/env python3
"""Generate all architecture diagrams."""

import subprocess
import sys
from pathlib import Path

# List of diagrams showing actual implementation
DIAGRAMS = [
    "01_system_architecture.py",
    "03_authentication_flow.py",
    "05_error_handling.py",
    "08_protocol_patterns.py",
]


def main():
    """Generate all diagrams."""
    print("🚀 Generating architecture diagrams for ACTUAL implementation...")
    print("=" * 60)

    success_count = 0
    for diagram in DIAGRAMS:
        diagram_path = Path(diagram)
        if not diagram_path.exists():
            print(f"❌ {diagram} not found - skipping")
            continue

        print(f"\n📊 Generating {diagram}...")
        try:
            subprocess.run([sys.executable, diagram], capture_output=True, text=True, check=True)  # noqa: S603
            print(f"✅ Generated {diagram.replace('.py', '.png')}")
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to generate {diagram}")
            print(f"   Error: {e.stderr}")

    print("\n" + "=" * 60)
    print(f"✨ Generated {success_count}/{len(DIAGRAMS)} diagrams successfully!")

    if success_count == len(DIAGRAMS):
        print("\n📁 Output files:")
        for diagram in DIAGRAMS:
            png_file = diagram.replace(".py", ".png")
            if Path(png_file).exists():
                print(f"   - {png_file}")

    return 0 if success_count == len(DIAGRAMS) else 1


if __name__ == "__main__":
    sys.exit(main())
