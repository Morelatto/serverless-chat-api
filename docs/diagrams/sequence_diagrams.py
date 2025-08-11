#!/usr/bin/env python3
"""Generate sequence diagrams showing time-ordered interactions."""

from pathlib import Path


def create_sequence_diagrams():
    """Create PlantUML sequence diagrams for key scenarios."""

    diagrams = {
        "09_happy_path_sequence": """
@startuml
!theme plain
skinparam backgroundColor white
skinparam sequenceMessageAlign center

title Happy Path: Successful Chat Request

actor Client
participant "API Gateway" as API
participant "Handler" as Handler
participant "Service" as Service
participant "Cache" as Cache
participant "LLM API" as LLM
database "Database" as DB

Client -> API: POST /chat\\n{user_id, content}
API -> Handler: validate(request)
Handler -> Service: process_message()
Service -> Cache: get(cache_key)
Cache --> Service: None (miss)
Service -> LLM: complete(prompt)
LLM --> Service: response_text
Service -> DB: save(message)
Service -> Cache: set(cache_key, response)
Service --> Handler: {id, content, model}
Handler --> API: 200 OK
API --> Client: JSON response

@enduml
""",
        "10_cache_hit_sequence": """
@startuml
!theme plain
skinparam backgroundColor white

title Cache Hit: Fast Response

actor Client
participant "API" as API
participant "Service" as Service
participant "Cache" as Cache

Client -> API: POST /chat
API -> Service: process_message()
Service -> Cache: get(cache_key)
Cache --> Service: cached_response
Service --> API: {cached: true}
API --> Client: JSON response

note over Cache: Response served\\nfrom cache\\n(no LLM call)

@enduml
""",
        "11_error_sequence": """
@startuml
!theme plain
skinparam backgroundColor white

title Error Handling: LLM Failure with Fallback

actor Client
participant "Service" as Service
participant "Gemini" as Primary
participant "OpenRouter" as Fallback

Client -> Service: process_message()
Service -> Primary: complete(prompt)
Primary --> Service: timeout/error
Service -> Fallback: complete(prompt)
Fallback --> Service: response_text
Service --> Client: 200 OK

note over Primary: Primary provider fails
note over Fallback: Fallback provider succeeds

@enduml
""",
        "12_startup_sequence": """
@startuml
!theme plain
skinparam backgroundColor white

title Application Startup

participant "Main" as Main
participant "Config" as Config
participant "Factory" as Factory
participant "App" as App

Main -> Config: load_settings()
Config --> Main: settings
Main -> Factory: create_repository(settings)
Factory --> Main: repository
Main -> Factory: create_cache(settings)
Factory --> Main: cache
Main -> App: initialize(repository, cache)
App --> Main: ready
Main -> App: start_server()

note over Factory: Creates appropriate\\nimplementations based\\non environment

@enduml
""",
    }

    # Save each diagram
    for filename, content in diagrams.items():
        path = Path(f"{filename}.puml")
        path.write_text(content)
        print(f"✅ Created {filename}.puml")

    return diagrams


def generate_pngs():
    """Generate PNG files from PlantUML diagrams."""
    import shutil
    import subprocess

    print("\n📊 Generating PNG images from sequence diagrams...")

    # Check if plantuml is available
    if not shutil.which("plantuml"):
        print("⚠️  PlantUML not found. Install with: brew install plantuml")
        print("   Or download from: https://plantuml.com/download")
        return False

    # Generate PNGs
    for puml_file in [
        "09_happy_path_sequence.puml",
        "10_cache_hit_sequence.puml",
        "11_error_sequence.puml",
        "12_startup_sequence.puml",
    ]:
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

    return True


if __name__ == "__main__":
    print("🎨 Creating sequence diagrams...")
    create_sequence_diagrams()

    # Try to generate PNGs if PlantUML is available
    generate_pngs()
