import time
from typing import cast

import openai
from loguru import logger
from pymongo import MongoClient
from zenml import step

from src.configs.prompts import SUMMARY_VARIANTS
from src.configs.settings import Settings

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
    client = openai.OpenAI(api_key=Settings().openai_api_key)
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


def summarize_content(content: str, team: str, prompt_template: str, max_tokens: int) -> str | None:
    """Chunk-aware summarization using custom prompt and token limit."""
    chunks = split_into_chunks(content)
    if len(chunks) == 1:
        return openai_chat(
            system_msg="You are an expert sports journalist.",
            user_msg=prompt_template.format(team=team, content=chunks[0]),
            max_tokens=max_tokens,
        )

    # Multi-chunk: summarize each, then combine
    partials: list[str] = []
    for idx, chunk in enumerate(chunks, 1):
        logger.info(f"  ↳ Summarizing chunk {idx}/{len(chunks)} for {team}")
        summary = openai_chat(
            system_msg="You condense football Wikipedia sections.",
            user_msg=f"Summarize the following part about {team}:\n\n{chunk}",
            max_tokens=max_tokens,
        )
        if summary:
            partials.append(summary)

    combined = "\n\n".join(partials)
    return openai_chat(
        system_msg="You compile football summaries.",
        user_msg="Combine the following parts into a cohesive summary:\n\n" + combined,
        max_tokens=max_tokens,
    )


# --- ZenML step ------------------------------------------------------------- #


@step(enable_cache=False)
def summarize_step(
    mongodb_uri: str,
    mongodb_database: str,
    mongodb_collection: str,
) -> None:
    """Summarize team content from MongoDB and store summaries in the 'summaries' field."""

    mongo: MongoClient = MongoClient(mongodb_uri)
    coll = mongo[mongodb_database][mongodb_collection]

    docs = list(coll.find({}, {"_id": 1, "team": 1, "content": 1, "summaries": 1}))
    logger.info(f"📄 Documents fetched: {len(docs)}")

    for d in docs:
        team = d["team"]
        content = d["content"]

        if not content.strip():
            logger.warning(f"⚠️ Skipping empty content for {team}")
            continue

        existing_summaries = d.get("summaries", {})
        all_summaries = existing_summaries.copy()  # Start with current summaries

        for variant, config in SUMMARY_VARIANTS.items():
            existing = existing_summaries.get(variant)
            if existing and existing.strip():
                logger.info(f"✅ Skipping existing summary for {team} [{variant}]")
                continue

            logger.info(f"📝 Summarizing {team} [{variant}] (len={len(content)} chars)")
            summary = summarize_content(content, team, config["prompt"], config["max_tokens"])

            if summary:
                all_summaries[variant] = summary
                time.sleep(0.2)

        # Update MongoDB document if there are any changes
        if all_summaries != existing_summaries:
            coll.update_one({"_id": d["_id"]}, {"$set": {"summaries": all_summaries}})
            logger.info(f"📥 Updated summaries for {team}")

    mongo.close()
