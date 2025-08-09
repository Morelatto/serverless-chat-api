# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Package Management (using uv)
- `uv sync --dev` - Install all dependencies including dev tools
- `uv run python -m chat_api` - Run the application locally
- `uv pip install -e .` - Install package in editable mode

### Testing
- `uv run python -m pytest tests/ -v` - Run all tests with verbose output
- `uv run python -m pytest tests/test_handlers.py::test_chat_endpoint -v` - Run specific test
- `uv run python -m pytest tests/ -s` - Show print statements during tests
- `uv run python -m pytest tests/ --cov=chat_api --cov-report=term-missing` - Run with coverage report

### Code Quality
- `ruff check . --fix` - Lint and auto-fix code issues
- `ruff format .` - Format code (replaces Black)
- `mypy chat_api/` - Type checking
- `bandit -r chat_api/ --skip B101` - Security scanning
- `uv run python -m pytest tests/ --cov=chat_api --cov-report=term-missing` - Run tests with coverage

#### Manual Pre-commit Checks (Environment Issue Workaround)
Due to pre-commit environment installation issues, run these commands manually:
```bash
# Format and lint
uv run ruff format chat_api/ tests/
uv run ruff check chat_api/ tests/ --fix

# Type checking
uv run mypy chat_api/ --ignore-missing-imports

# Security scan
uv run bandit -r chat_api/ --skip B101

# Tests
uv run python -m pytest tests/ -v
```

### Docker Development
- `docker-compose build --no-cache` - Rebuild Docker image
- `CHAT_OPENROUTER_API_KEY=<key> docker-compose up -d` - Run with API key
- `docker-compose logs -f api` - Stream container logs
- `docker-compose down -v` - Stop and remove containers with volumes

### Make Targets
- `make dev` - Complete development setup (creates .env, installs deps)
- `make docker-env` - Full Docker environment setup
- `make clean` - Remove all temporary files
- `make deploy ENV=prod` - Deploy to AWS Lambda

⚠️ **IAC Deployment Notice**: The current Terraform configuration is **not compatible** with the updated architecture. See @docs/DEPLOYMENT_MIGRATION.md for required updates before deploying.

## Architecture Overview

This is a **Pythonic chat API** following "flat is better than nested" philosophy. The codebase was refactored from Java-style patterns to idiomatic Python, reducing code by 70%.

### Module Architecture

```
chat_api/
├── __init__.py      # Public API exports: app, process_message, ChatMessage
├── __main__.py      # Entry point for `python -m chat_api`
├── app.py           # FastAPI app with lifespan management
├── handlers.py      # HTTP endpoints (thin layer, delegates to core)
├── core.py          # Business logic (process_message, health_check)
├── storage.py       # Data persistence and caching
├── models.py        # Pydantic models with validation
├── config.py        # Settings singleton with CHAT_ prefix
├── middleware.py    # Request tracking (X-Request-ID)
└── background.py    # Async background tasks
```

### Request Flow

1. **Request arrives** at @chat_api/handlers.py endpoint
2. **Middleware** (@chat_api/middleware.py) adds request_id for tracking
3. **Handler** validates input via Pydantic models (@chat_api/models.py)
4. **Core** (@chat_api/core.py) checks cache, calls LLM if needed
5. **Storage** (@chat_api/storage.py) persists interaction to SQLite/DynamoDB
6. **Response** returns with tracking headers

### Key Design Decisions

**Module-Level Functions**: Core business logic in @chat_api/core.py is implemented as simple async functions rather than classes:
```python
# Direct function calls, not service objects
from chat_api import process_message
result = await process_message(user_id, content)
```

**Settings Singleton**: Configuration is loaded once at module level in @chat_api/config.py:
```python
# In config.py
settings = get_settings()  # Module-level singleton

# Used throughout
from chat_api.config import settings
```

**LLM Integration**: Uses litellm for provider abstraction (see @chat_api/core.py):
- Primary: Gemini (via `gemini/gemini-1.5-flash`)
- Fallback: OpenRouter (via `openrouter/auto`)
- Retry with exponential backoff (3 attempts)

**Storage Strategy** (@chat_api/storage.py):
- **Development**: SQLite with connection pooling
- **Production**: DynamoDB with on-demand scaling
- **Cache**: Redis (optional) or in-memory dict

### Environment Configuration

All environment variables use `CHAT_` prefix (defined in @chat_api/config.py):
- `CHAT_LLM_PROVIDER` - "gemini" or "openrouter"
- `CHAT_GEMINI_API_KEY` / `CHAT_OPENROUTER_API_KEY` - API credentials
- `CHAT_DATABASE_URL` - SQLite path or DynamoDB endpoint
- `CHAT_REDIS_URL` - Optional Redis for caching
- `CHAT_RATE_LIMIT` - Format: "60/minute"
- `CHAT_LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR

### API Endpoints

Defined in @chat_api/handlers.py:
- `POST /chat` - Process a chat message
- `GET /history/{user_id}` - Get user's chat history
- `GET /health` - Basic health check
- `GET /health/detailed` - Component health status
- `GET /` - API info and version

### Testing Strategy

Tests use pytest with async support and focus on behavior:
- **Fixtures** in @tests/conftest.py for shared test setup
- **Handler tests** in @tests/test_handlers.py
- **Core logic tests** in @tests/test_core.py
- **Model validation** in @tests/test_models.py
- **Storage tests** in @tests/test_storage.py
- **E2E tests** in @tests/test_e2e.py
- **Coverage** target: >75% (currently 79.29%)

### Error Handling

Specific exception types for each failure mode (defined in @chat_api/models.py):
- `ConnectionError, TimeoutError` - Infrastructure issues (retry)
- `ValueError, ValidationError` - Input validation (400)
- `JSONDecodeError` - Serialization issues (422)
- Custom exceptions in @chat_api/models.py for domain errors

### Deployment

**Local**: `uv run python -m chat_api` (FastAPI with auto-reload via @chat_api/__main__.py)
**Docker**: Multi-stage build (@Dockerfile) with distroless base
**AWS Lambda**: Via Mangum adapter in @chat_api/lambda_handler.py
**Docker Compose**: Configuration in @docker-compose.yml

### Common Development Tasks

When modifying the API:
1. Update models in @chat_api/models.py with Pydantic validation
2. Add endpoint in @chat_api/handlers.py (thin layer)
3. Implement logic in @chat_api/core.py
4. Add tests in corresponding `test_*.py` file
5. Run @scripts/check.sh before committing

When debugging:
- Check logs with `logger` from loguru (structured logging)
- Request tracking via X-Request-ID header (@chat_api/middleware.py)
- Use `/health/detailed` for component status
- SQLite database at `chat_history.db` (local)

### Important Configuration Files

- @pyproject.toml - Package dependencies and project metadata
- @.env.example - Environment variable template
- @Makefile - Common development and deployment tasks
- @.pre-commit-config.yaml - Git hooks for code quality
- @docs/adr/ - Architecture Decision Records
