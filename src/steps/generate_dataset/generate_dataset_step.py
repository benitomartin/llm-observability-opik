import os
import time
from typing import cast

import openai
from loguru import logger
from pymongo import MongoClient
from zenml import step

from src.configs.settings import Settings  # your existing Settings class

# --- Helper functions -------------------------------------------------------- #


def rough_token_count(text: str) -> int:
    """≈1 token per 0.75 words (very rough)."""
    return int(len(text.split()) / 0.75)


def split_into_chunks(text: str, max_tokens: int = 100_000) -> list[str]:
    """Return chunks small enough for the model."""
    if rough_token_count(text) <= max_tokens:
        return [text]

    words = text.split()
    chunk_len = int(len(words) * max_tokens / rough_token_count(text))
    return [" ".join(words[i : i + chunk_len]) for i in range(0, len(words), chunk_len)]


def openai_chat(
    system_msg: str,
    user_msg: str,
    model: str = "gpt-4o-mini",
    max_tokens: int = 1_500,
    temperature: float = 0.3,
) -> str | None:
    """Small wrapper with error handling."""
    client = openai.OpenAI(
        api_key=Settings().openai_api_key,  # Ensure you have set your OpenAI API key
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return cast(str, resp.choices[0].message.content)
    except Exception as err:
        logger.error(f"OpenAI error: {err}")
        return None


def summarize_content(content: str, team: str) -> str | None:
    """Chunk-aware summarization using OpenAI GPT-4o-mini."""
    chunks = split_into_chunks(content)
    if len(chunks) == 1:
        return openai_chat(
            system_msg="You are an expert sports journalist.",
            user_msg=_FINAL_PROMPT.format(team=team, content=chunks[0]),
        )

    # multi-chunk: summarize each, then combine
    partials: list[str] = []
    for idx, chunk in enumerate(chunks, 1):
        logger.info(f"  ↳ Summarizing chunk {idx}/{len(chunks)} for {team}")
        summary = openai_chat(
            system_msg="You condense football Wikipedia sections.",
            user_msg=f"Summarize the following part about {team}:\n\n{chunk}",
            max_tokens=800,
        )
        if summary:
            partials.append(summary)

    combined = "\n\n".join(partials)
    return openai_chat(
        system_msg="You compile football summaries.",
        user_msg=_COMBINE_PROMPT.format(team=team, parts=combined),
    )


# --- Prompts (kept outside functions for readability) ----------------------- #

_FINAL_PROMPT = """
Create a comprehensive summary of {team} from the following Wikipedia content.

Expected sections:
1. **Overview & History**
2. **Stadium & Facilities**
3. **Major Achievements**
4. **Notable Players & Management**
5. **Recent Performance**
6. **Culture & Rivalries**

Keep it factual, structured, and 600-1000 words.

Content:
{content}
"""

_COMBINE_PROMPT = """
Use the partial summaries about {team} (below) to craft one final summary with the same 6 sections.

{parts}
"""

# --- ZenML step ------------------------------------------------------------- #


@step(enable_cache=False)
def summarize_step(
    mongodb_uri: str, mongodb_database: str, mongodb_collection: str, summaries_dir: str
) -> None:  # Changed from -> None to explicit None type
    """Summarize team content from MongoDB and save to files."""

    output_dir = summaries_dir
    os.makedirs(output_dir, exist_ok=True)

    mongo: MongoClient = MongoClient(mongodb_uri)
    coll = mongo[mongodb_database][mongodb_collection]

    docs = list(coll.find({}, {"_id": 1, "team": 1, "content": 1}))
    logger.info(f"📄 Documents fetched: {len(docs)}")

    rows = []

    for d in docs:
        team = d["team"]
        content = d["content"]

        if not content.strip():
            logger.warning(f"Skipping empty content for {team}")
            continue

        logger.info(f"📝 Summarizing {team} (len={len(content)} chars)")
        summary = summarize_content(content, team)

        if not summary:
            logger.error(f"Failed summarizing {team}")
            continue

        out_path = os.path.join(output_dir, f"{team.lower().replace(' ', '_')}_summary.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(summary)
        logger.success(f"Summary saved → {out_path}")

        rows.append({"instruction": content, "answer": summary})
        coll.update_one({"_id": d["_id"]}, {"$set": {"summary": summary}})
        time.sleep(0.2)

    mongo.close()
