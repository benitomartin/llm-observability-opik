from typing import Any

from loguru import logger
from pymongo import MongoClient
from zenml import step

from src.configs.settings import Settings


@step(enable_cache=False)
def mongo_ingest_step(documents: list[dict[str, Any]]) -> None:
    """
    Insert or update documents in the MongoDB collection.

    Args:
        documents: Output list from `parse_step`, each containing at least
                   `team`, `source_url`, `content`, `timestamp` and `metadata` keys.
    """
    settings = Settings()
    mongodb_uri = settings.mongodb_uri

    if not mongodb_uri:
        raise ValueError("`mongodb_uri` not provided in .env file")

    client: MongoClient = MongoClient(mongodb_uri)
    db = client[settings.mongodb_database]
    collection = db[settings.mongodb_collection]

    try:
        for doc in documents:
            query = {field: doc[field] for field in settings.mongodb_query_fields}
            existing = collection.find_one(query)

            if existing:
                if existing.get("content") != doc["content"]:
                    collection.update_one(query, {"$set": doc})
                    logger.success(f"Updated document for query: {query}")
                else:
                    logger.info(f"No change for query: {query} — skipping update")
            else:
                collection.insert_one(doc)
                logger.success(f"Inserted new document for query: {query}")
    finally:
        client.close()
        logger.info("MongoDB connection closed")
