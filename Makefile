.DEFAULT_GOAL := help
ENV ?= dev

.PHONY: help
help: ## Show this help message
	@echo "Usage: make <target> [ENV=dev|staging|prod]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

.PHONY: dev
dev: ## Complete development setup
	@echo "Setting up development environment..."
	@[ -f .env ] || cp .env.example .env && echo "✓ Created .env file"
	@pip install --no-user -e ".[dev]" && echo "✓ Installed dependencies"
	@pre-commit install && echo "✓ Installed pre-commit hooks"
	@echo "✅ Development environment ready!"

.PHONY: clean
clean: ## Clean all temporary files and build artifacts
	@echo "Cleaning temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov/ 2>/dev/null || true
	@rm -f chat_history.db .secrets.baseline 2>/dev/null || true
	@rm -rf iac/terraform/layer/ iac/terraform/lambda_*.zip 2>/dev/null || true
	@rm -rf iac/terraform/.terraform/ iac/terraform/.terraform.lock.hcl 2>/dev/null || true
	@echo "✅ Cleaned temporary files"

.PHONY: docker-env
docker-env: ## Full Docker environment setup
	@echo "Setting up Docker environment..."
	@docker build -t serverless-chat-api:latest .
	@docker-compose up -d
	@echo "✅ Running on http://localhost:8000"
	@echo "   View logs: docker-compose logs -f api"

.PHONY: docker-reset
docker-reset: ## Complete Docker cleanup and data removal
	@echo "Resetting Docker environment..."
	@docker-compose down -v 2>/dev/null || true
	@rm -rf data/ 2>/dev/null || true
	@docker rmi serverless-chat-api:latest 2>/dev/null || true
	@echo "✅ Docker environment reset"

.PHONY: deploy
deploy: ## Deploy to AWS Lambda (builds dependencies and applies Terraform)
	@echo "🚀 Deploying to AWS ($(ENV))..."
	@cd iac/terraform && [ -f terraform.tfvars.$(ENV) ] || cp terraform.tfvars.example terraform.tfvars.$(ENV)
	@cd iac/terraform && terraform init -reconfigure
	@$(MAKE) build-layer
	@cd iac/terraform && terraform apply -var-file="terraform.tfvars.$(ENV)" -auto-approve
	@echo "✅ Deployment complete!"
	@cd iac/terraform && terraform output -json | jq '.' 2>/dev/null || terraform output

.PHONY: build-layer
build-layer: ## Build Lambda layer with Python dependencies
	@echo "📦 Building Lambda layer..."
	@pip install -e . --quiet
	@pip freeze | grep -v "^-e" | grep -v "uvicorn" > /tmp/lambda-deps.txt
	@rm -rf iac/terraform/layer iac/terraform/lambda_layer.zip
	@mkdir -p iac/terraform/layer/python
	@pip install -r /tmp/lambda-deps.txt \
		-t iac/terraform/layer/python \
		--platform manylinux2014_x86_64 \
		--only-binary=:all: \
		--upgrade \
		--quiet
	@rm /tmp/lambda-deps.txt
	@find iac/terraform/layer -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@find iac/terraform/layer -type d -name '*.dist-info' -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Layer built: $$(du -sh iac/terraform/layer 2>/dev/null | cut -f1 || echo 'N/A')"

.PHONY: destroy
destroy: ## Destroy all AWS resources (requires confirmation)
	@echo "⚠️  WARNING: This will destroy all AWS resources!"
	@read -p "Type 'destroy' to confirm: " confirm && [ "$$confirm" = "destroy" ] || exit 1
	@cd iac/terraform && terraform destroy -var-file="terraform.tfvars.$(ENV)" -auto-approve
	@echo "✅ Resources destroyed"

.PHONY: logs
logs: ## Stream Lambda function logs from CloudWatch
	@cd iac/terraform && FUNCTION_NAME=$$(terraform output -raw lambda_function_name 2>/dev/null); \
	if [ -z "$$FUNCTION_NAME" ]; then \
		echo "❌ Lambda not deployed yet"; \
		exit 1; \
	fi; \
	aws logs tail --follow "/aws/lambda/$$FUNCTION_NAME"

.PHONY: diagrams
diagrams: ## Generate architecture diagrams (12 professional diagrams with custom icons)
	@echo "🎨 Generating architecture diagrams with custom icons..."
	@if ! python -c "import diagrams" 2>/dev/null; then \
		echo "📦 Installing Python diagrams..."; \
		pip install diagrams --quiet; \
	fi
	@cd docs/diagrams && python generate_final_diagrams.py
	@cd docs/diagrams && python sequence_diagrams.py
	@mv docs/diagrams/*.png docs/asset/ 2>/dev/null || true
	@echo "✅ Professional architecture diagrams generated!"
	@echo "   📄 docs/ARCHITECTURE.md"
	@echo "   📊 12 professional diagrams in docs/asset/"
	@echo "   🎨 Custom icons for validation, config, errors, APIs"
	@echo ""
	@echo "   Each diagram answers ONE question:"
	@echo "   - Static Structure: What are the components?"
	@echo "   - Request Flow: How does a request flow?"
	@echo "   - Deployments: Where does it run?"
	@echo "   - Data Flow: How is data transformed?"
	@echo "   - Error Handling: What happens on failure?"
	@echo "   - Dependencies: What depends on what?"
	@echo "   - AWS Infrastructure: What AWS services?"
	@echo "   - Protocols: How do protocols work?"
	@echo "   - Plus 4 sequence diagrams for time-ordered flows"


# Direct commands to use:
#   pytest tests/                           # Run all tests
#   pytest tests/unit/                      # Run unit tests only
#   pytest tests/ --cov=src                 # Run tests with coverage
#   pre-commit run --all-files              # Run all code quality checks
#   python -m src.main                      # Start the application locally
#   docker-compose logs -f                  # View Docker logs
#
# Terraform commands (from iac/terraform/):
#   terraform init                          # Initialize Terraform
#   terraform plan -var-file="terraform.tfvars.dev"  # Preview changes
#   terraform validate                      # Validate configuration
#   terraform fmt -recursive                # Format .tf files
#   terraform output                        # Show outputs
#   terraform state list                    # List resources
#
# Test Lambda endpoint:
#   curl $(cd iac/terraform && terraform output -raw lambda_function_url)/v1/health
