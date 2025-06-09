import os
from datetime import UTC, datetime

from loguru import logger
from zenml import step

from src.configs.settings import CrawledDoc, YamlConfig
from src.steps.etl.wikipedia_crawler import extract_wikipedia_page


@step(enable_cache=False)
def crawl_step(config: YamlConfig) -> list[CrawledDoc]:
    """
    ZenML pipeline step: Extracts Wikipedia articles and stores them as text files.

    Args:
        config (YamlConfig): Parsed YAML configuration.

    Returns:
        List[CrawledDoc]: Cleaned documents for downstream use.
    """
    output_dir = config.output_dir
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    results: list[CrawledDoc] = []

    for team in config.teams:
        logger.info(f"📘 Extracting: {team.name}")
        page_title = team.url.split("/wiki/")[-1]
        file_path = os.path.join(output_dir, team.filename)

        # ✅ Skip if file already exists
        if os.path.exists(file_path):
            logger.info(f"✅ Wikipedia content already exists for {team.name}, skipping.")
            with open(file_path, encoding="utf-8") as f:
                content: str | None = f.read()
            results.append(
                CrawledDoc(
                    team=team.name,
                    url=team.url,
                    filename=team.filename,
                    content=content or "",
                    timestamp=datetime.now(UTC),
                    metadata=team.metadata or {},
                )
            )
            continue

        try:
            content = extract_wikipedia_page(page_title, file_path)
            if content:
                results.append(
                    CrawledDoc(
                        team=team.name,
                        url=team.url,
                        filename=team.filename,
                        content=content,
                        timestamp=datetime.now(UTC),
                        metadata=team.metadata or {},
                    )
                )
            else:
                logger.warning(f"No content for {team.name} / {page_title}")
        except Exception as e:
            logger.error(f"❌ Failed to extract {team.name}: {e}")

    logger.success(f"🧾 Done. Crawled {len(results)} documents.")
    return results
