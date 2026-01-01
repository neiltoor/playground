import os
from typing import Dict, List
from datetime import datetime
from pathlib import Path

from llama_index.core import VectorStoreIndex, Settings, StorageContext, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.anthropic import Anthropic
from llama_index.readers.file import PyMuPDFReader, DocxReader

from app.config import settings
from app.database import get_database_url


class RAGEngine:
    """RAG engine using LlamaIndex with pgvector and Claude."""

    def __init__(self):
        """Initialize the RAG engine."""
        self.initialized = False
        self.index = None
        self.vector_store = None
        self._initialize()

    def _initialize(self):
        """Initialize LlamaIndex components."""
        try:
            # Configure global LlamaIndex settings
            Settings.llm = Anthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                model="claude-sonnet-4-20250514",
                temperature=0.1
            )

            Settings.embed_model = HuggingFaceEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )

            Settings.node_parser = SentenceSplitter(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP
            )

            # Initialize pgvector store
            self.vector_store = PGVectorStore.from_params(
                database=settings.DATABASE_URL.split("/")[-1],
                host=settings.DATABASE_URL.split("@")[1].split(":")[0],
                password=settings.DATABASE_URL.split(":")[2].split("@")[0],
                port=int(settings.DATABASE_URL.split(":")[-1].split("/")[0]),
                user=settings.DATABASE_URL.split("://")[1].split(":")[0],
                table_name="document_embeddings",
                embed_dim=384  # HuggingFace all-MiniLM-L6-v2 embedding dimension
            )

            # Create storage context
            storage_context = StorageContext.from_defaults(
                vector_store=self.vector_store
            )

            # Create or load index
            try:
                self.index = VectorStoreIndex.from_vector_store(
                    vector_store=self.vector_store,
                    storage_context=storage_context
                )
            except Exception:
                # If index doesn't exist, create an empty one
                self.index = VectorStoreIndex(
                    [],
                    storage_context=storage_context
                )

            self.initialized = True
            print("RAG engine initialized successfully")

        except Exception as e:
            print(f"Error initializing RAG engine: {e}")
            raise

    def ingest_document(self, file_path: str, metadata: Dict) -> int:
        """
        Ingest a document into the RAG system.

        Args:
            file_path: Path to the document file
            metadata: Additional metadata to attach to the document

        Returns:
            Number of chunks created
        """
        if not self.initialized:
            raise RuntimeError("RAG engine not initialized")

        try:
            # Determine file type and use appropriate reader
            file_extension = Path(file_path).suffix.lower()

            if file_extension == '.pdf':
                # Use PyMuPDF for better PDF parsing
                reader = PyMuPDFReader()
                documents = reader.load(file_path)
            elif file_extension in ['.docx', '.doc']:
                # Use DOCX reader
                reader = DocxReader()
                documents = reader.load(file_path)
            else:
                # Fallback to basic text reading
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                documents = [Document(text=text)]

            # Clean documents and add metadata
            cleaned_documents = []
            for doc in documents:
                # Remove NUL characters and other problematic characters
                cleaned_text = doc.text.replace('\x00', '').strip()

                # Skip empty documents
                if not cleaned_text:
                    continue

                # Update metadata
                doc_metadata = doc.metadata.copy() if hasattr(doc, 'metadata') and doc.metadata else {}
                doc_metadata.update(metadata)
                doc_metadata["ingestion_date"] = datetime.utcnow().isoformat()

                # Create new document with cleaned text
                cleaned_doc = Document(
                    text=cleaned_text,
                    metadata=doc_metadata
                )
                cleaned_documents.append(cleaned_doc)

            # Insert into index
            for doc in cleaned_documents:
                self.index.insert(doc)

            # Count chunks (nodes) created
            chunk_count = len(cleaned_documents)

            print(f"Ingested {chunk_count} chunks from {metadata.get('filename', 'unknown')}")
            return chunk_count

        except Exception as e:
            print(f"Error ingesting document: {e}")
            raise

    def query(self, query_text: str, user_id: str, top_k: int = 5) -> Dict:
        """
        Query the RAG system with user-specific filtering.

        Args:
            query_text: The question to ask
            user_id: Current user (only search their docs + shared docs)
            top_k: Number of relevant chunks to retrieve

        Returns:
            Dictionary with answer and sources
        """
        if not self.initialized:
            raise RuntimeError("RAG engine not initialized")

        try:
            # Create metadata filters: user's docs OR shared docs
            from llama_index.core.vector_stores.types import (
                MetadataFilters,
                MetadataFilter,
                FilterOperator,
            )

            filters = MetadataFilters(
                filters=[
                    MetadataFilter(
                        key="user_id",
                        value=user_id,
                        operator=FilterOperator.EQ
                    ),
                    MetadataFilter(
                        key="user_id",
                        value="SHARED",
                        operator=FilterOperator.EQ
                    )
                ],
                condition="or"  # User's docs OR shared docs
            )

            # Create query engine with filters
            query_engine = self.index.as_query_engine(
                similarity_top_k=top_k,
                response_mode="compact",
                filters=filters
            )

            # Execute query
            response = query_engine.query(query_text)

            # Extract sources
            sources = []
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    source = {
                        "text": node.text,
                        "score": node.score if hasattr(node, 'score') else 0.0,
                        "filename": node.metadata.get("filename", "unknown"),
                        "document_id": node.metadata.get("document_id", "unknown")
                    }
                    sources.append(source)

            return {
                "answer": str(response),
                "sources": sources,
                "query": query_text
            }

        except Exception as e:
            print(f"Error querying RAG system: {e}")
            raise

    def get_document_count(self) -> int:
        """Get the total number of documents in the system."""
        try:
            # This is a simplified count - in production you'd query the vector store
            return 0
        except Exception as e:
            print(f"Error getting document count: {e}")
            return 0


# Global RAG engine instance
rag_engine = None


def get_rag_engine() -> RAGEngine:
    """Get or create the global RAG engine instance."""
    global rag_engine
    if rag_engine is None:
        rag_engine = RAGEngine()
    return rag_engine
