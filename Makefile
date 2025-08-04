# Project settings
PROJECT_NAME = processo-itau-v3
SRC_DIR = src
DATA_DIR = data

# Environment
ENV_FILE = .env
ENV_EXAMPLE = .env.example

# Tools
PYTHON = python
PIP = pip
DOCKER = docker
DOCKER_COMPOSE = docker-compose
RUFF = ruff
MYPY = mypy

# Docker
DOCKER_IMAGE = $(PROJECT_NAME):latest
DOCKER_SERVICE = api
DOCKER_PORT = 8000

# Clean patterns
CLEAN_PATTERNS = __pycache__ .pytest_cache .mypy_cache .ruff_cache *.pyc .coverage
CLEAN_FILES = chat_history.db .secrets.baseline

# Default target
.DEFAULT_GOAL := help

.PHONY: help
help: ## Show help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# Development setup
.PHONY: setup
setup: ## Setup environment configuration
	@if [ ! -f $(ENV_FILE) ]; then \
		cp $(ENV_EXAMPLE) $(ENV_FILE) && \
		echo "✓ Created $(ENV_FILE)"; \
	fi

.PHONY: clean
clean: ## Clean cache and temporary files
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .pytest_cache .mypy_cache .ruff_cache
	@rm -f $(CLEAN_FILES) 2>/dev/null || true

# Installation
.PHONY: install install-dev
install: ## Install package
	@$(PIP) install --no-user -e .

install-dev: ## Install with dev dependencies
	@$(PIP) install --no-user -e ".[dev]"

# Application
.PHONY: run test test-unit test-integration
run: ## Start application server
	@$(PYTHON) -m $(SRC_DIR).main

test: ## Run all tests with pytest
	@pytest tests/ -v

test-unit: ## Run unit tests only
	@pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@pytest tests/integration/ -v

# Code quality
.PHONY: lint lint-fix typecheck check pre-commit
lint: ## Run linter (check only)
	@$(RUFF) check $(SRC_DIR)/ tests/

lint-fix: ## Run linter with auto-fix
	@$(RUFF) check $(SRC_DIR)/ tests/ --fix

typecheck: ## Run type checker
	@$(MYPY) $(SRC_DIR)/ --strict

check: lint typecheck ## Run all code quality checks

pre-commit: ## Run pre-commit hooks on all files
	@PIP_USER=false pre-commit run --all-files

# Docker
.PHONY: docker-build docker docker-down docker-logs docker-clean
docker-build: ## Build Docker image
	@$(DOCKER) build -t $(DOCKER_IMAGE) .

docker: docker-build ## Build and start services
	@$(DOCKER_COMPOSE) up -d
	@echo "✓ Running on http://localhost:$(DOCKER_PORT)"

docker-down: ## Stop services
	@$(DOCKER_COMPOSE) down

docker-logs: ## Show container logs
	@$(DOCKER_COMPOSE) logs -f $(DOCKER_SERVICE)

docker-clean: docker-down ## Clean Docker volumes
	@$(DOCKER_COMPOSE) down -v
	@rm -rf $(DATA_DIR)/

# Compound targets
.PHONY: dev all-tests full-clean test-cov
dev: setup install-dev ## Complete dev setup
all-tests: test ## Run all tests
test-cov: ## Run tests with coverage
	@pytest tests/ --cov=src --cov-report=term-missing
full-clean: clean docker-clean ## Complete cleanup
