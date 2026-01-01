"""
OpenRouter LLM Service - Microservice wrapper for OpenRouter API calls (xAI Grok)
"""
import os
import httpx
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="OpenRouter LLM Service")

# OpenRouter configuration
API_KEY = os.getenv("OPENROUTER_API_KEY", "")
BASE_URL = "https://openrouter.ai/api/v1"

if not API_KEY:
    print("Warning: OPENROUTER_API_KEY not set")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "x-ai/grok-beta"
    temperature: float = 0.1
    max_tokens: int = 4096


class ChatResponse(BaseModel):
    content: str
    model: str
    usage: Dict[str, Any]


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "openrouter-llm",
        "api_key_configured": bool(API_KEY)
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """
    Handle chat completion requests using OpenRouter API.

    Args:
        request: Chat request with messages and model configuration

    Returns:
        Chat response with generated content
    """
    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter API key not configured"
        )

    try:
        # Prepare request for OpenRouter
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/yourusername/the-pipeline",
            "X-Title": "Resume Comparison Tool"
        }

        payload = {
            "model": request.model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }

        # Call OpenRouter API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        # Extract response
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return ChatResponse(
            content=content,
            model=data.get("model", request.model),
            usage={
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }
        )

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"OpenRouter API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"OpenRouter API error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
