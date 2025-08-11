#!/usr/bin/env python3
"""Generate sequence diagrams showing time-ordered interactions."""

import shutil
import subprocess
from pathlib import Path


def load_sequence_diagrams():
    """Load existing PlantUML sequence diagrams from files."""
    puml_files = [
        "09_happy_path_sequence.puml",
        "10_cache_hit_sequence.puml",
        "11_error_sequence.puml",
        "12_startup_sequence.puml",
    ]

    diagrams = {}
    for filename in puml_files:
        path = Path(filename)
        if path.exists():
            diagrams[path.stem] = path.read_text()
            print(f"✅ Loaded {filename}")
        else:
            print(f"⚠️  Missing {filename}")

    return diagrams


def generate_pngs():
    """Generate PNG files from existing PlantUML diagrams."""
    print("\n📊 Generating PNG images from sequence diagrams...")

    # Check if plantuml is available
    if not shutil.which("plantuml"):
        print("⚠️  PlantUML not found. Install with: brew install plantuml")
        print("   Or download from: https://plantuml.com/download")
        return False

    # Generate PNGs from existing PUML files
    puml_files = [
        "09_happy_path_sequence.puml",
        "10_cache_hit_sequence.puml",
        "11_error_sequence.puml",
        "12_startup_sequence.puml",
    ]

    for puml_file in puml_files:
        path = Path(puml_file)
        if path.exists():
            # Use subprocess with list args (safer)
            result = subprocess.run(  # noqa: S603
                ["plantuml", "-tpng", str(path)],  # noqa: S607 - Safe: path is from known list
                capture_output=True,
                text=True,
                check=False,  # Don't raise on non-zero exit
            )
            if result.returncode == 0:
                print(f"   ✅ Generated {puml_file.replace('.puml', '.png')}")
            else:
                print(f"   ❌ Failed to generate {puml_file}: {result.stderr}")
        else:
            print(f"   ⚠️  Missing {puml_file}")

    return True


if __name__ == "__main__":
    print("🎨 Processing sequence diagrams...")

    # Load existing diagrams from PUML files
    diagrams = load_sequence_diagrams()
    print(f"\n📝 Loaded {len(diagrams)} sequence diagrams")

    # Try to generate PNGs if PlantUML is available
    generate_pngs()
