.PHONY: help install test check

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Install development dependencies
	uv pip install -e ".[dev,plot]"

test: ## Run tests
	uv run pytest --cov=src --cov-report=term-missing

check: ## Run linter
	@echo "Running linter..."
	uv run ruff check . --ignore N806,N999
	@echo "\nAll checks passed!"
