import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import check_database_connection
from app.rag_engine import get_rag_engine
from app.models import HealthResponse
from app.api import upload, query, auth, llm_compare


app = FastAPI(
    title="RAG Pipeline API",
    description="Document upload and Q&A using LlamaIndex, pgvector, and Claude",
    version="1.0.0"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        # Validate settings
        settings.validate()
        print("Settings validated successfully")

        # Initialize RAG engine
        rag_engine = get_rag_engine()
        print("RAG engine initialized")

        # Auto-load default document (neiltoor.pdf)
        default_doc_path = Path(settings.UPLOAD_DIR) / "neiltoor.pdf"
        marker_file = Path(settings.UPLOAD_DIR) / ".neiltoor_loaded"

        if default_doc_path.exists() and not marker_file.exists():
            try:
                metadata = {
                    "document_id": "default-neiltoor",
                    "filename": "neiltoor.pdf",
                    "file_type": ".pdf",
                    "is_default": True,
                    "user_id": "SHARED",
                    "is_shared": True
                }
                chunks = rag_engine.ingest_document(str(default_doc_path), metadata)
                marker_file.touch()
                print(f"Auto-loaded default document: neiltoor.pdf ({chunks} chunks)")
            except Exception as e:
                print(f"Warning: Could not auto-load neiltoor.pdf: {e}")
        elif marker_file.exists():
            print("Default document neiltoor.pdf already loaded (skipping)")

    except Exception as e:
        print(f"Error during startup: {e}")
        raise


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    db_connected = check_database_connection()
    api_key_configured = bool(settings.OPENROUTER_API_KEY)

    status = "healthy" if (db_connected and api_key_configured) else "unhealthy"

    return HealthResponse(
        status=status,
        database="connected" if db_connected else "disconnected",
        api_key_configured=api_key_configured,
        message=f"All systems operational (Model: {settings.LLM_MODEL})" if status == "healthy" else "Some systems are down"
    )


# Include routers
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(query.router, prefix="/api", tags=["query"])
app.include_router(llm_compare.router, prefix="/api", tags=["llm-compare"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RAG Pipeline API",
        "docs": "/docs",
        "health": "/api/health"
    }
