# Sport Teams AI Evaluation and Observability

A modular pipeline for LLM observability, evaluation, and summarization using **ZenML**, **MongoDB**, and **Opik**.

## Overview

- **ETL Pipeline**: Crawl, parse, and ingest Wikipedia articles into MongoDB.
- **Summarization Pipeline**: Generate summaries for each article using LLMs.
- **Evaluation Pipelines**: Score summaries and QA datasets using BERTScore, cosine similarity, and Opik metrics.
- **Experiment Tracking**: Integrated with **ZenML** and **Opik** for experiment and metric visualization.
- **Configurable**: Customize settings via YAML and environment variables.

## Project Structure

```text
.
├── LICENSE
├── Makefile
├── README.md
├── pyproject.toml
├── uv.lock
├── src
│   ├── configs/               # Configs, prompts, and settings
│   ├── data/                  # Evaluation data and crawled team data
│   ├── evaluation/            # Summary and QA evaluation scripts
│   ├── infra/                 # MongoDB vector index utilities
│   ├── pipelines/             # ZenML pipeline entrypoints
│   ├── similarity/            # Semantic similarity search utilities
│   ├── steps/                 # ZenML steps: ETL, dataset, summaries
│   └── tests/                 # Unit tests
```

## Getting Started

### Prerequisites

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv)
- [ZenML](https://zenml.io/)
- [Opik](https://www.comet.com/site/products/opik/)
- [MongoDB](https://www.mongodb.com/)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/llm-observability-opik.git
   cd llm-observability-opik
   ```

1. **Install dependencies**

   ```bash
   uv sync --all-groups
   source ./.venv/bin/activate
   ```

1. **Configure environment**

   - Copy `.env.example` to `.env` and update with your credentials:

     ```bash
     cp .env.example .env
     ```

1. **Create MongoDB Account**

   You need to create a MongoDB account to store and query data. Once the account has been created, you need to get the MONGODB_URI`and add it into the`.env file\`.

   This project consider two collections. One to store the wikipedia articles with summaries and another with additional vector index and embeddings for similarity search.

## Usage

### Pipelines

- **Start ZenML**

  ```bash
  make zenml-login
  ```

- **ETL pipeline**

  ```bash
  make run-team-pipeline
  ```

- **Summarization pipeline**

  ```bash
  make run-summarization-pipeline
  ```

### Evaluation

- **Evaluate QA dataset**

  ```bash
  uv run src/evaluation/evaluate_dataset.py
  ```

- **Evaluate summaries with Opik**

  Evaluate the summaries using BERT Score and Cosine Similarity:

  ```bash
  make run-evaluate-summaries
  ```

  Evaluate a synthetic Q&A dataset on Hallucinations and Answer Relevancy:

  ```bash
  make run-evaluate-dataset
  ```

### Dev Tools

- **Lint, format, and type-check**

  ```bash
  make all
  ```

## Configuration

You can configure the following:

- MongoDB connection
- OpenAI API and model names
- Evaluation dataset paths

Edit:

- `src/configs/settings.py`
- `src/configs/config.yaml`

## Experiment Tracking

- **ZenML Dashboard**: [http://127.0.0.1:8237](http://127.0.0.1:8237)
- **Opik**: [Opik](https://www.comet.com/site/products/opik/)
- **MongoDB**: [MongoDB](https://www.mongodb.com/)

## 📄 License

[MIT License](LICENSE)
