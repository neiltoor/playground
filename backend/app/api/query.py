from fastapi import APIRouter, HTTPException

from app.models import QueryRequest, QueryResponse, SourceInfo
from app.rag_engine import get_rag_engine


router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Query the RAG system with a question.

    Args:
        request: Query request with question and optional top_k

    Returns:
        Query response with answer and sources
    """
    try:
        # Get RAG engine
        rag_engine = get_rag_engine()

        # Execute query
        result = rag_engine.query(
            query_text=request.query,
            top_k=request.top_k
        )

        # Convert sources to SourceInfo models
        sources = [
            SourceInfo(
                text=source["text"],
                score=source["score"],
                filename=source.get("filename"),
                document_id=source.get("document_id")
            )
            for source in result["sources"]
        ]

        return QueryResponse(
            answer=result["answer"],
            sources=sources,
            query=result["query"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error querying documents: {str(e)}"
        )
