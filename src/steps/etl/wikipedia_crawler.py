import os
import re
import time

import requests
from bs4 import BeautifulSoup, Tag
from loguru import logger


def get_wikipedia_toc(page_title: str) -> list | None:
    """
    Fetch the Table of Contents (TOC) for a given Wikipedia page using the MediaWiki API.

    Args:
        page_title (str): The title (slug) of the Wikipedia page, e.g. "Real_Madrid_CF".

    Returns:
        list | None: A list of sections with metadata if successful, None if the page or sections are not found or on error.
    """
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
    Fetch a specific section of a Wikipedia page, clean its HTML content by removing scripts,
    styles, references, and hyperlinks, then return plain text.

    Args:
        page_title (str): Wikipedia page slug, e.g. "Real_Madrid_CF".
        section_index (str): Section index identifier as returned by the MediaWiki API, e.g. "15".

    Returns:
        str | None: Clean plain-text content of the section or None if fetching/parsing fails.
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
    """
    Extract the full content of a Wikipedia page, including its TOC and all sections,
    clean the text content, and save the combined output to a file.

    Args:
        page_title (str): Wikipedia page slug to extract.
        out_path (str): Path to save the extracted text file.
        sleep (float): Delay in seconds between fetching individual sections to avoid API rate limits.

    Returns:
        str | None: The full extracted text content if successful, None otherwise.
    """
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
