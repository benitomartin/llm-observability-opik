import json
import os

from loguru import logger
from openai import OpenAI
from zenml import step

from src.configs.settings import Settings, YamlConfig
from src.steps.generate_dataset.mongo_client import MongoVectorSearchClient
from src.steps.generate_dataset.questions import answer_query_with_context, questions


@step
def generate_qa_dataset(config: YamlConfig) -> list[dict[str, str]]:
    """ZenML step to generate a QA dataset using MongoDB context and OpenAI completions.

    Args:
        config (YamlConfig): Configuration object containing evaluation paths.

    Returns:
        list[dict[str, str]]: List of dictionaries with questions and generated answers.
    """
    eval_dir = config.eval_dir
    eval_dataset = config.eval_dataset
    os.makedirs(eval_dir, exist_ok=True)
    logger.info(f"Output directory: {eval_dir}")

    settings = Settings()
    openai_client = OpenAI(api_key=settings.openai_api_key)
    vector_client = MongoVectorSearchClient(connection_uri=settings.mongodb_uri, db_name=settings.mongodb_database)

    qa_pairs = []
    for q in questions:
        logger.info(f"Generating answer for question: {q}")
        answer = answer_query_with_context(openai_client, vector_client, settings, q)
        qa_pairs.append({"input": q, "expected_output": answer})

    vector_client.close_connection()

    # Save dataset
    output_path = os.path.join(eval_dir, eval_dataset)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(qa_pairs, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ Dataset saved to {output_path}")
    return qa_pairs
