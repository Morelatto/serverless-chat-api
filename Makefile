.PHONY: help run docker test clean deploy

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

run: ## Run locally with Python
	python -m src.main

docker: ## Run with Docker Compose
	docker-compose up --build

docker-down: ## Stop Docker containers
	docker-compose down

test: ## Run tests
	python -m pytest tests/ -v

install: ## Install dependencies (modern)
	pip install -e .

install-dev: ## Install with dev dependencies
	pip install -e ".[dev]"

install-legacy: ## Install from requirements.txt (legacy)
	pip install -r requirements.txt

clean: ## Clean cache and temp files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -f chat_history.db
	rm -rf .pytest_cache

deploy: ## Deploy to AWS (requires terraform)
	cd infra/terraform && terraform init && terraform apply

format: ## Format code with black
	black src/

lint: ## Lint code with ruff
	ruff check src/ --fix

setup: ## Initial setup
	cp .env.example .env
	@echo "✅ Setup complete! Edit .env with your API keys"