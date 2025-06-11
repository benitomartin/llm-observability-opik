import json
from pathlib import Path
from typing import Any

from loguru import logger
from openai import OpenAI
from opik import Opik, track
from opik.evaluation import evaluate
from opik.evaluation.metrics import AnswerRelevance, Hallucination
from opik.integrations.openai import track_openai

from src.configs.settings import Settings


def load_config_and_dataset() -> tuple[Settings, list[dict[str, str]]]:
    """
    Load the YAML configuration settings and the evaluation QA dataset from JSON.

    Returns:
        A tuple of:
            - Settings object with loaded configuration
            - List of QA pairs loaded from the dataset file
    """
    settings = Settings()
    settings.load_yaml()
    config = settings.yaml_config

    eval_path = Path(config.eval_dir) / config.eval_dataset
    logger.info(f"Loading QA dataset from: {eval_path}")
    with open(eval_path, encoding="utf-8") as f:
        qa_data = json.load(f)

    return settings, qa_data


def initialize_openai_client(api_key: str) -> OpenAI:
    """
    Initialize and return an OpenAI client wrapped with Opik tracking.

    Args:
        api_key: OpenAI API key string.

    Returns:
        OpenAI client instance wrapped with tracking.
    """
    return track_openai(OpenAI(api_key=api_key))


def get_llm_application(model: str, openai_client: OpenAI) -> Any:
    """
    Create a tracked LLM application function that queries the OpenAI API.

    Args:
        model: The model name to use for chat completions.
        openai_client: Initialized OpenAI client.

    Returns:
        A function that takes a string input and returns the model's output string.
    """

    @track
    def app(input: str) -> str:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": input}],
        )
        content = response.choices[0].message.content
        return content.strip() if content is not None else ""

    return app


def evaluate_llm_app(settings: Settings, qa_data: list[dict[str, str]]) -> None:
    """
    Evaluate the LLM application on a dataset of QA pairs using Opik.

    Args:
        settings: Loaded Settings object containing model and API key.
        qa_data: List of question-answer dicts to evaluate.
    """
    model = settings.openai_llm_model
    openai_client = initialize_openai_client(settings.openai_api_key)
    llm_app = get_llm_application(model, openai_client)

    def task(x: dict[str, Any]) -> dict:
        """
        Run the LLM application on a single QA input.

        Args:
            x: A dictionary with an "input" key.

        Returns:
            A dictionary with the model's output.
        """
        return {"output": llm_app(x["input"])}

    client = Opik()
    dataset = client.get_or_create_dataset(name="QA Dataset")
    dataset.insert(qa_data)

    metrics = [
        Hallucination(),
        AnswerRelevance(require_context=False),
    ]

    logger.info("Running evaluation...")
    evaluate(
        dataset=dataset,
        task=task,
        scoring_metrics=metrics,
        experiment_config={
            "model": model,
            "description": "Evaluation of QA LLM application using summaries from MongoDB context",
        },
    )
    logger.info("✅ Evaluation completed.")


if __name__ == "__main__":
    settings, qa_data = load_config_and_dataset()
    evaluate_llm_app(settings, qa_data)
