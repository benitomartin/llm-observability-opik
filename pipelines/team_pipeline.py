from zenml import pipeline

from steps.crawl_step import crawl_step
from steps.mongo_ingest_step import mongo_ingest_step
from steps.parse_step import parse_step


@pipeline
def team_pipeline() -> None:
    crawl_step()
    docs = parse_step()
    mongo_ingest_step(docs)


if __name__ == "__main__":
    # Instantiate the pipeline object
    p = team_pipeline()
