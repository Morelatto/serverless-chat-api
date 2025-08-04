.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help message
	@echo "Usage: make <target>"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

.PHONY: dev
dev: ## Complete development setup
	@echo "Setting up development environment..."
	@[ -f .env ] || cp .env.example .env && echo "✓ Created .env file"
	@pip install --no-user -e ".[dev]" && echo "✓ Installed dependencies"
	@pre-commit install && echo "✓ Installed pre-commit hooks"
	@echo "✅ Development environment ready!"

.PHONY: clean
clean: ## Clean all temporary and cache files
	@echo "Cleaning temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov/ 2>/dev/null || true
	@rm -f chat_history.db .secrets.baseline 2>/dev/null || true
	@echo "✅ Cleaned temporary files"

.PHONY: docker-env
docker-env: ## Full Docker environment setup
	@echo "Setting up Docker environment..."
	@docker build -t processo-itau-v3:latest .
	@docker-compose up -d
	@echo "✅ Running on http://localhost:8000"
	@echo "   View logs: docker-compose logs -f api"

.PHONY: docker-reset
docker-reset: ## Complete Docker cleanup and data removal
	@echo "Resetting Docker environment..."
	@docker-compose down -v 2>/dev/null || true
	@rm -rf data/ 2>/dev/null || true
	@docker rmi processo-itau-v3:latest 2>/dev/null || true
	@echo "✅ Docker environment reset"

# Direct commands to use:
#   pytest tests/                    # Run all tests
#   pytest tests/unit/               # Run unit tests
#   pytest tests/ --cov=src          # Run tests with coverage
#   pre-commit run --all-files       # Run all code quality checks
#   python -m src.main               # Start the application
#   docker-compose logs -f           # View Docker logs