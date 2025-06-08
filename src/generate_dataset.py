import json
from typing import Any

from loguru import logger
from openai import OpenAI
from pymongo import MongoClient
from pymongo.mongo_client import MongoClient as MongoClientType

from src.configs.prompts import QUERY_PROMPT
from src.configs.settings import Settings


class MongoVectorSearchClient:
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
        self.mongodb_client.close()


def answer_query_with_context(
    openai_client: Any, vector_client: MongoVectorSearchClient, settings: Settings, query: str, limit: int = 3
) -> str:
    # Get embedding for query
    embedding_response = openai_client.embeddings.create(input=query, model=settings.openai_embedding_model)
    query_vec = embedding_response.data[0].embedding

    # Search in MongoDB vector index
    results = vector_client.vector_search(
        collection_name=settings.mongodb_collection_index,
        index_name=settings.mongodb_collection_index_name,
        attr_name="embedding",
        embedding_vector=query_vec,
        limit=limit,
    )

    # Prepare context for prompt
    context = "\n\n".join([r["summary_text"] for r in results])
    prompt = QUERY_PROMPT.format(context=context, query=query)

    # Get answer from OpenAI chat completion
    response = openai_client.chat.completions.create(
        model=settings.openai_llm_model, messages=[{"role": "user", "content": prompt}]
    )

    answer = response.choices[0].message.content or ""
    return answer


if __name__ == "__main__":
    settings = Settings()
    openai_client = OpenAI(api_key=settings.openai_api_key)
    vector_client = MongoVectorSearchClient(connection_uri=settings.mongodb_uri, db_name=settings.mongodb_database)

    questions = [
        "When was Real Madrid CF founded?",
        "What is the name of Real Madrid's home stadium?",
        "Can you describe the early history of Real Madrid?",
        "Who are some legendary players in Real Madrid's history?",
        "How has Real Madrid performed in recent La Liga seasons (2020-2025)?",
        "What are some of Real Madrid’s recent achievements from 2020 to 2025?",
        "Who is the current manager of Real Madrid?",
        "How many UEFA Champions League titles has Real Madrid won?",
        "What are some of Real Madrid's most significant trophies?",
        "Who are Real Madrid's biggest rivals and what is the significance of their rivalry?",
    ]

    qa_pairs = []
    for q in questions:
        logger.info(f"Generating answer for question: {q}")
        answer = answer_query_with_context(openai_client, vector_client, settings, q)
        qa_pairs.append({"input": q, "expected_output": answer})

    vector_client.close_connection()

    # Save to JSON file
    with open("real_madrid_qa_dataset.json", "w", encoding="utf-8") as f:
        json.dump(qa_pairs, f, indent=2, ensure_ascii=False)

    logger.info("✅ Dataset saved to real_madrid_qa_dataset.json")
