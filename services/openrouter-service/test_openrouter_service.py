"""
Tests for OpenRouter microservice endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from main import app


client = TestClient(app)


def test_health_endpoint():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "openrouter-llm"
    assert "api_key_configured" in data


def test_chat_endpoint_no_api_key():
    """Test chat endpoint returns 503 when no API key is configured."""
    with patch('main.API_KEY', ""):
        response = client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "x-ai/grok-beta"
            }
        )
        assert response.status_code == 503
        assert "API key not configured" in response.json()["detail"]


def test_chat_endpoint_with_mocked_openrouter():
    """Test chat endpoint with mocked OpenRouter response."""
    # Mock httpx AsyncClient
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "Hello! I'm Grok. How can I help you today?"
            }
        }],
        "model": "x-ai/grok-beta",
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 12,
            "total_tokens": 27
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch('main.API_KEY', 'test-key'):
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/chat",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "model": "x-ai/grok-beta",
                    "temperature": 0.5,
                    "max_tokens": 2048
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["content"] == "Hello! I'm Grok. How can I help you today?"
            assert data["model"] == "x-ai/grok-beta"
            assert data["usage"]["input_tokens"] == 15
            assert data["usage"]["output_tokens"] == 12
            assert data["usage"]["total_tokens"] == 27


def test_chat_endpoint_with_different_models():
    """Test chat endpoint works with different OpenRouter models."""
    models_to_test = [
        "x-ai/grok-beta",
        "google/gemini-flash-1.5",
        "anthropic/claude-3.5-sonnet",
        "meta-llama/llama-3.1-70b-instruct"
    ]

    for model in models_to_test:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": f"Response from {model}"}}],
            "model": model,
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        }
        mock_response.raise_for_status = MagicMock()

        with patch('main.API_KEY', 'test-key'):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value = mock_client

                response = client.post(
                    "/chat",
                    json={
                        "messages": [{"role": "user", "content": "Test"}],
                        "model": model
                    }
                )

                assert response.status_code == 200
                data = response.json()
                assert data["model"] == model


def test_chat_endpoint_handles_http_error():
    """Test that HTTP errors from OpenRouter are handled properly."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Invalid API key"

    from httpx import HTTPStatusError, Request, Response

    with patch('main.API_KEY', 'invalid-key'):
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value.post = AsyncMock(
                side_effect=HTTPStatusError(
                    "401 Unauthorized",
                    request=MagicMock(),
                    response=mock_response
                )
            )
            mock_client_class.return_value = mock_client

            response = client.post(
                "/chat",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "model": "x-ai/grok-beta"
                }
            )

            assert response.status_code == 401
            assert "OpenRouter API error" in response.json()["detail"]


def test_chat_endpoint_handles_network_error():
    """Test that network errors are handled properly."""
    with patch('main.API_KEY', 'test-key'):
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Connection timeout")
            )
            mock_client_class.return_value = mock_client

            response = client.post(
                "/chat",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "model": "x-ai/grok-beta"
                }
            )

            assert response.status_code == 500
            assert "OpenRouter API error" in response.json()["detail"]


def test_chat_endpoint_includes_proper_headers():
    """Test that proper headers are sent to OpenRouter API."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Test response"}}],
        "model": "x-ai/grok-beta",
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}
    }
    mock_response.raise_for_status = MagicMock()

    with patch('main.API_KEY', 'test-api-key'):
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value.post = mock_post
            mock_client_class.return_value = mock_client

            response = client.post(
                "/chat",
                json={
                    "messages": [{"role": "user", "content": "Test"}],
                    "model": "x-ai/grok-beta"
                }
            )

            assert response.status_code == 200

            # Verify headers were set correctly
            call_kwargs = mock_post.call_args[1]
            headers = call_kwargs["headers"]
            assert headers["Authorization"] == "Bearer test-api-key"
            assert headers["Content-Type"] == "application/json"
            assert "HTTP-Referer" in headers
            assert "X-Title" in headers
