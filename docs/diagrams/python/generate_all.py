#!/usr/bin/env python3
"""Generate all architecture diagrams."""

import subprocess
import sys
from pathlib import Path

# Diagram modules to generate
DIAGRAMS = [
    "01_system_architecture",
    "02_request_flow",
    "03_authentication_flow",
    "04_data_transformations",
    "05_error_handling",
    "06_runtime_dependencies",
    "07_deployment_architecture",
    "08_protocol_patterns",
]


def check_dependencies() -> bool:
    """Check if required dependencies are installed."""
    try:
        import diagrams  # noqa: F401

        print("✓ diagrams library installed")
    except ImportError:
        print("✗ diagrams library not found. Install with: pip install diagrams")
        return False

    # Check for graphviz
    result = subprocess.run(["which", "dot"], capture_output=True, text=True)  # noqa: S603, S607
    if result.returncode != 0:
        print("✗ Graphviz not found. Install with:")
        print("  Ubuntu/Debian: sudo apt-get install graphviz")
        print("  MacOS: brew install graphviz")
        print("  Or visit: https://graphviz.org/download/")
        return False
    print("✓ Graphviz installed")

    return True


def generate_diagram(module_name: str) -> bool:
    """Generate a single diagram."""
    try:
        print(f"  Generating {module_name}...", end=" ")

        # Import and execute the module
        module_path = Path(__file__).parent / f"{module_name}.py"

        # Execute the Python file to generate the diagram
        result = subprocess.run(  # noqa: S603
            [sys.executable, str(module_path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )

        if result.returncode != 0:
            print("✗ Error")
            print(f"    {result.stderr}")
            return False

        # Check if output file was created
        output_file = Path(__file__).parent / f"{module_name}.png"
        if output_file.exists():
            size = output_file.stat().st_size / 1024  # Size in KB
            print(f"✓ ({size:.1f} KB)")
            return True
        print("✗ No output file created")
        return False  # noqa: TRY300

    except Exception as e:  # noqa: BLE001
        print(f"✗ Exception: {e}")
        return False


def generate_all() -> None:
    """Generate all diagrams."""
    print("\n🎨 Chat API Diagram Generation")
    print("=" * 40)

    # Check dependencies
    if not check_dependencies():
        print("\n❌ Missing dependencies. Please install required packages.")
        sys.exit(1)

    print("\n📊 Generating diagrams:")
    print("-" * 40)

    success_count = 0
    failed = []

    for diagram in DIAGRAMS:
        if generate_diagram(diagram):
            success_count += 1
        else:
            failed.append(diagram)

    # Summary
    print("\n" + "=" * 40)
    print(f"✅ Successfully generated: {success_count}/{len(DIAGRAMS)} diagrams")

    if failed:
        print(f"❌ Failed diagrams: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("\n🎉 All diagrams generated successfully!")
        print(f"📁 Output directory: {Path(__file__).parent}")

        # List generated files
        print("\n📄 Generated files:")
        for diagram in DIAGRAMS:
            output_file = Path(__file__).parent / f"{diagram}.png"
            if output_file.exists():
                print(f"  • {output_file.name}")


def clean() -> None:
    """Remove all generated diagram files."""
    print("\n🧹 Cleaning generated diagrams...")

    removed = 0
    for diagram in DIAGRAMS:
        png_file = Path(__file__).parent / f"{diagram}.png"
        if png_file.exists():
            png_file.unlink()
            print(f"  ✓ Removed {png_file.name}")
            removed += 1

    print(f"\n✅ Removed {removed} diagram files")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate architecture diagrams")
    parser.add_argument("--clean", action="store_true", help="Remove all generated diagram files")
    parser.add_argument("--diagram", choices=DIAGRAMS, help="Generate a specific diagram only")

    args = parser.parse_args()

    if args.clean:
        clean()
    elif args.diagram:
        if check_dependencies():
            print(f"\n📊 Generating {args.diagram}...")
            if generate_diagram(args.diagram):
                print("✅ Diagram generated successfully!")
            else:
                print("❌ Failed to generate diagram")
                sys.exit(1)
    else:
        generate_all()
