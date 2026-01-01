"""
Unit tests for RAG engine with Anthropic provider.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from app.rag_engine import RAGEngine
from app.config import settings


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


class TestRAGEngineAnthropicProvider:
    """Test suite for RAG engine using Anthropic provider."""

    def test_query_with_anthropic_provider(self, rag_engine, mock_llm):
        """Test querying with Anthropic provider."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Test answer from Anthropic"
        mock_response.source_nodes = []

        # Setup mock query engine
        mock_query_engine = MagicMock()
        mock_query_engine.query.return_value = mock_response
        rag_engine.index.as_query_engine.return_value = mock_query_engine

        # Execute query with Anthropic provider
        result = rag_engine.query(
            query_text="What is the test query?",
            user_id="test_user",
            top_k=5,
            provider="anthropic",
            model="anthropic/claude-3.5-sonnet"
        )

        # Verify LLM was created with Anthropic settings
        mock_llm.assert_called()
        call_kwargs = mock_llm.call_args[1]
        assert call_kwargs['api_base'] == "https://openrouter.ai/api/v1"
        assert call_kwargs['model'] == "anthropic/claude-3.5-sonnet"
        assert call_kwargs['temperature'] == 0.1
        assert call_kwargs['is_chat_model'] is True

        # Verify query engine was created with correct filters
        rag_engine.index.as_query_engine.assert_called_once()

        # Verify result structure
        assert result['answer'] == "Test answer from Anthropic"
        assert result['query'] == "What is the test query?"
        assert isinstance(result['sources'], list)

    def test_query_anthropic_with_api_key_from_settings(self, rag_engine, mock_llm):
        """Test that Anthropic uses correct API key from settings."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Answer"
        mock_response.source_nodes = []

        mock_query_engine = MagicMock()
        mock_query_engine.query.return_value = mock_response
        rag_engine.index.as_query_engine.return_value = mock_query_engine

        # Patch settings to have specific keys
        with patch('app.rag_engine.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "anthropic-specific-key"
            mock_settings.ANTHROPIC_BASE_URL = "https://openrouter.ai/api/v1"
            mock_settings.OPENROUTER_API_KEY = "openrouter-key"

            result = rag_engine.query(
                query_text="Test query",
                user_id="user1",
                provider="anthropic",
                model="anthropic/claude-3.5-sonnet"
            )

        # Verify the Anthropic API key was used
        call_kwargs = mock_llm.call_args[1]
        assert call_kwargs['api_key'] == "anthropic-specific-key"

    def test_query_anthropic_fallback_to_openrouter_key(self, rag_engine, mock_llm):
        """Test that Anthropic falls back to OpenRouter key if no dedicated key."""
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Answer"
        mock_response.source_nodes = []

        mock_query_engine = MagicMock()
        mock_query_engine.query.return_value = mock_response
        rag_engine.index.as_query_engine.return_value = mock_query_engine

        with patch('app.rag_engine.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = ""  # No Anthropic key
            mock_settings.OPENROUTER_API_KEY = "openrouter-fallback-key"
            mock_settings.ANTHROPIC_BASE_URL = "https://openrouter.ai/api/v1"

            result = rag_engine.query(
                query_text="Test query",
                user_id="user1",
                provider="anthropic",
                model="anthropic/claude-3.5-sonnet"
            )

        # Verify OpenRouter key was used as fallback
        call_kwargs = mock_llm.call_args[1]
        assert call_kwargs['api_key'] == "openrouter-fallback-key"

    def test_query_anthropic_no_api_key_raises_error(self, rag_engine):
        """Test that querying Anthropic without API key raises error."""
        with patch('app.rag_engine.settings') as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.OPENROUTER_API_KEY = ""

            with pytest.raises(RuntimeError, match="No API key configured"):
                rag_engine.query(
                    query_text="Test query",
                    user_id="user1",
                    provider="anthropic",
                    model="anthropic/claude-3.5-sonnet"
                )

    def test_query_anthropic_with_sources(self, rag_engine, mock_llm):
        """Test Anthropic query with source documents returned."""
        # Setup mock source nodes
        mock_node1 = MagicMock()
        mock_node1.text = "Source text 1"
        mock_node1.score = 0.95
        mock_node1.metadata = {
            "filename": "doc1.pdf",
            "document_id": "doc-123",
            "user_id": "test_user"
        }

        mock_node2 = MagicMock()
        mock_node2.text = "Source text 2"
        mock_node2.score = 0.87
        mock_node2.metadata = {
            "filename": "doc2.pdf",
            "document_id": "doc-456",
            "user_id": "test_user"
        }

        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Answer based on sources"
        mock_response.source_nodes = [mock_node1, mock_node2]

        mock_query_engine = MagicMock()
        mock_query_engine.query.return_value = mock_response
        rag_engine.index.as_query_engine.return_value = mock_query_engine

        # Execute query
        result = rag_engine.query(
            query_text="What do the documents say?",
            user_id="test_user",
            provider="anthropic",
            model="anthropic/claude-3.5-sonnet"
        )

        # Verify sources were extracted correctly
        assert len(result['sources']) == 2
        assert result['sources'][0]['text'] == "Source text 1"
        assert result['sources'][0]['score'] == 0.95
        assert result['sources'][0]['filename'] == "doc1.pdf"
        assert result['sources'][0]['document_id'] == "doc-123"

        assert result['sources'][1]['text'] == "Source text 2"
        assert result['sources'][1]['score'] == 0.87
        assert result['sources'][1]['filename'] == "doc2.pdf"

    def test_query_anthropic_with_custom_model(self, rag_engine, mock_llm):
        """Test Anthropic with different model versions."""
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Answer"
        mock_response.source_nodes = []

        mock_query_engine = MagicMock()
        mock_query_engine.query.return_value = mock_response
        rag_engine.index.as_query_engine.return_value = mock_query_engine

        # Test with Claude Opus
        result = rag_engine.query(
            query_text="Test",
            user_id="user1",
            provider="anthropic",
            model="anthropic/claude-opus-4"
        )

        # Verify the custom model was used
        call_kwargs = mock_llm.call_args[1]
        assert call_kwargs['model'] == "anthropic/claude-opus-4"

    def test_query_anthropic_with_user_filtering(self, rag_engine, mock_llm):
        """Test that user filtering is applied correctly for Anthropic queries."""
        from llama_index.core.vector_stores.types import MetadataFilters, MetadataFilter

        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Answer"
        mock_response.source_nodes = []

        mock_query_engine = MagicMock()
        mock_query_engine.query.return_value = mock_response
        rag_engine.index.as_query_engine.return_value = mock_query_engine

        # Execute query
        result = rag_engine.query(
            query_text="Test query",
            user_id="user123",
            provider="anthropic",
            model="anthropic/claude-3.5-sonnet"
        )

        # Verify query engine was created with filters
        call_kwargs = rag_engine.index.as_query_engine.call_args[1]
        assert 'filters' in call_kwargs

        # The filters should allow user's docs OR shared docs
        filters = call_kwargs['filters']
        assert filters.condition == "or"
        assert len(filters.filters) == 2
