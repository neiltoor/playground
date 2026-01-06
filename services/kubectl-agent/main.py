"""
kubectl-agent-service: Agent orchestrator for kubectl operations.
Coordinates between Claude (via anthropic-service) and kubectl-service.
"""

import os
import json
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent import run_agent, run_agent_streaming, clear_conversation


app = FastAPI(
    title="Kubectl Agent Service",
    description="AI-powered Kubernetes assistant using Claude and kubectl",
    version="1.0.0"
)

# CORS for direct access (though typically proxied via nginx)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    """Request to chat with the kubectl agent."""
    message: str = Field(..., min_length=1, description="User's natural language message")
    conversation_id: Optional[str] = Field(None, description="ID to continue existing conversation")


class ChatResponse(BaseModel):
    """Response from the kubectl agent."""
    conversation_id: str
    response: str
    commands_executed: List[str] = []
    error: bool = False


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    anthropic_service_url: str
    kubectl_service_url: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="kubectl-agent",
        anthropic_service_url=os.getenv("ANTHROPIC_SERVICE_URL", "http://anthropic-service:8001"),
        kubectl_service_url=os.getenv("KUBECTL_SERVICE_URL", "http://kubectl-service:8003")
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the kubectl agent.

    Send a natural language message and receive a response.
    The agent will execute kubectl commands as needed to answer your question.
    """
    try:
        result = await run_agent(
            user_message=request.message,
            conversation_id=request.conversation_id
        )

        return ChatResponse(
            conversation_id=result["conversation_id"],
            response=result["response"],
            commands_executed=result.get("commands_executed", []),
            error=result.get("error", False)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Chat with the kubectl agent using Server-Sent Events for streaming.

    Events sent:
    - thinking: Agent is processing
    - executing: Running a command
    - result: Command result
    - response: Final response
    - error: Error occurred
    """
    async def event_generator():
        try:
            async for event in run_agent_streaming(
                user_message=request.message,
                conversation_id=request.conversation_id
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Clear a conversation from memory."""
    success = clear_conversation(conversation_id)
    if success:
        return {"status": "deleted", "conversation_id": conversation_id}
    else:
        raise HTTPException(status_code=404, detail="Conversation not found")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "kubectl-agent",
        "description": "AI-powered Kubernetes assistant",
        "endpoints": {
            "/health": "Health check",
            "/chat": "Chat with the agent (POST)",
            "/conversation/{id}": "Delete conversation (DELETE)"
        }
    }
