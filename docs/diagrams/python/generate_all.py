#!/usr/bin/env python3
"""Generate all architecture diagrams in organized folders."""

import os
import subprocess
import sys
from pathlib import Path

# Define diagram categories and their files
DIAGRAM_STRUCTURE = {
    "architecture": {
        "description": "System structure and data flow",
        "diagrams": ["01_system_overview.py", "07_data_flow.py"],
    },
    "flows": {
        "description": "User journeys and temporal sequences",
        "diagrams": [
            "02_request_journey.py",
            "06_authentication_flow.py",
            "09_startup_sequence.py",
        ],
    },
    "deployment": {
        "description": "Deployment options and scaling",
        "diagrams": ["03_deployment_options.py", "10_scaling_strategy.py"],
    },
    "performance": {
        "description": "Performance characteristics and cost analysis",
        "diagrams": ["04_caching_impact.py", "08_cost_analysis.py"],
    },
    "operations": {
        "description": "Error handling and operational aspects",
        "diagrams": ["05_error_handling.py"],
    },
}


def generate_diagrams():
    """Generate all diagrams in their respective folders."""
    root_dir = Path(__file__).parent
    total_generated = 0
    failed = []

    print("🚀 Generating all architecture diagrams...")
    print("=" * 60)

    for category, info in DIAGRAM_STRUCTURE.items():
        category_dir = root_dir / category

        if not category_dir.exists():
            print(f"⚠️  Skipping {category}: directory not found")
            continue

        print(f"\n📁 {category.upper()}: {info['description']}")
        print("-" * 40)

        for diagram_file in info["diagrams"]:
            diagram_path = category_dir / diagram_file

            if not diagram_path.exists():
                print(f"  ❌ {diagram_file} not found")
                failed.append(f"{category}/{diagram_file}")
                continue

            # Change to the diagram's directory to ensure relative paths work
            original_dir = Path.cwd()
            os.chdir(category_dir)

            try:
                # Run the diagram generation
                result = subprocess.run(  # noqa: S603
                    [sys.executable, diagram_file], capture_output=True, text=True, timeout=30
                )

                if result.returncode == 0:
                    # Check if PNG was created
                    png_name = diagram_file.replace(".py", ".png")
                    if (category_dir / png_name).exists():
                        print(f"  ✅ {diagram_file} → {png_name}")
                        total_generated += 1
                    else:
                        print(f"  ⚠️  {diagram_file} ran but no PNG generated")
                        failed.append(f"{category}/{diagram_file}")
                else:
                    print(f"  ❌ {diagram_file} failed: {result.stderr[:100]}")
                    failed.append(f"{category}/{diagram_file}")

            except subprocess.TimeoutExpired:
                print(f"  ⏱️  {diagram_file} timed out")
                failed.append(f"{category}/{diagram_file}")
            except (OSError, ValueError) as e:
                print(f"  ❌ {diagram_file} error: {str(e)[:100]}")
                failed.append(f"{category}/{diagram_file}")
            finally:
                os.chdir(original_dir)

    # Summary
    print("\n" + "=" * 60)
    print("✨ Generation Complete!")
    print(f"   Generated: {total_generated} diagrams")
    print(f"   Failed: {len(failed)} diagrams")

    if failed:
        print("\n❌ Failed diagrams:")
        for diagram in failed:
            print(f"   - {diagram}")

    print("\n📊 View diagrams:")
    print(f"   find {root_dir} -name '*.png' -type f")

    return total_generated, failed


if __name__ == "__main__":
    generate_diagrams()
