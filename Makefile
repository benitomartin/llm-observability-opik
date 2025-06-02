# Makefile

.PHONY: all ruff mypy clean help


################################################################################
## ZenML Commands
################################################################################

zenml-login: ## Login to ZenML using local mode
	@echo "Logging in to ZenML in local mode..."
	uv run zenml login --local
	@echo "ZenML login complete."

zenml-logout: ## Login to ZenML using local mode
	@echo "Logging out to ZenML in local mode..."
	uv run zenml logout --local
	@echo "ZenML log out complete."


run-pipeline: ## Run the ZenML pipeline
	@echo "Running the ZenML pipeline..."
	uv run src/pipelines/team_pipeline.py
	@echo "ZenML pipeline run complete."









# build: ## Build the Docker image
# 	@echo "Building Docker image..."
# 	docker-compose up -d
# 	@echo "Docker image built successfully."


################################################################################
## Linting and Formatting
################################################################################

all: ruff mypy clean ## Run all linting and formatting commands

ruff: ## Run Ruff linter
	@echo "Running Ruff linter..."
	uv run ruff check . --fix --exit-non-zero-on-fix
	@echo "Ruff linter complete."

mypy: ## Run MyPy static type checker
	@echo "Running MyPy static type checker..."
	uv run mypy
	@echo "MyPy static type checker complete."

clean: ## Clean up cached generated files
	@echo "Cleaning up generated files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Cleanup complete."


################################################################################
## Help Command
################################################################################

help: ## Display this help message
	@echo "Default target: $(.DEFAULT_GOAL)"
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.DEFAULT_GOAL := help
