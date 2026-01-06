import os
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import check_database_connection
from app.rag_engine import get_rag_engine
from app.models import HealthResponse
from app.api import upload, query, auth, llm_compare, activity
from app.middleware.activity_logger import ActivityLoggerMiddleware

CONFIG_FILE_PATH = "/data/config.json"


def _load_cors_origins() -> list:
    """Load CORS origins from config file, env var, or use defaults."""
    # 1. Try config file first
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config = json.load(f)
            if config.get("cors_origins"):
                print(f"Loaded CORS origins from /data/config.json: {config['cors_origins']}")
                return config["cors_origins"]
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        pass

    # 2. Try environment variable
    cors_env = os.getenv("CORS_ORIGINS", "")
    if cors_env:
        origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
        print(f"Loaded CORS origins from CORS_ORIGINS env var: {origins}")
        return origins

    # 3. Default to localhost
    print("WARNING: CORS origins not configured. Defaulting to localhost only.")
    return ["https://localhost:8443", "https://127.0.0.1:8443"]


app = FastAPI(
    title="RAG Pipeline API",
    description="Document upload and Q&A using LlamaIndex, pgvector, and Claude",
    version="1.0.0"
)

CORS_ORIGINS = _load_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Activity logging middleware
app.add_middleware(ActivityLoggerMiddleware)


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
app.include_router(activity.router, prefix="/api", tags=["activity"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RAG Pipeline API",
        "docs": "/docs",
        "health": "/api/health"
    }
