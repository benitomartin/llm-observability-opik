import os
import re
import time
from datetime import UTC, datetime

import requests
from bs4 import BeautifulSoup, Tag
from loguru import logger
from zenml import step

from src.configs.settings import CrawledDoc, YamlConfig


def get_wikipedia_toc(page_title: str) -> list | None:
    """Get table of contents for a Wikipedia page using the MediaWiki API."""
    url = "https://en.wikipedia.org/w/api.php"
    params = {"action": "parse", "format": "json", "prop": "sections", "page": page_title, "redirects": "true"}

    logger.info(f"Requesting TOC for Wikipedia page: '{page_title}'")

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if "parse" in data and "sections" in data["parse"]:
            logger.success(f"Retrieved {len(data['parse']['sections'])} sections from '{page_title}'")
            return list(data["parse"]["sections"])
        else:
            logger.warning(f"No 'sections' found for page '{page_title}'")
            return None

    except requests.exceptions.RequestException as req_err:
        logger.error(f"HTTP error while fetching TOC for '{page_title}': {req_err}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error while getting TOC for '{page_title}': {e}")
        return None


def get_clean_section_content(page_title: str, section_index: str) -> str | None:
    """
    Fetch a single Wikipedia section, strip unwanted markup, hyperlinks
    and references, then return clean text.

    Args:
        page_title:   The Wikipedia page slug, e.g. "Real_Madrid_CF"
        section_index: Section index string as returned by the
                       MediaWiki `prop=sections` API (e.g. "15")

    Returns:
        Cleaned plain-text string, or None on failure.
    """
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "parse",
        "format": "json",
        "prop": "text",
        "page": page_title,
        "section": section_index,
        "redirects": "true",
    }

    # logger.debug(f"Requesting section {section_index} of '{page_title}'")

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if "parse" not in data or "text" not in data["parse"]:
            logger.warning(f"No text found for {page_title} section {section_index}")
            return None

        html = data["parse"]["text"]["*"]
        soup = BeautifulSoup(html, "html.parser")

        # Remove <script> / <style> blocks
        for tag in soup(["script", "style"]):
            tag.decompose()

        # Remove citation superscripts <sup class="reference">[1]</sup>
        for ref in soup.select("sup.reference"):
            ref.decompose()

        # Unwrap hyperlinks but keep their visible text
        for a in soup.find_all("a"):
            if isinstance(a, Tag):
                a.unwrap()

        # Extract plain text
        text = soup.get_text(separator=" ").strip()

        # Collapse multiple whitespace
        text = re.sub(r"\s{2,}", " ", text)

        # logger.success(f"✓ Cleaned section {section_index} of '{page_title}' "
        #                f"({len(text)} chars)")
        return text

    except requests.exceptions.RequestException as http_err:
        logger.error(f"HTTP error for {page_title} sec {section_index}: {http_err}")
    except (KeyError, ValueError) as parse_err:
        logger.error(f"Parse error for {page_title} sec {section_index}: {parse_err}")
    except Exception as e:
        logger.exception(f"Unexpected error on {page_title} sec {section_index}: {e}")

    return None


def extract_wikipedia_page(page_title: str, out_path: str, sleep: float = 0.3) -> str | None:
    """Download the whole article, write to disk, return content."""
    sections = get_wikipedia_toc(page_title)
    if not sections:
        return None

    content_lines: list[str] = [
        f"WIKIPEDIA ARTICLE: {page_title}",
        "=" * 80,
        "",
        "TABLE OF CONTENTS",
        "-" * 40,
    ]

    # build TOC
    for sec in sections:
        indent = "  " * (int(sec["level"]) - 1)
        content_lines.append(f"{indent}{sec.get('number', '')} {sec['line']}")

    content_lines += ["", "FULL CONTENT", "=" * 80, ""]

    # fetch each section
    for _, sec in enumerate(sections, start=1):
        header_marker = "#" * int(sec["level"])
        content_lines.append(f"{header_marker} {sec['line']}\n")

        section_text = get_clean_section_content(page_title, sec["index"])
        content_lines.append(section_text or "[No content available]")
        content_lines += ["", "-" * 60, ""]
        time.sleep(sleep)

    full_text = "\n".join(content_lines)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    logger.success(f"Saved → {out_path}  ({len(full_text)} chars)")
    return full_text


# ------------------------ ZenML Step ------------------------- #


@step(enable_cache=True)
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
