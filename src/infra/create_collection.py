from loguru import logger
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import CollectionInvalid
from pymongo.operations import SearchIndexModel

from src.configs.settings import Settings


def create_summary_vectors_collection(db: Database) -> None:
    try:
        db.create_collection(settings.mongodb_collection_index)
        logger.info(f"Collection {settings.mongodb_collection_index} created successfully.")
    except CollectionInvalid:
        logger.warning(f"Collection {settings.mongodb_collection_index} already exists. Skipping creation.")


def create_vector_search_index(vector_collection: Collection) -> None:
    search_index_model = SearchIndexModel(
        definition={
            "fields": [
                {
                    "type": "vector",
                    "numDimensions": 1536,  # For OpenAI text-embedding-3-small
                    "path": "embedding",
                    "similarity": "cosine",
                }
            ]
        },
        name=settings.mongodb_collection_index_name,
        type="vectorSearch",
    )

    existing_indexes = vector_collection.list_search_indexes()
    if not any(idx["name"] == settings.mongodb_collection_index_name for idx in existing_indexes):
        vector_collection.create_search_index(model=search_index_model)
        logger.info(f"Vector search index '{settings.mongodb_collection_index_name}' created.")
    else:
        logger.warning(f"Vector search index '{settings.mongodb_collection_index_name}' already exists.")


def main() -> None:
    settings = Settings()
    client: MongoClient = MongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_database]

    create_summary_vectors_collection(db)
    vector_collection = db[settings.mongodb_collection_index]
    create_vector_search_index(vector_collection)


if __name__ == "__main__":
    # Initialize settings
    settings = Settings()

    main()
