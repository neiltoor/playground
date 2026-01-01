from fastapi import APIRouter, HTTPException, Depends

from app.models import QueryRequest, QueryResponse, SourceInfo
from app.rag_engine import get_rag_engine
from app.auth import get_current_user


router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    username: str = Depends(get_current_user)
):
    """
    Query the RAG system with user-specific filtering.

    User can only query their own documents + shared documents.

    Args:
        request: Query request with question and optional top_k
        username: Current authenticated user

    Returns:
        Query response with answer and sources
    """
    try:
        # Get RAG engine
        rag_engine = get_rag_engine()

        # Execute query with user filtering and selected LLM provider/model
        result = rag_engine.query(
            query_text=request.query,
            user_id=username,
            top_k=request.top_k,
            provider=request.provider,
            model=request.model
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
