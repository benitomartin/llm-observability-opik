from loguru import logger
from openai import OpenAI
from pymongo import MongoClient
from pymongo.mongo_client import MongoClient as MongoClientType

from src.configs.settings import Settings


def insert_embeddings() -> None:
    """
    Generate OpenAI embeddings and insert into MongoDB,
    skipping duplicates.
    """
    settings = Settings()
    mongodb_uri = settings.mongodb_uri
    openai_api_key = settings.openai_api_key
    if not mongodb_uri or not openai_api_key:
        raise ValueError("MongoDB URI and OpenAI API key must be set in the settings.")

    openai_client = OpenAI(api_key=openai_api_key)

    client: MongoClientType = MongoClient(mongodb_uri)
    db = client[settings.mongodb_database]
    source_collection = db[settings.mongodb_collection]
    vector_collection = db[settings.mongodb_collection_index]

    batch_to_insert = []

    for doc in source_collection.find():
        team = doc["team"]
        summaries = doc.get("summaries", {})

        for summary_type, summary_text in summaries.items():
            if vector_collection.find_one({"team": team, "summary_type": summary_type}):
                logger.warning(f"Skipping existing summary for team '{team}' and type '{summary_type}'.")
                continue

            embedding_response = openai_client.embeddings.create(input=summary_text, model="text-embedding-3-small")
            embedding = embedding_response.data[0].embedding

            new_doc = {
                "team": team,
                "summary_type": summary_type,
                "summary_text": summary_text,
                "embedding": embedding,
                "source_url": doc.get("source_url"),
                "metadata": doc.get("metadata", {}),
                "timestamp": doc.get("timestamp"),
            }

            batch_to_insert.append(new_doc)

    if batch_to_insert:
        vector_collection.insert_many(batch_to_insert)
        logger.info(f"Inserted {len(batch_to_insert)} new documents into the vector collection.")
    else:
        logger.warning("No new documents to insert into the vector collection.")


if __name__ == "__main__":
    # Initialize settings
    settings = Settings()

    insert_embeddings()
