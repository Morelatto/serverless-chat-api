.PHONY: help clean setup install install-dev run test test-suite lint lint-fix typecheck docker-build docker docker-down docker-logs docker-clean

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

clean: ## Clean cache and temp files  
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -f chat_history.db
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf reports/*.log reports/*.json

setup: ## Setup development environment
	@echo "Setting up environment..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Created .env from .env.example"; \
	else \
		echo "✓ .env already exists"; \
	fi
	@echo "✓ Setup complete. Edit .env to add your API keys."

install: ## Install package in editable mode
	pip install --no-user -e .

install-dev: ## Install package with dev dependencies
	pip install --no-user -e ".[dev]"

run: ## Start the server
	python -m src.main

test: ## Run simple server test
	python test_server.py

test-suite: ## Run complete test suite
	python test_suite.py

lint: ## Run linter (check only)
	ruff check src/

lint-fix: ## Run linter with auto-fix
	ruff check src/ --fix

typecheck: ## Run type checker
	mypy src/ --strict

docker-build: ## Build Docker image
	@echo "Building Docker image..."
	docker build -t processo-itau-v3:latest .
	@echo "✓ Docker image built successfully"

docker: ## Start services with docker-compose
	@echo "Starting Docker services..."
	docker-compose up -d
	@echo "✓ Services running on http://localhost:8000"
	@echo "✓ Health check: http://localhost:8000/v1/health"

docker-down: ## Stop and remove Docker services
	@echo "Stopping Docker services..."
	docker-compose down
	@echo "✓ Services stopped"

docker-logs: ## Show Docker container logs
	docker-compose logs -f api

docker-clean: ## Remove Docker volumes and clean data
	@echo "Cleaning Docker volumes and data..."
	docker-compose down -v
	rm -rf data/
	@echo "✓ Docker volumes and data cleaned"