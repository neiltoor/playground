from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import check_database_connection
from app.rag_engine import get_rag_engine
from app.models import HealthResponse
from app.api import upload, query


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
        get_rag_engine()
        print("RAG engine initialized")

    except Exception as e:
        print(f"Error during startup: {e}")
        raise


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    db_connected = check_database_connection()
    api_key_configured = bool(settings.ANTHROPIC_API_KEY)

    status = "healthy" if (db_connected and api_key_configured) else "unhealthy"

    return HealthResponse(
        status=status,
        database="connected" if db_connected else "disconnected",
        api_key_configured=api_key_configured,
        message="All systems operational" if status == "healthy" else "Some systems are down"
    )


# Include routers
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(query.router, prefix="/api", tags=["query"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RAG Pipeline API",
        "docs": "/docs",
        "health": "/api/health"
    }
