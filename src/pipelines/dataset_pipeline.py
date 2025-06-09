from zenml import pipeline

from src.configs.settings import Settings
from src.steps.generate_dataset.generate_dataset_step import generate_qa_dataset


@pipeline
def dataset_pipeline() -> None:
    """
    ZenML pipeline to generate the QA dataset.

    Raises:
        ValueError: If YAML configuration is not loaded properly.
    """
    if settings.yaml_config is None:
        raise ValueError("YAML configuration not loaded")

    generate_qa_dataset(config=settings.yaml_config)


if __name__ == "__main__":
    settings = Settings()
    settings.load_yaml()

    dataset_pipeline()
