# How to Render the Component Diagram

## Option 1: PlantUML Online Server (Easiest)
1. Go to http://www.plantuml.com/plantuml/uml/
2. Copy the contents of `docs/component-diagram.puml`
3. Paste into the text area
4. The diagram will render automatically
5. Right-click to save as PNG/SVG

## Option 2: VS Code Extension
1. Install the PlantUML extension in VS Code
2. Open `docs/component-diagram.puml`
3. Press `Alt+D` (or `Option+D` on Mac) to preview
4. Right-click preview to export

## Option 3: Command Line (Local Installation)

### Install PlantUML
```bash
# macOS
brew install plantuml

# Ubuntu/Debian
sudo apt-get install plantuml

# Or download JAR directly
wget https://github.com/plantuml/plantuml/releases/download/v1.2024.7/plantuml-1.2024.7.jar
```

### Generate diagram
```bash
# Generate PNG
plantuml -tpng docs/component-diagram.puml

# Generate SVG (better quality, scalable)
plantuml -tsvg docs/component-diagram.puml

# With custom output name
plantuml -tpng docs/component-diagram.puml -o ../diagrams/

# Using JAR directly
java -jar plantuml.jar -tsvg docs/component-diagram.puml
```

## Option 4: Docker (No Installation Required)
```bash
# Run PlantUML in Docker
docker run --rm -v $(pwd)/docs:/data plantuml/plantuml -tsvg /data/component-diagram.puml

# This creates component-diagram.svg in the docs/ directory
```

## Option 5: Python Script (Automated)
```python
#!/usr/bin/env python3
"""Render PlantUML diagrams using the online server."""

import base64
import zlib
import requests
from pathlib import Path

def encode_plantuml(text):
    """Encode PlantUML text for URL."""
    compressed = zlib.compress(text.encode('utf-8'))
    encoded = base64.b64encode(compressed).decode('ascii')
    # PlantUML URL encoding
    encoded = encoded.translate(str.maketrans('+/', '-_'))
    return encoded.rstrip('=')

def render_diagram(puml_file, output_format='svg'):
    """Render PlantUML diagram using online server."""
    with open(puml_file, 'r') as f:
        diagram_text = f.read()

    encoded = encode_plantuml(diagram_text)
    url = f"http://www.plantuml.com/plantuml/{output_format}/{encoded}"

    response = requests.get(url)
    if response.status_code == 200:
        output_file = puml_file.replace('.puml', f'.{output_format}')
        with open(output_file, 'wb') as f:
            f.write(response.content)
        print(f"Diagram saved to {output_file}")
    else:
        print(f"Error: {response.status_code}")

if __name__ == "__main__":
    render_diagram('docs/component-diagram.puml', 'svg')
    render_diagram('docs/component-diagram.puml', 'png')
```

## Option 6: Makefile Target
Add to your Makefile:
```makefile
.PHONY: diagrams
diagrams: ## Generate all PlantUML diagrams
	@echo "Generating diagrams..."
	@if command -v plantuml >/dev/null 2>&1; then \
		plantuml -tsvg docs/*.puml; \
		echo "✅ Diagrams generated in docs/"; \
	elif command -v docker >/dev/null 2>&1; then \
		docker run --rm -v $(PWD)/docs:/data plantuml/plantuml -tsvg /data/*.puml; \
		echo "✅ Diagrams generated using Docker"; \
	else \
		echo "❌ Please install PlantUML or Docker"; \
		exit 1; \
	fi
```

## Recommended Approach

For quick viewing: **Option 1** (PlantUML Online Server)
For development: **Option 2** (VS Code Extension)
For CI/CD: **Option 4** (Docker) or **Option 5** (Python script)

## Output Formats

- **PNG**: Good for documentation, fixed resolution
- **SVG**: Best quality, scalable, can be styled with CSS
- **PDF**: Good for printing and formal documentation
- **EPS**: For LaTeX documents

## Tips

1. SVG format is recommended for documentation as it's scalable and looks good at any size
2. The online server has a size limit (~8KB encoded), for larger diagrams use local installation
3. VS Code extension provides live preview while editing
4. Docker approach ensures consistency across different environments
