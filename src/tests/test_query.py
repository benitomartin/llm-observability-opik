from unittest.mock import MagicMock, patch

import pytest

from src.configs.settings import Settings
from src.search.search_tracing_opik import answer_query_with_context


@pytest.fixture
def fake_embedding_response() -> MagicMock:
    """Mock response for OpenAI embeddings.create()."""
    mock = MagicMock()
    mock.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
    return mock


@pytest.fixture
def fake_chat_response() -> MagicMock:
    """Mock response for OpenAI chat.completions.create()."""
    mock = MagicMock()
    mock.choices = [MagicMock(message=MagicMock(content="This is a test answer."))]
    return mock


@patch("src.search.search_tracing_opik.OpenAI")
@patch("src.search.search_tracing_opik.Settings", autospec=True)
def test_answer_query_with_context(
    mock_settings_cls: MagicMock,
    mock_openai_cls: MagicMock,
    fake_embedding_response: MagicMock,
    fake_chat_response: MagicMock,
) -> None:
    # Configure Settings mock
    mock_settings = MagicMock(spec=Settings)
    mock_settings.openai_api_key = "fake_api_key"
    mock_settings.mongodb_uri = "mongodb://fake_uri"
    mock_settings.mongodb_database = "test_db"
    mock_settings.mongodb_collection_index = "test_collection"
    mock_settings.mongodb_collection_index_name = "test_index"
    mock_settings.openai_embedding_model = "fake-embedding-model"
    mock_settings.openai_llm_model = "fake-llm-model"
    mock_settings_cls.return_value = mock_settings

    # Configure mocked OpenAI client
    mock_openai = MagicMock()
    mock_openai.embeddings.create.return_value = fake_embedding_response
    mock_openai.chat.completions.create.return_value = fake_chat_response
    mock_openai_cls.return_value = mock_openai

    # Fake MongoDB vector search results
    fake_results = [
        {
            "_id": "123",
            "team": "Atlético Madrid",
            "summary_type": "season_summary",
            "summary_text": "Atlético Madrid won La Liga in 2021.",
            "source_url": "http://example.com",
            "search_score": 0.98,
        }
    ]

    with patch("src.search.search_tracing_opik.MongoVectorSearchClient") as mock_client_cls:
        mock_client_instance = mock_client_cls.return_value
        mock_client_instance.vector_search.return_value = fake_results
        mock_client_instance.close_connection.return_value = None

        # Execute the function under test
        query = "When did Atlético Madrid last win La Liga?"
        answer = answer_query_with_context(query, limit=3)

    # Assertions
    assert "test answer" in answer.lower()

    # Verify OpenAI embeddings was called correctly
    mock_openai.embeddings.create.assert_called_once_with(model="fake-embedding-model", input=query)

    # Verify chat completion was called
    mock_openai.chat.completions.create.assert_called_once()

    # Verify vector search was called with correct parameters
    mock_client_instance.vector_search.assert_called_once_with(
        collection_name="test_collection",
        index_name="test_index",
        attr_name="embedding",
        embedding_vector=[0.1, 0.2, 0.3],
        limit=3,
    )

    # Verify connection cleanup
    mock_client_instance.close_connection.assert_called_once()
