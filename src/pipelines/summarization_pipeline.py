from zenml import pipeline

from src.configs.settings import Settings
from src.steps.generate_summaries.generate_summaries_step import summarize_step


@pipeline
def summarization_pipeline() -> None:
    """
    Pipeline to generate summaries using the summarize_step.
    """
    summarize_step(
        mongodb_uri=settings.mongodb_uri,
        mongodb_database=settings.mongodb_database,
        mongodb_collection=settings.mongodb_collection,
    )


if __name__ == "__main__":
    settings = Settings()

    summarization_pipeline()
