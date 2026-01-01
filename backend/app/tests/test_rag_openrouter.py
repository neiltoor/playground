"""
Unit tests for RAG engine with OpenRouter provider.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch

from app.rag_engine import RAGEngine


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch('app.rag_engine.settings') as mock_settings:
        mock_settings.ANTHROPIC_API_KEY = "test-anthropic-key"
        mock_settings.ANTHROPIC_BASE_URL = "https://openrouter.ai/api/v1"
        mock_settings.ANTHROPIC_DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"
        mock_settings.OPENROUTER_API_KEY = "test-openrouter-key"
        mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
        mock_settings.OPENROUTER_DEFAULT_MODEL = "xai/grok-beta"
        mock_settings.CHUNK_SIZE = 512
        mock_settings.CHUNK_OVERLAP = 50
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost:5432/testdb"
        yield mock_settings


@pytest.fixture
def mock_vector_store():
    """Mock PGVectorStore."""
    with patch('app.rag_engine.PGVectorStore') as mock_pg:
        mock_store = MagicMock()
        mock_pg.from_params.return_value = mock_store
        yield mock_store


@pytest.fixture
def mock_index():
    """Mock VectorStoreIndex."""
    with patch('app.rag_engine.VectorStoreIndex') as mock_idx:
        mock_index_instance = MagicMock()
        mock_idx.from_vector_store.return_value = mock_index_instance
        mock_idx.return_value = mock_index_instance
        yield mock_index_instance


@pytest.fixture
def mock_llm():
    """Mock OpenAILike LLM."""
    with patch('app.rag_engine.OpenAILike') as mock_llm_class:
        mock_llm_instance = MagicMock()
        mock_llm_class.return_value = mock_llm_instance
        yield mock_llm_class


@pytest.fixture
def mock_embeddings():
    """Mock HuggingFace embeddings."""
    with patch('app.rag_engine.HuggingFaceEmbedding') as mock_embed:
        yield mock_embed


@pytest.fixture
def mock_storage_context():
    """Mock StorageContext."""
    with patch('app.rag_engine.StorageContext') as mock_storage:
        mock_context = MagicMock()
        mock_storage.from_defaults.return_value = mock_context
        yield mock_storage


@pytest.fixture
def rag_engine(mock_settings, mock_vector_store, mock_index, mock_llm,
               mock_embeddings, mock_storage_context):
    """Create a RAGEngine instance with mocked dependencies."""
    with patch('app.rag_engine.Settings') as mock_settings_class:
        engine = RAGEngine()
        engine.initialized = True
        engine.index = mock_index
        engine.vector_store = mock_vector_store
        yield engine


class TestRAGEngineOpenRouterProvider:
    """Test suite for RAG engine using OpenRouter provider."""

    def test_query_with_openrouter_provider(self, rag_engine, mock_llm):
        """Test querying with OpenRouter provider."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Test answer from OpenRouter"
        mock_response.source_nodes = []

        # Setup mock query engine
        mock_query_engine = MagicMock()
        mock_query_engine.query.return_value = mock_response
        rag_engine.index.as_query_engine.return_value = mock_query_engine

        # Execute query with OpenRouter provider
        result = rag_engine.query(
            query_text="What is the test query?",
            user_id="test_user",
            top_k=5,
            provider="openrouter",
            model="xai/grok-beta"
        )

        # Verify LLM was created with OpenRouter settings
        mock_llm.assert_called()
        call_kwargs = mock_llm.call_args[1]
        assert call_kwargs['api_base'] == "https://openrouter.ai/api/v1"
        assert call_kwargs['model'] == "xai/grok-beta"
        assert call_kwargs['temperature'] == 0.1
        assert call_kwargs['is_chat_model'] is True

        # Verify result structure
        assert result['answer'] == "Test answer from OpenRouter"
        assert result['query'] == "What is the test query?"
        assert isinstance(result['sources'], list)

    def test_query_openrouter_uses_correct_api_key(self, rag_engine, mock_llm):
        """Test that OpenRouter uses the correct API key."""
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Answer"
        mock_response.source_nodes = []

        mock_query_engine = MagicMock()
        mock_query_engine.query.return_value = mock_response
        rag_engine.index.as_query_engine.return_value = mock_query_engine

        with patch('app.rag_engine.settings') as mock_settings:
            mock_settings.OPENROUTER_API_KEY = "openrouter-specific-key"
            mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

            result = rag_engine.query(
                query_text="Test query",
                user_id="user1",
                provider="openrouter",
                model="xai/grok-beta"
            )

        # Verify the OpenRouter API key was used
        call_kwargs = mock_llm.call_args[1]
        assert call_kwargs['api_key'] == "openrouter-specific-key"

    def test_query_openrouter_no_api_key_raises_error(self, rag_engine):
        """Test that querying OpenRouter without API key raises error."""
        with patch('app.rag_engine.settings') as mock_settings:
            mock_settings.OPENROUTER_API_KEY = ""

            with pytest.raises(RuntimeError, match="OpenRouter API key not configured"):
                rag_engine.query(
                    query_text="Test query",
                    user_id="user1",
                    provider="openrouter",
                    model="xai/grok-beta"
                )

    def test_query_openrouter_with_sources(self, rag_engine, mock_llm):
        """Test OpenRouter query with source documents returned."""
        # Setup mock source nodes
        mock_node1 = MagicMock()
        mock_node1.text = "OpenRouter source 1"
        mock_node1.score = 0.92
        mock_node1.metadata = {
            "filename": "resume1.pdf",
            "document_id": "doc-789",
            "user_id": "test_user"
        }

        mock_node2 = MagicMock()
        mock_node2.text = "OpenRouter source 2"
        mock_node2.score = 0.85
        mock_node2.metadata = {
            "filename": "resume2.pdf",
            "document_id": "doc-012",
            "user_id": "test_user"
        }

        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Comparison based on resumes"
        mock_response.source_nodes = [mock_node1, mock_node2]

        mock_query_engine = MagicMock()
        mock_query_engine.query.return_value = mock_response
        rag_engine.index.as_query_engine.return_value = mock_query_engine

        # Execute query
        result = rag_engine.query(
            query_text="Compare the resumes",
            user_id="test_user",
            provider="openrouter",
            model="xai/grok-beta"
        )

        # Verify sources were extracted correctly
        assert len(result['sources']) == 2
        assert result['sources'][0]['text'] == "OpenRouter source 1"
        assert result['sources'][0]['score'] == 0.92
        assert result['sources'][0]['filename'] == "resume1.pdf"
        assert result['sources'][0]['document_id'] == "doc-789"

        assert result['sources'][1]['text'] == "OpenRouter source 2"
        assert result['sources'][1]['score'] == 0.85

    def test_query_openrouter_with_different_models(self, rag_engine, mock_llm):
        """Test OpenRouter with different model options."""
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Answer"
        mock_response.source_nodes = []

        mock_query_engine = MagicMock()
        mock_query_engine.query.return_value = mock_response
        rag_engine.index.as_query_engine.return_value = mock_query_engine

        # Test with different models
        models_to_test = [
            "xai/grok-beta",
            "google/gemini-pro",
            "meta-llama/llama-3-70b",
            "openai/gpt-4-turbo"
        ]

        for model in models_to_test:
            result = rag_engine.query(
                query_text="Test",
                user_id="user1",
                provider="openrouter",
                model=model
            )

            # Verify the correct model was used
            call_kwargs = mock_llm.call_args[1]
            assert call_kwargs['model'] == model

    def test_query_openrouter_with_custom_top_k(self, rag_engine, mock_llm):
        """Test OpenRouter query with custom top_k value."""
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Answer"
        mock_response.source_nodes = []

        mock_query_engine = MagicMock()
        mock_query_engine.query.return_value = mock_response
        rag_engine.index.as_query_engine.return_value = mock_query_engine

        # Execute query with custom top_k
        result = rag_engine.query(
            query_text="Test query",
            user_id="user1",
            top_k=10,
            provider="openrouter",
            model="xai/grok-beta"
        )

        # Verify top_k was passed correctly
        call_kwargs = rag_engine.index.as_query_engine.call_args[1]
        assert call_kwargs['similarity_top_k'] == 10

    def test_query_openrouter_with_user_filtering(self, rag_engine, mock_llm):
        """Test that user filtering is applied correctly for OpenRouter queries."""
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Answer"
        mock_response.source_nodes = []

        mock_query_engine = MagicMock()
        mock_query_engine.query.return_value = mock_response
        rag_engine.index.as_query_engine.return_value = mock_query_engine

        # Execute query with specific user
        result = rag_engine.query(
            query_text="Test query",
            user_id="user456",
            provider="openrouter",
            model="xai/grok-beta"
        )

        # Verify query engine was created with filters
        call_kwargs = rag_engine.index.as_query_engine.call_args[1]
        assert 'filters' in call_kwargs

        # The filters should allow user's docs OR shared docs
        filters = call_kwargs['filters']
        assert filters.condition == "or"
        assert len(filters.filters) == 2

    def test_query_openrouter_response_mode(self, rag_engine, mock_llm):
        """Test that OpenRouter uses compact response mode."""
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Answer"
        mock_response.source_nodes = []

        mock_query_engine = MagicMock()
        mock_query_engine.query.return_value = mock_response
        rag_engine.index.as_query_engine.return_value = mock_query_engine

        result = rag_engine.query(
            query_text="Test",
            user_id="user1",
            provider="openrouter",
            model="xai/grok-beta"
        )

        # Verify response_mode is compact
        call_kwargs = rag_engine.index.as_query_engine.call_args[1]
        assert call_kwargs['response_mode'] == "compact"

    def test_query_openrouter_llm_parameter_passed(self, rag_engine, mock_llm):
        """Test that custom LLM instance is passed to query engine."""
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Answer"
        mock_response.source_nodes = []

        mock_query_engine = MagicMock()
        mock_query_engine.query.return_value = mock_response
        rag_engine.index.as_query_engine.return_value = mock_query_engine

        result = rag_engine.query(
            query_text="Test",
            user_id="user1",
            provider="openrouter",
            model="xai/grok-beta"
        )

        # Verify LLM was passed to query engine
        call_kwargs = rag_engine.index.as_query_engine.call_args[1]
        assert 'llm' in call_kwargs
        assert call_kwargs['llm'] is not None
