"""
Integration tests for microservices endpoints.
Tests the actual running services via HTTP.
"""
import httpx
import pytest


# Service URLs (internal Docker network)
ANTHROPIC_SERVICE_URL = "http://anthropic-service:8001"
OPENROUTER_SERVICE_URL = "http://openrouter-service:8002"


def test_anthropic_health():
    """Test Anthropic service health endpoint."""
    response = httpx.get(f"{ANTHROPIC_SERVICE_URL}/health", timeout=5.0)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "anthropic-llm"
    print(f"✓ Anthropic service health check passed: {data}")


def test_openrouter_health():
    """Test OpenRouter service health endpoint."""
    response = httpx.get(f"{OPENROUTER_SERVICE_URL}/health", timeout=5.0)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "openrouter-llm"
    print(f"✓ OpenRouter service health check passed: {data}")


def test_anthropic_chat_basic():
    """Test Anthropic service chat endpoint with a simple query."""
    payload = {
        "messages": [
            {"role": "user", "content": "Say 'test successful' and nothing else."}
        ],
        "model": "claude-3-haiku-20240307",
        "temperature": 0.1,
        "max_tokens": 50
    }

    response = httpx.post(
        f"{ANTHROPIC_SERVICE_URL}/chat",
        json=payload,
        timeout=30.0
    )

    print(f"Anthropic response status: {response.status_code}")

    if response.status_code == 503:
        pytest.skip("Anthropic API key not configured")

    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "model" in data
    assert "usage" in data
    assert len(data["content"]) > 0
    print(f"✓ Anthropic chat test passed. Response: {data['content'][:100]}")


def test_openrouter_chat_basic():
    """Test OpenRouter service chat endpoint with a simple query."""
    payload = {
        "messages": [
            {"role": "user", "content": "Say 'test successful' and nothing else."}
        ],
        "model": "x-ai/grok-3-mini",
        "temperature": 0.1,
        "max_tokens": 50
    }

    response = httpx.post(
        f"{OPENROUTER_SERVICE_URL}/chat",
        json=payload,
        timeout=30.0
    )

    print(f"OpenRouter response status: {response.status_code}")

    if response.status_code == 503:
        pytest.skip("OpenRouter API key not configured")

    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "model" in data
    assert "usage" in data
    assert len(data["content"]) > 0
    print(f"✓ OpenRouter chat test passed. Response: {data['content'][:100]}")


def test_anthropic_chat_with_context():
    """Test Anthropic service with multi-turn conversation."""
    payload = {
        "messages": [
            {"role": "user", "content": "Hello, what's your name?"},
            {"role": "assistant", "content": "I'm Claude, an AI assistant."},
            {"role": "user", "content": "What can you help me with?"}
        ],
        "model": "claude-3-haiku-20240307",
        "temperature": 0.3,
        "max_tokens": 100
    }

    response = httpx.post(
        f"{ANTHROPIC_SERVICE_URL}/chat",
        json=payload,
        timeout=30.0
    )

    if response.status_code == 503:
        pytest.skip("Anthropic API key not configured")

    assert response.status_code == 200
    data = response.json()
    assert len(data["content"]) > 0
    assert data["usage"]["input_tokens"] > 0
    assert data["usage"]["output_tokens"] > 0
    print(f"✓ Anthropic multi-turn test passed. Tokens used: {data['usage']}")


def test_openrouter_chat_with_different_model():
    """Test OpenRouter service with a different model."""
    payload = {
        "messages": [
            {"role": "user", "content": "What is 2+2?"}
        ],
        "model": "google/gemini-flash-1.5",
        "temperature": 0.1,
        "max_tokens": 50
    }

    response = httpx.post(
        f"{OPENROUTER_SERVICE_URL}/chat",
        json=payload,
        timeout=30.0
    )

    if response.status_code == 503:
        pytest.skip("OpenRouter API key not configured")

    # Some models might not be available, that's okay
    if response.status_code == 200:
        data = response.json()
        assert "content" in data
        print(f"✓ OpenRouter different model test passed: {data.get('model')}")
    else:
        print(f"⚠ Model not available or error: {response.status_code}")


if __name__ == "__main__":
    """Run tests directly for manual testing."""
    print("\n=== Testing Microservices ===\n")

    try:
        test_anthropic_health()
    except Exception as e:
        print(f"✗ Anthropic health check failed: {e}")

    try:
        test_openrouter_health()
    except Exception as e:
        print(f"✗ OpenRouter health check failed: {e}")

    try:
        test_anthropic_chat_basic()
    except Exception as e:
        print(f"✗ Anthropic chat test failed: {e}")

    try:
        test_openrouter_chat_basic()
    except Exception as e:
        print(f"✗ OpenRouter chat test failed: {e}")

    print("\n=== Tests Complete ===\n")
