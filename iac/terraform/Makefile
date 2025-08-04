# Makefile for Lambda deployment with Terraform

.PHONY: help init plan apply destroy clean build-layer test-local fmt validate

# Variables
ENV ?= dev
TF_VAR_FILE = terraform.tfvars.$(ENV)
PYTHON_VERSION = 3.11

help: ## Show this help message
	@echo "Usage: make [target] ENV=[dev|staging|prod]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

init: ## Initialize Terraform
	terraform init -reconfigure

validate: ## Validate Terraform configuration
	terraform validate

fmt: ## Format Terraform files
	terraform fmt -recursive

plan: init ## Plan Terraform changes
	@if [ ! -f $(TF_VAR_FILE) ]; then \
		echo "Error: $(TF_VAR_FILE) not found. Copy terraform.tfvars.example to $(TF_VAR_FILE)"; \
		exit 1; \
	fi
	terraform plan -var-file="$(TF_VAR_FILE)"

apply: init ## Apply Terraform changes
	@if [ ! -f $(TF_VAR_FILE) ]; then \
		echo "Error: $(TF_VAR_FILE) not found. Copy terraform.tfvars.example to $(TF_VAR_FILE)"; \
		exit 1; \
	fi
	terraform apply -var-file="$(TF_VAR_FILE)" -auto-approve

destroy: ## Destroy Terraform resources
	@if [ ! -f $(TF_VAR_FILE) ]; then \
		echo "Error: $(TF_VAR_FILE) not found"; \
		exit 1; \
	fi
	@echo "WARNING: This will destroy all resources!"
	@read -p "Are you sure? (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1
	terraform destroy -var-file="$(TF_VAR_FILE)" -auto-approve

build-layer: ## Build Lambda layer with dependencies
	@echo "Building Lambda layer for Python $(PYTHON_VERSION)..."
	@cd ../.. && pip install -e . --quiet
	@pip freeze | grep -v "^-e" | grep -v "uvicorn" > /tmp/lambda-deps.txt
	@rm -rf layer lambda_layer.zip
	@mkdir -p layer/python
	@pip install -r /tmp/lambda-deps.txt \
		-t layer/python \
		--platform manylinux2014_x86_64 \
		--only-binary=:all: \
		--upgrade \
		--quiet
	@rm /tmp/lambda-deps.txt
	@find layer -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@find layer -type d -name '*.dist-info' -exec rm -rf {} + 2>/dev/null || true
	@echo "Layer built: $$(du -sh layer | cut -f1)"

test-local: ## Test Lambda function locally
	@echo "Testing Lambda function locally..."
	@cd ../.. && python -m pytest tests/ -v

clean: ## Clean build artifacts
	rm -rf layer/
	rm -f lambda_function.zip
	rm -f lambda_layer.zip
	rm -rf .terraform/
	rm -f .terraform.lock.hcl
	rm -rf lambda_package/
	@echo "Cleaned build artifacts"

refresh: ## Refresh Terraform state
	terraform refresh -var-file="$(TF_VAR_FILE)"

output: ## Show Terraform outputs
	@terraform output -json | jq '.'

logs: ## Tail Lambda function logs
	@FUNCTION_NAME=$$(terraform output -raw lambda_function_name 2>/dev/null); \
	if [ -z "$$FUNCTION_NAME" ]; then \
		echo "Error: Lambda function not deployed yet"; \
		exit 1; \
	fi; \
	aws logs tail --follow "/aws/lambda/$$FUNCTION_NAME"

invoke: ## Invoke Lambda function with test event
	@FUNCTION_URL=$$(terraform output -raw lambda_function_url 2>/dev/null); \
	if [ -z "$$FUNCTION_URL" ]; then \
		echo "Error: Lambda function not deployed yet"; \
		exit 1; \
	fi; \
	echo "Testing health endpoint..."; \
	curl -s "$$FUNCTION_URL/v1/health" | jq '.'

deploy: fmt validate build-layer apply ## Full deployment (format, validate, build, apply)
	@echo "Deployment complete!"
	@echo ""
	@make output

quick-deploy: apply ## Quick deployment without building layer
	@echo "Quick deployment complete!"

# Advanced targets
import-state: ## Import existing AWS resources into Terraform state
	@echo "Importing existing resources..."
	@read -p "Enter Lambda function name: " fname; \
	terraform import -var-file="$(TF_VAR_FILE)" aws_lambda_function.api $$fname
	@read -p "Enter DynamoDB table name: " tname; \
	terraform import -var-file="$(TF_VAR_FILE)" aws_dynamodb_table.main $$tname

state-list: ## List resources in Terraform state
	terraform state list

backup-state: ## Backup current Terraform state
	@mkdir -p backups
	@terraform state pull > backups/terraform-state-$$(date +%Y%m%d-%H%M%S).json
	@echo "State backed up to backups/"

check-drift: ## Check for configuration drift
	terraform plan -var-file="$(TF_VAR_FILE)" -detailed-exitcode || true