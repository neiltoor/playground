"""
Tests for Anthropic microservice endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app


client = TestClient(app)


def test_health_endpoint():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "anthropic-llm"
    assert "api_key_configured" in data


def test_chat_endpoint_no_api_key():
    """Test chat endpoint returns 503 when no API key is configured."""
    with patch('main.client', None):
        response = client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "claude-3-5-sonnet-20241022"
            }
        )
        assert response.status_code == 503
        assert "API key not configured" in response.json()["detail"]


def test_chat_endpoint_with_mocked_anthropic():
    """Test chat endpoint with mocked Anthropic response."""
    # Mock the Anthropic client response
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Hello! How can I help you?")]
    mock_response.model = "claude-3-5-sonnet-20241022"
    mock_response.usage = MagicMock(input_tokens=10, output_tokens=8)

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch('main.client', mock_client):
        response = client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 0.7,
                "max_tokens": 1024
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Hello! How can I help you?"
        assert data["model"] == "claude-3-5-sonnet-20241022"
        assert data["usage"]["input_tokens"] == 10
        assert data["usage"]["output_tokens"] == 8

        # Verify the Anthropic API was called with correct parameters
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-5-sonnet-20241022"
        assert call_kwargs["max_tokens"] == 1024
        assert call_kwargs["temperature"] == 0.7
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"
        assert call_kwargs["messages"][0]["content"] == "Hello"


def test_chat_endpoint_with_multiple_messages():
    """Test chat endpoint with conversation history."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Sure, I can help with that!")]
    mock_response.model = "claude-3-5-sonnet-20241022"
    mock_response.usage = MagicMock(input_tokens=50, output_tokens=20)

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch('main.client', mock_client):
        response = client.post(
            "/chat",
            json={
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"},
                    {"role": "user", "content": "Can you help me?"}
                ],
                "model": "claude-3-5-sonnet-20241022"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Sure, I can help with that!"

        # Verify all messages were passed
        call_kwargs = mock_client.messages.create.call_args[1]
        assert len(call_kwargs["messages"]) == 3


def test_chat_endpoint_handles_anthropic_error():
    """Test that Anthropic API errors are handled properly."""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("API Error: Rate limit exceeded")

    with patch('main.client', mock_client):
        response = client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "claude-3-5-sonnet-20241022"
            }
        )

        assert response.status_code == 500
        assert "Anthropic API error" in response.json()["detail"]
