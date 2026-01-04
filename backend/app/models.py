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
    role: str = "user"


class UserInfo(BaseModel):
    """Model for user information."""
    username: str
    role: str = "user"


# Activity Log Models
class ActivityLogEntry(BaseModel):
    """Model for activity log entry."""
    id: int
    username: str
    activity_type: str
    resource_path: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime
    details: Optional[str] = None


class ActivityLogsResponse(BaseModel):
    """Response model for activity logs."""
    logs: List[ActivityLogEntry]
    total: int
    limit: int
    offset: int


class ActivityStatsResponse(BaseModel):
    """Response model for activity statistics."""
    by_type: dict
    last_24_hours: int
    unique_users_today: int


# LLM Comparison Models
class LLMUsage(BaseModel):
    """Token usage information from LLM response."""
    input_tokens: int
    output_tokens: int
    total_tokens: Optional[int] = None


class LLMResult(BaseModel):
    """Single LLM response result."""
    content: str
    model: str
    usage: LLMUsage
    error: Optional[str] = None


class LLMCompareRequest(BaseModel):
    """Request model for LLM comparison."""
    prompt: str = Field(..., min_length=1, description="The prompt to send to both LLMs")
    anthropic_model: Optional[str] = Field("claude-3-haiku-20240307", description="Anthropic model to use")
    openrouter_model: Optional[str] = Field("x-ai/grok-3-mini", description="OpenRouter model to use")


class LLMCompareResponse(BaseModel):
    """Response model for LLM comparison."""
    prompt: str
    anthropic: LLMResult
    openrouter: LLMResult
