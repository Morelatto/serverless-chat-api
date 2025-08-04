.PHONY: help clean

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

clean: ## Clean cache and temp files  
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -f chat_history.db
	rm -rf .pytest_cache