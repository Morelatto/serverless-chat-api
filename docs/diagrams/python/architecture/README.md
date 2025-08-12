# 🏗️ Architecture Diagrams

System structure and data flow visualization.

## Diagrams

### 1. System Overview
**File**: `01_system_overview.png`

Shows the high-level architecture with main components:
- Client → FastAPI → Cache/Database/LLM
- Visual emphasis on 90% cache hit rate
- Clean horizontal flow

**Key Insight**: Cache handles 90% of requests, making the system fast and cost-effective.

### 2. Data Flow
**File**: `07_data_flow.png`

Illustrates clean architecture layers:
- Input Layer: JSON → Pydantic models
- Business Layer: Service logic with caching
- External Layer: LLM integration
- Output Layer: Response serialization

**Key Insight**: Type-safe data validation throughout the stack using Pydantic.

## Visual Conventions
- **Line thickness** indicates traffic volume (thick = 90%, thin = 10%)
- **Colors** are semantic (green = success, orange = warning)
- **Layers** show separation of concerns
