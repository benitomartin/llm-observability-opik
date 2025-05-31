import asyncio
import os

import yaml
from crawl4ai import AsyncWebCrawler
from zenml import step


@step
def crawl_step(config_path: str = "config.yaml") -> None:
    with open(config_path) as f:
        config = yaml.safe_load(f)

    output_dir = config["output_dir"]
    os.makedirs(output_dir, exist_ok=True)

    async def crawl() -> None:
        async with AsyncWebCrawler() as crawler:
            for team in config["teams"]:
                url = team["url"]
                filename = team["filename"]
                result = await crawler.arun(url=url)
                with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                    f.write(result.markdown)

    asyncio.run(crawl())
