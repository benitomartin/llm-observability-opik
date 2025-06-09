import time

from loguru import logger
from pymongo import MongoClient
from zenml import step

from src.configs.prompts import SUMMARY_VARIANTS
from src.steps.generate_summaries.helpers import summarize_content


@step(enable_cache=False)
def summarize_step(
    mongodb_uri: str,
    mongodb_database: str,
    mongodb_collection: str,
) -> None:
    """
    Summarize team content documents from a MongoDB collection.
    Updates each document by adding summaries to the 'summaries' field.

    Args:
        mongodb_uri (str): MongoDB connection URI.
        mongodb_database (str): Database name.
        mongodb_collection (str): Collection name containing team content.
    """
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
