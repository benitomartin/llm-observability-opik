import opik
from loguru import logger
from openai import OpenAI
from opik.integrations.openai import track_openai

from src.configs.prompts import QUERY_PROMPT
from src.configs.settings import Settings
from src.infra.mongo_search_client import MongoVectorSearchClient


@opik.track(name="get_embedding")
def get_query_embedding(query: str, client: OpenAI, model: str) -> list:
    """Extract embedding generation into a separate tracked function."""
    embedding_response = client.embeddings.create(input=query, model=model)
    return embedding_response.data[0].embedding


@opik.track(name="prepare_context")
def prepare_context_from_results(results: list) -> str:
    """Extract context preparation into a separate tracked function."""
    context = "\n\n".join([r["summary_text"] for r in results])
    return context


@opik.track(name="generate_answer")
def generate_answer(prompt: str, client: OpenAI, model: str) -> str:
    """Extract answer generation into a separate tracked function."""
    response = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
    return response.choices[0].message.content or ""


@opik.track(name="rag_query_pipeline")
def answer_query_with_context(query: str, limit: int = 3) -> str:
    """Main RAG pipeline with comprehensive Opik tracing."""
    settings = Settings()

    # Initialize OpenAI client with Opik tracking
    openai_client = OpenAI(api_key=settings.openai_api_key)
    openai_client = track_openai(openai_client)

    vector_client = MongoVectorSearchClient(connection_uri=settings.mongodb_uri, db_name=settings.mongodb_database)

    try:
        # Get embedding for query (tracked)
        query_vec = get_query_embedding(query, openai_client, settings.openai_embedding_model)

        # Search in MongoDB vector index (tracked)
        results = vector_client.vector_search(
            collection_name=settings.mongodb_collection_index,
            index_name=settings.mongodb_collection_index_name,
            attr_name="embedding",
            embedding_vector=query_vec,
            limit=limit,
        )

        # Prepare context for prompt (tracked)
        context = prepare_context_from_results(results)

        # Create the final prompt
        prompt = QUERY_PROMPT.format(context=context, query=query)

        # Get answer from OpenAI chat completion (tracked)
        answer = generate_answer(prompt, openai_client, settings.openai_llm_model)

        return answer

    finally:
        vector_client.close_connection()


if __name__ == "__main__":
    q = "When did Atlético Madrid last win La Liga?"
    answer = answer_query_with_context(q)
    logger.info(f"Answer: {answer}")
