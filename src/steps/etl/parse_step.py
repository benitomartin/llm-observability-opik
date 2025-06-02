from typing import Any

from loguru import logger
from zenml import step

from src.configs.settings import CrawledDoc


@step(enable_cache=True)
def parse_step(crawled_data: list[CrawledDoc]) -> list[dict[str, Any]]:
    """
    Parses crawled content and adds metadata.

    Args:
        crawled_data: List of dictionaries with team content from crawl_step.

    Returns:
        A list of enriched document dictionaries.
    """
    docs: list[dict[str, Any]] = []

    for team in crawled_data:
        logger.info(f"Parsing content for: {team.team}")

        docs.append(
            {
                "team": team.team,
                "source_url": team.url,
                "content": team.content,
                "timestamp": team.timestamp.isoformat(),
                "metadata": team.metadata,
            }
        )

    logger.success(f"Parsed {len(docs)} documents.")
    return docs
