"""
Anthropic LLM Service - Microservice wrapper for Anthropic API calls
"""
import os
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from anthropic import Anthropic

app = FastAPI(title="Anthropic LLM Service")

# Load configuration from file or environment
def load_config():
    config_path = "/data/config.json"
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config['llm_providers']['anthropic']['api_key']
    return os.getenv("ANTHROPIC_API_KEY", "")

API_KEY = load_config()
if not API_KEY:
    print("Warning: ANTHROPIC_API_KEY not set in config or environment")

client = Anthropic(api_key=API_KEY) if API_KEY else None


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.1
    max_tokens: int = 4096
    system: Optional[str] = None


class ChatResponse(BaseModel):
    content: str
    model: str
    usage: Dict[str, Any]


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "anthropic-llm",
        "api_key_configured": bool(API_KEY)
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """
    Handle chat completion requests using Anthropic API.

    Args:
        request: Chat request with messages and model configuration

    Returns:
        Chat response with generated content
    """
    if not client:
        raise HTTPException(
            status_code=503,
            detail="Anthropic API key not configured"
        )

    try:
        # Convert messages to Anthropic format
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        # Build API call parameters
        api_params = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages
        }

        # Add system prompt if provided
        if request.system:
            api_params["system"] = request.system

        # Call Anthropic API
        response = client.messages.create(**api_params)

        # Extract response content
        content = response.content[0].text if response.content else ""

        return ChatResponse(
            content=content,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Anthropic API error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
