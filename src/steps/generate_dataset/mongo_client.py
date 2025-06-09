from pymongo import MongoClient
from pymongo.mongo_client import MongoClient as MongoClientType


class MongoVectorSearchClient:
    """
    Perform a vector search query on the specified collection.

    Args:
        collection_name (str): Name of the collection to query.
        index_name (str): Name of the vector search index.
        attr_name (str): Document attribute path holding the embedding vector.
        embedding_vector (List[float]): Query embedding vector.
        limit (int, optional): Max number of results to return. Defaults to 3.

    Returns:
        List[Any]: List of matching documents with search scores.
    """

    def __init__(self, connection_uri: str, db_name: str):
        self.mongodb_client: MongoClientType = MongoClient(connection_uri)
        self.database = self.mongodb_client[db_name]

    def vector_search(
        self, collection_name: str, index_name: str, attr_name: str, embedding_vector: list, limit: int = 3
    ) -> list:
        collection = self.database[collection_name]
        results = collection.aggregate(
            [
                {
                    "$vectorSearch": {
                        "index": index_name,
                        "path": attr_name,
                        "queryVector": embedding_vector,
                        "numCandidates": 50,
                        "limit": limit,
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "team": 1,
                        "summary_type": 1,
                        "summary_text": 1,
                        "source_url": 1,
                        "search_score": {"$meta": "vectorSearchScore"},
                    }
                },
            ]
        )
        return list(results)

    def close_connection(self) -> None:
        """Close the MongoDB client connection."""
        self.mongodb_client.close()
