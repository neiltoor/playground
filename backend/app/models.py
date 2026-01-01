from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response model for document upload."""
    document_id: str
    filename: str
    status: str
    chunks_created: int
    message: str


class DocumentInfo(BaseModel):
    """Model for document information."""
    id: str
    filename: str
    upload_date: datetime
    chunk_count: int
    is_shared: bool = False


class QueryRequest(BaseModel):
    """Request model for RAG query."""
    query: str = Field(..., min_length=1, description="The question to ask")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Number of relevant chunks to retrieve")
    provider: Optional[str] = Field("anthropic", description="LLM provider: 'openrouter' or 'anthropic'")
    model: Optional[str] = Field("claude-3-haiku-20240307", description="LLM model to use")


class SourceInfo(BaseModel):
    """Model for source information in query response."""
    text: str
    score: float
    filename: Optional[str] = None
    document_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for RAG query."""
    answer: str
    sources: List[SourceInfo]
    query: str


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    database: str
    api_key_configured: bool
    message: Optional[str] = None


class LoginRequest(BaseModel):
    """Request model for user login."""
    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")


class LoginResponse(BaseModel):
    """Response model for successful login."""
    access_token: str
    token_type: str = "bearer"
    username: str


class UserInfo(BaseModel):
    """Model for user information."""
    username: str
