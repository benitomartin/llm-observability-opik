from zenml import pipeline

from src.configs.settings import Settings
from src.steps.etl.crawl_step import crawl_step
from src.steps.etl.mongo_ingest_step import mongo_ingest_step
from src.steps.etl.parse_step import parse_step

settings = Settings()
settings.load_yaml()


@pipeline
def team_pipeline() -> None:
    """
    ETL pipeline for crawling, parsing, and ingesting team data.
    """
    if settings.yaml_config is None:
        raise ValueError("YAML configuration not loaded")

    crawled_data = crawl_step(config=settings.yaml_config)
    parsed_docs = parse_step(crawled_data=crawled_data)
    mongo_ingest_step(documents=parsed_docs)


if __name__ == "__main__":
    # Instantiate the pipeline object
    team_pipeline()
