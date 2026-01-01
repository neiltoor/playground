"""
Unit tests for RAG engine with microservices architecture.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from pathlib import Path
import httpx

from app.rag_engine import RAGEngine


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
def rag_engine(mock_vector_store, mock_index, mock_embeddings, mock_storage_context):
    """Create a RAGEngine instance with mocked dependencies."""
    with patch('app.rag_engine.Settings') as mock_settings_class:
        engine = RAGEngine()
        engine.initialized = True
        engine.index = mock_index
        engine.vector_store = mock_vector_store
        return engine


class TestRAGEngineMicroservices:
    """Test RAG engine with microservices architecture."""

    @pytest.mark.asyncio
    async def test_query_with_anthropic_service(self, rag_engine):
        """Test querying with Anthropic microservice."""
        # Mock retriever
        mock_node = MagicMock()
        mock_node.text = "Test document content"
        mock_node.score = 0.9
        mock_node.metadata = {"filename": "test.pdf", "document_id": "doc1"}

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [mock_node]
        rag_engine.index.as_retriever.return_value = mock_retriever

        # Mock httpx AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": "Answer from Anthropic service",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 100, "output_tokens": 50}
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context

            result = await rag_engine.query(
                query_text="Test query",
                user_id="test_user",
                top_k=5,
                provider="anthropic",
                model="claude-3-5-sonnet-20241022"
            )

        assert result["answer"] == "Answer from Anthropic service"
        assert len(result["sources"]) == 1
        assert result["sources"][0]["filename"] == "test.pdf"
        assert result["query"] == "Test query"

    @pytest.mark.asyncio
    async def test_query_with_openrouter_service(self, rag_engine):
        """Test querying with OpenRouter microservice."""
        # Mock retriever
        mock_node = MagicMock()
        mock_node.text = "Test document content"
        mock_node.score = 0.85
        mock_node.metadata = {"filename": "test2.pdf", "document_id": "doc2"}

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [mock_node]
        rag_engine.index.as_retriever.return_value = mock_retriever

        # Mock httpx AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": "Answer from OpenRouter service",
            "model": "x-ai/grok-beta",
            "usage": {"input_tokens": 120, "output_tokens": 60}
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context

            result = await rag_engine.query(
                query_text="Another test query",
                user_id="test_user2",
                top_k=3,
                provider="openrouter",
                model="x-ai/grok-beta"
            )

        assert result["answer"] == "Answer from OpenRouter service"
        assert len(result["sources"]) == 1
        assert result["sources"][0]["filename"] == "test2.pdf"
        assert result["query"] == "Another test query"

    @pytest.mark.asyncio
    async def test_query_with_multiple_sources(self, rag_engine):
        """Test querying with multiple document sources."""
        # Mock retriever with multiple nodes
        mock_nodes = []
        for i in range(3):
            node = MagicMock()
            node.text = f"Document {i} content"
            node.score = 0.9 - (i * 0.1)
            node.metadata = {"filename": f"doc{i}.pdf", "document_id": f"id{i}"}
            mock_nodes.append(node)

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = mock_nodes
        rag_engine.index.as_retriever.return_value = mock_retriever

        # Mock httpx AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": "Synthesized answer from multiple docs",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 200, "output_tokens": 100}
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context

            result = await rag_engine.query(
                query_text="Query multiple docs",
                user_id="user1",
                top_k=3,
                provider="anthropic"
            )

        assert len(result["sources"]) == 3
        assert result["sources"][0]["score"] == 0.9
        assert result["sources"][1]["score"] == 0.8
        assert result["sources"][2]["score"] == 0.7

    @pytest.mark.asyncio
    async def test_query_invalid_provider_raises_error(self, rag_engine):
        """Test that invalid provider raises ValueError."""
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        rag_engine.index.as_retriever.return_value = mock_retriever

        with pytest.raises(ValueError, match="Unknown provider"):
            await rag_engine.query(
                query_text="Test",
                user_id="user1",
                provider="invalid_provider"
            )

    @pytest.mark.asyncio
    async def test_query_http_error_raises_runtime_error(self, rag_engine):
        """Test that HTTP errors are properly handled."""
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [MagicMock()]
        rag_engine.index.as_retriever.return_value = mock_retriever

        with patch('httpx.AsyncClient') as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPError("Service unavailable")
            )
            mock_client.return_value = mock_context

            with pytest.raises(RuntimeError, match="LLM service error"):
                await rag_engine.query(
                    query_text="Test",
                    user_id="user1",
                    provider="anthropic"
                )

    @pytest.mark.asyncio
    async def test_query_calls_correct_service_url(self, rag_engine):
        """Test that the correct service URL is called for each provider."""
        mock_node = MagicMock()
        mock_node.text = "Content"
        mock_node.score = 0.9
        mock_node.metadata = {"filename": "test.pdf", "document_id": "doc1"}

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [mock_node]
        rag_engine.index.as_retriever.return_value = mock_retriever

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": "Test answer",
            "model": "test-model",
            "usage": {}
        }
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = mock_post
            mock_client.return_value = mock_context

            # Test Anthropic service
            await rag_engine.query(
                query_text="Test",
                user_id="user1",
                provider="anthropic"
            )

            # Verify Anthropic URL was called
            call_args = mock_post.call_args
            assert call_args[0][0] == "http://anthropic-service:8001/chat"

            # Test OpenRouter service
            mock_post.reset_mock()
            await rag_engine.query(
                query_text="Test",
                user_id="user1",
                provider="openrouter"
            )

            # Verify OpenRouter URL was called
            call_args = mock_post.call_args
            assert call_args[0][0] == "http://openrouter-service:8002/chat"
