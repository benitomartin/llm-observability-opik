from typing import Any

from src.configs.prompts import QUERY_PROMPT
from src.configs.settings import Settings
from src.infra.mongo_search_client import MongoVectorSearchClient

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


def answer_query_with_context(
    openai_client: Any, vector_client: MongoVectorSearchClient, settings: Settings, query: str, limit: int = 3
) -> str:
    # Get embedding for query
    embedding_response = openai_client.embeddings.create(input=query, model=settings.openai_embedding_model)
    query_vec = embedding_response.data[0].embedding

    # Vector search in MongoDB
    results = vector_client.vector_search(
        collection_name=settings.mongodb_collection_index,
        index_name=settings.mongodb_collection_index_name,
        attr_name="embedding",
        embedding_vector=query_vec,
        limit=limit,
    )

    # Build prompt context
    context = "\n\n".join([r["summary_text"] for r in results])
    prompt = QUERY_PROMPT.format(context=context, query=query)

    # Get LLM response
    response = openai_client.chat.completions.create(
        model=settings.openai_llm_judge_model, messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content or ""
