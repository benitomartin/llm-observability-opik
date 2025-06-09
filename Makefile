# Makefile

# Check if .env exists
ifeq (,$(wildcard .env))
$(error .env file is missing at .env. Please create one based on .env.example)
endif

# Load environment variables from .env
include .env

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


run-team-pipeline: ## Run the ZenML team pipeline
	@echo "Running the ZenML pipeline..."
	uv run src/pipelines/team_pipeline.py
	@echo "ZenML pipeline run complete."


run-summarization-pipeline: ## Run the ZenML summarization pipeline
	@echo "Running the ZenML pipeline..."
	uv run src/pipelines/summarization_pipeline.py
	@echo "ZenML pipeline run complete."

run-dataset-pipeline: ## Run the ZenML dataset pipeline
	@echo "Running the ZenML dataset pipeline..."
	uv run src/pipelines/dataset_pipeline.py
	@echo "ZenML dataset pipeline run complete."

################################################################################
## MongoDB Commands
################################################################################


create-collection-index: ## Create the MongoDB collection
	@echo "Creating the MongoDB collection index..."
	uv run src/infra/create_collection.py
	@echo "MongoDB collection created successfully."

insert-embeddings: ## Insert embeddings into the MongoDB collection
	@echo "Inserting embeddings into the MongoDB collection index..."
	uv run src/infra/insert_embeddings.py
	@echo "Embeddings inserted successfully."

################################################################################
## Search Commands
################################################################################

run-search: ## Run the search script
	@echo "Running the search script..."
	uv run src/similarity/search.py
	@echo "Search script run complete."

################################################################################
## Evaluation Commands
################################################################################

run-evaluate-summaries: ## Run the evaluation script
	@echo "Running the evaluation script..."
	uv run src/evaluation/evaluate_summaries_opik.py
	@echo "Evaluation script run complete."

run-evaluate-dataset: ## Evaluate the dataset using the MongoDB collection
	@echo "Evaluating the dataset using the MongoDB collection..."
	uv run src/evaluation/evaluate_dataset.py
	@echo "Dataset evaluation complete."


#################################################################################
## Testing Commands
#################################################################################

run-tests: ## Run all tests
	@echo "Running all tests..."
	uv run pytest
	@echo "All tests completed."


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
