"""
LLM Comparison API endpoint.
Sends prompts to both Anthropic and OpenRouter services and returns side-by-side results.
"""
import asyncio
from typing import Tuple

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.models import LLMCompareRequest, LLMCompareResponse, LLMResult, LLMUsage


router = APIRouter()

# Service URLs (internal Docker network)
ANTHROPIC_SERVICE_URL = "http://anthropic-service:8001"
OPENROUTER_SERVICE_URL = "http://openrouter-service:8002"


async def call_llm_service(
    service_url: str,
    prompt: str,
    model: str,
    service_name: str
) -> LLMResult:
    """
    Call an LLM service and return the result.

    Args:
        service_url: Base URL of the LLM service
        prompt: The prompt to send
        model: Model identifier to use
        service_name: Name for error messages ('anthropic' or 'openrouter')

    Returns:
        LLMResult with response content and usage stats
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{service_url}/chat",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "model": model,
                    "temperature": 0.1,
                    "max_tokens": 4096
                }
            )

            if response.status_code == 503:
                return LLMResult(
                    content="",
                    model=model,
                    usage=LLMUsage(input_tokens=0, output_tokens=0, total_tokens=0),
                    error=f"{service_name} API key not configured"
                )

            response.raise_for_status()
            data = response.json()

            return LLMResult(
                content=data.get("content", ""),
                model=data.get("model", model),
                usage=LLMUsage(
                    input_tokens=data.get("usage", {}).get("input_tokens", 0),
                    output_tokens=data.get("usage", {}).get("output_tokens", 0),
                    total_tokens=data.get("usage", {}).get("total_tokens", 0)
                )
            )

    except httpx.HTTPStatusError as e:
        return LLMResult(
            content="",
            model=model,
            usage=LLMUsage(input_tokens=0, output_tokens=0, total_tokens=0),
            error=f"{service_name} HTTP error: {e.response.status_code}"
        )
    except Exception as e:
        return LLMResult(
            content="",
            model=model,
            usage=LLMUsage(input_tokens=0, output_tokens=0, total_tokens=0),
            error=f"{service_name} error: {str(e)}"
        )


@router.post("/llm-compare", response_model=LLMCompareResponse)
async def compare_llms(
    request: LLMCompareRequest,
    username: str = Depends(get_current_user)
):
    """
    Compare responses from Anthropic and OpenRouter LLMs.

    Sends the same prompt to both services in parallel and returns
    side-by-side results with content and token usage.

    Args:
        request: LLMCompareRequest with prompt and optional model selections
        username: Current authenticated user

    Returns:
        LLMCompareResponse with results from both providers
    """
    # Call both services in parallel
    anthropic_task = call_llm_service(
        ANTHROPIC_SERVICE_URL,
        request.prompt,
        request.anthropic_model,
        "Anthropic"
    )
    openrouter_task = call_llm_service(
        OPENROUTER_SERVICE_URL,
        request.prompt,
        request.openrouter_model,
        "OpenRouter"
    )

    anthropic_result, openrouter_result = await asyncio.gather(
        anthropic_task,
        openrouter_task
    )

    return LLMCompareResponse(
        prompt=request.prompt,
        anthropic=anthropic_result,
        openrouter=openrouter_result
    )
