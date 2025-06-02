from zenml import pipeline

from src.configs.settings import Settings
from src.steps.generate_dataset.generate_summaries_step import summarize_step  # adjust import path as needed

settings = Settings()
settings.load_yaml()  # load YAML into settings.yaml_config


@pipeline
def summarization_pipeline() -> None:
    summarize_step(
        mongodb_uri=settings.mongodb_uri,
        mongodb_database=settings.mongodb_database,
        mongodb_collection=settings.mongodb_collection,
        summaries_dir=settings.yaml_config.summaries_dir,
    )


if __name__ == "__main__":
    summarization_pipeline()
