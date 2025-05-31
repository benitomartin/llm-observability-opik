import asyncio
import os

import yaml
from crawl4ai import AsyncWebCrawler

# Load config from YAML
with open("config.yaml") as f:
    config = yaml.safe_load(f)

OUTPUT_DIR = config["output_dir"]
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def main() -> None:
    async with AsyncWebCrawler() as crawler:
        for team in config["teams"]:
            url = team["url"]
            filename = team["filename"]

            result = await crawler.arun(url=url)
            markdown_text = result.markdown

            file_path = os.path.join(OUTPUT_DIR, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_text)

            print(f"✅ Saved: {file_path}")


if __name__ == "__main__":
    asyncio.run(main())
