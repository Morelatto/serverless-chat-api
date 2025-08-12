# 🎨 Chat API Architecture Diagrams

This directory contains Python-based architecture diagrams using the `diagrams` library. These diagrams provide comprehensive visual documentation of the Chat API system architecture, data flows, and deployment patterns.

## 📊 Diagram Inventory

### Core Architecture
1. **`01_system_architecture.py`** - High-level component overview showing all layers and their relationships
2. **`08_protocol_patterns.py`** - Protocol/interface pattern implementation demonstrating loose coupling

### Request Processing
3. **`02_request_flow.py`** - Complete request flow with JWT authentication, caching, and error paths
4. **`03_authentication_flow.py`** - Detailed JWT token creation and validation process
5. **`04_data_transformations.py`** - JSON input to response pipeline with Pydantic validation

### Error Handling & Operations
6. **`05_error_handling.py`** - Comprehensive error matrix showing all failure modes and responses
7. **`06_runtime_dependencies.py`** - Startup sequence and dependency initialization graph

### Deployment
8. **`07_deployment_architecture.py`** - Multi-environment deployment (Local, Docker, AWS Lambda)

## 🚀 Quick Start

### Prerequisites
```bash
# Install Python dependencies
pip install diagrams

# Install Graphviz (required for rendering)
# Ubuntu/Debian
sudo apt-get install graphviz

# MacOS
brew install graphviz

# Or download from https://graphviz.org/download/
```

### Generate All Diagrams
```bash
# Generate all diagrams
python generate_all.py

# Generate a specific diagram
python generate_all.py --diagram 01_system_architecture

# Clean generated files
python generate_all.py --clean
```

### Generate Individual Diagrams
```bash
# Run any diagram script directly
python 01_system_architecture.py
python 02_request_flow.py
# etc...
```

## 📋 Diagram Types & Shapes

The diagrams use proper flowchart notation:

| Shape | Meaning | Example |
|-------|---------|---------|
| 🔷 **Diamond** | Decision point | "JWT Valid?", "Cache Hit?" |
| ⬜ **Rectangle** | Process/Action | "Validate Content", "Call LLM" |
| 🔲 **Parallelogram** | Input/Output | "JSON Request", "HTTP Response" |
| 📄 **Document** | Data/Error | "401 Unauthorized", "LLM Response" |
| ⭕ **Circle** | Start/End | "Request Arrives", "Response Sent" |
| 🗄️ **Cylinder** | Database | "SQLite", "DynamoDB" |

## 🎨 Color Coding

- 🟢 **Green** (`#28a745`) - Success paths
- 🔴 **Red** (`#dc3545`) - Error paths
- 🟡 **Yellow** (`#ffc107`) - Cache operations
- 🔵 **Blue** (`#17a2b8`) - External services
- 🟣 **Purple** (`#6f42c1`) - Security/Auth

## 📐 Architecture Decisions

### Why Python Diagrams over PlantUML?

1. **Programmatic Generation** - Version controlled, reviewable code
2. **Rich Icon Library** - AWS, cloud provider, and technology-specific icons
3. **Consistent Styling** - Centralized color schemes and layouts
4. **Better Shapes** - Proper flowchart notation (diamonds, parallelograms)
5. **Clustering** - Logical grouping with visual boundaries

### Diagram Philosophy

- **Separation of Concerns**: Each diagram has a single focus
- **Progressive Disclosure**: Start with high-level, drill down to details
- **Complete Coverage**: All paths shown (success, error, edge cases)
- **Real Implementation**: Diagrams reflect actual code, not idealized design

## 🔄 Updating Diagrams

When code changes affect architecture:

1. Update the relevant Python diagram file
2. Run `python generate_all.py` to regenerate
3. Commit both `.py` and `.png` files
4. Update this README if adding new diagrams

## 📚 Related Documentation

- **Sequence Diagrams**: See `../` for PlantUML sequence diagrams (temporal flow)
- **API Documentation**: See `/docs` for OpenAPI specs
- **Implementation**: See `/chat_api` for actual code

## 🏷️ Key Insights from Diagrams

### From System Architecture (01)
- Clean separation between API, Business Logic, and Data layers
- Protocol pattern enables swapping implementations (SQLite ↔ DynamoDB)
- Multiple deployment targets from same codebase

### From Request Flow (02)
- JWT validation happens BEFORE rate limiting (security first)
- Cache key generation after validation (prevents cache poisoning)
- All error paths lead to structured error responses

### From Authentication (03)
- User ID comes from JWT token, NOT request body
- 30-minute token expiration
- Multiple validation checks (format, signature, expiration, claims)

### From Error Handling (05)
- Comprehensive error coverage (4xx client, 5xx server)
- Retry logic only for transient failures
- Request ID tracking for debugging

### From Deployment (07)
- Same code runs in Local, Docker, and Lambda
- Environment determines storage backend
- External services shared across deployments

## ⚡ Performance Considerations

The diagrams reveal several performance optimizations:
- Caching before expensive LLM calls
- Connection pooling for databases
- Async I/O throughout (aiosqlite, aioboto3)
- Rate limiting at gateway level

## 🔒 Security Highlights

Security features visible in diagrams:
- JWT authentication required for all endpoints
- Input validation and sanitization
- Rate limiting (60 requests/minute)
- Secret management (environment variables, AWS Secrets)

---

Generated with `diagrams` library v0.24.4
