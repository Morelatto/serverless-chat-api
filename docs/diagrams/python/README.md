# 📊 Chat API Architecture Diagrams

Comprehensive visual documentation of the Chat API system architecture, organized by domain.

## 📁 Folder Structure

```
diagrams/
├── 🏗️ architecture/     # System structure and data flow
├── 🔄 flows/            # User journeys and sequences
├── 🚀 deployment/       # Deployment and scaling
├── 📊 performance/      # Performance and cost analysis
├── ⚙️ operations/       # Error handling and operations
└── 🔧 shared/          # Shared resources (icons, styles)
```

## 🗺️ Quick Navigation

### [Architecture](./architecture/)
- **System Overview** - High-level component architecture
- **Data Flow** - Clean architecture layers

### [Flows](./flows/)
- **Request Journey** - Complete request lifecycle
- **Authentication Flow** - JWT token management
- **Startup Sequence** - Application initialization

### [Deployment](./deployment/)
- **Deployment Options** - Local/Docker/Lambda configurations
- **Scaling Strategy** - From 1 to ∞ users

### [Performance](./performance/)
- **Caching Impact** - 16x performance improvement
- **Cost Analysis** - 85% cost reduction

### [Operations](./operations/)
- **Error Handling** - Unified error management

## 🚀 Quick Start

### Generate All Diagrams
```bash
python generate_all.py
```

### Generate Category
```bash
cd architecture && python 01_system_overview.py
cd flows && python 02_request_journey.py
```

### View All Diagrams
```bash
# macOS
find . -name "*.png" -exec open {} \;

# Linux
find . -name "*.png" -exec xdg-open {} \;

# Windows
for /r %i in (*.png) do start "" "%i"
```

## 🎯 Key Insights

| Metric | Value | Impact |
|--------|-------|---------|
| **Cache Hit Rate** | 90% | 16x faster responses |
| **P50 Latency** | 17ms (cached) | Excellent UX |
| **Cost Savings** | 85% | $1,710/day saved |
| **Scaling** | ∞ | Serverless auto-scale |
| **Startup Time** | 50ms | Fast deployments |

## 🛠️ Technology Stack

### Core Framework
- **FastAPI** - Modern async Python web framework
- **Pydantic** - Data validation with type hints
- **python-jose** - JWT authentication
- **slowapi** - Rate limiting

### Storage (Environment Adaptive)
| Environment | Database | Cache |
|------------|----------|--------|
| Local | SQLite | Dict (in-memory) |
| Docker | PostgreSQL | Redis |
| Lambda | DynamoDB | ElastiCache |

### External Services
- **LiteLLM** - Multi-provider LLM abstraction
- **Providers** - OpenAI, Anthropic, Google

## 📈 Visual Language

### Line Weights
- **Bold (6-7px)** → Primary path (90% traffic)
- **Normal (2-3px)** → Standard flow
- **Thin (1px)** → Secondary path (10% traffic)
- **Dashed** → Optional/fallback

### Color Semantics
- 🟢 **Green** → Success/optimal
- 🔵 **Blue** → Normal operation
- 🟡 **Orange** → Degraded/warning
- 🔴 **Red** → Error/failure
- ⚫ **Gray** → Infrastructure

### Icons
- Technology-specific icons (FastAPI, Redis, etc.)
- HTTP status code badges
- Semantic indicators (✓ success, ✗ failure)

## 📝 Architecture Principles

1. **Environment Adaptivity** - Same code, different configs
2. **Cache-First** - 90% requests never hit LLM
3. **Type Safety** - Pydantic validation throughout
4. **Stateless Auth** - JWT enables horizontal scaling
5. **Unified Errors** - Consistent error responses

## 🔧 Maintenance

### Adding New Diagrams
1. Create Python file in appropriate folder
2. Import shared resources: `sys.path.append("../shared")`
3. Follow naming convention: `XX_diagram_name.py`
4. Update `generate_all.py` with new diagram
5. Add documentation to folder README

### Updating Icons
Icons are stored in `shared/icons/`:
- Convert SVG to PNG for Graphviz compatibility
- Use 512x512 resolution for clarity
- Follow semantic naming

## 📚 Documentation

Each folder contains a README with:
- Diagram descriptions
- Key insights
- Visual conventions
- Related metrics

## 🤝 Contributing

When adding diagrams:
1. Answer ONE clear question per diagram
2. Use consistent visual language
3. Include relevant metrics
4. Document in folder README

---

*Generated with Python diagrams library using Graphviz*
*Architecture by: Chat API Team*
