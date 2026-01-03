"""
Integration tests for Login API endpoints.
Tests the /api/login and /api/me endpoints against the running backend.
"""
import httpx
import pytest
from datetime import datetime, timedelta
from jose import jwt


# Backend URL (internal Docker network)
BACKEND_URL = "http://backend:8000"

# Test credentials (from /data/auth file)
VALID_USERNAME = "neil"
VALID_PASSWORD = "Picerne!"

# JWT config (must match backend)
SECRET_KEY = "dev-secret-key-change-in-production"
ALGORITHM = "HS256"


class TestLoginEndpoint:
    """Tests for POST /api/login endpoint."""

    def test_login_success(self):
        """Valid credentials should return JWT token."""
        response = httpx.post(
            f"{BACKEND_URL}/api/login",
            json={"username": VALID_USERNAME, "password": VALID_PASSWORD},
            timeout=10.0
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "access_token" in data
        assert "token_type" in data
        assert "username" in data

        # Verify token type
        assert data["token_type"] == "bearer"
        assert data["username"] == VALID_USERNAME

        # Verify token is valid JWT
        assert len(data["access_token"]) > 0
        print(f"✓ Login successful, token received for user: {data['username']}")

    def test_login_invalid_password(self):
        """Wrong password should return 401 Unauthorized."""
        response = httpx.post(
            f"{BACKEND_URL}/api/login",
            json={"username": VALID_USERNAME, "password": "wrong-password"},
            timeout=10.0
        )

        assert response.status_code == 401
        data = response.json()
        assert "Invalid username or password" in data["detail"]
        print("✓ Invalid password correctly rejected")

    def test_login_invalid_username(self):
        """Unknown username should return 401 Unauthorized."""
        response = httpx.post(
            f"{BACKEND_URL}/api/login",
            json={"username": "nonexistent_user", "password": "any-password"},
            timeout=10.0
        )

        assert response.status_code == 401
        data = response.json()
        assert "Invalid username or password" in data["detail"]
        print("✓ Unknown user correctly rejected")

    def test_login_empty_credentials(self):
        """Empty credentials should return 422 Validation Error."""
        # Empty username
        response = httpx.post(
            f"{BACKEND_URL}/api/login",
            json={"username": "", "password": "test"},
            timeout=10.0
        )
        assert response.status_code == 422

        # Empty password
        response = httpx.post(
            f"{BACKEND_URL}/api/login",
            json={"username": "test", "password": ""},
            timeout=10.0
        )
        assert response.status_code == 422

        # Missing fields
        response = httpx.post(
            f"{BACKEND_URL}/api/login",
            json={},
            timeout=10.0
        )
        assert response.status_code == 422
        print("✓ Empty credentials correctly rejected with 422")


class TestMeEndpoint:
    """Tests for GET /api/me endpoint."""

    def _get_valid_token(self) -> str:
        """Helper to get a valid auth token."""
        response = httpx.post(
            f"{BACKEND_URL}/api/login",
            json={"username": VALID_USERNAME, "password": VALID_PASSWORD},
            timeout=10.0
        )
        return response.json()["access_token"]

    def test_me_endpoint_valid_token(self):
        """Valid token should return user info."""
        token = self._get_valid_token()

        response = httpx.get(
            f"{BACKEND_URL}/api/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0
        )

        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert data["username"] == VALID_USERNAME
        print(f"✓ /api/me returned user info: {data}")

    def test_me_endpoint_no_token(self):
        """Missing token should return 403 Forbidden."""
        response = httpx.get(
            f"{BACKEND_URL}/api/me",
            timeout=10.0
        )

        # FastAPI HTTPBearer returns 403 when no credentials provided
        assert response.status_code == 403
        print("✓ Missing token correctly rejected with 403")

    def test_me_endpoint_invalid_token(self):
        """Invalid token should return 401 Unauthorized."""
        response = httpx.get(
            f"{BACKEND_URL}/api/me",
            headers={"Authorization": "Bearer invalid-token-here"},
            timeout=10.0
        )

        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]
        print("✓ Invalid token correctly rejected")

    def test_me_endpoint_expired_token(self):
        """Expired token should return 401 Unauthorized."""
        # Create an expired token (expired 1 hour ago)
        expired_payload = {
            "sub": VALID_USERNAME,
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)

        response = httpx.get(
            f"{BACKEND_URL}/api/me",
            headers={"Authorization": f"Bearer {expired_token}"},
            timeout=10.0
        )

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
        print("✓ Expired token correctly rejected")


if __name__ == "__main__":
    """Run tests directly for manual testing."""
    print("\n=== Testing Login API ===\n")

    # Login tests
    login_tests = TestLoginEndpoint()
    for test_name in ['test_login_success', 'test_login_invalid_password',
                      'test_login_invalid_username', 'test_login_empty_credentials']:
        try:
            getattr(login_tests, test_name)()
        except Exception as e:
            print(f"✗ {test_name} failed: {e}")

    # Me endpoint tests
    me_tests = TestMeEndpoint()
    for test_name in ['test_me_endpoint_valid_token', 'test_me_endpoint_no_token',
                      'test_me_endpoint_invalid_token', 'test_me_endpoint_expired_token']:
        try:
            getattr(me_tests, test_name)()
        except Exception as e:
            print(f"✗ {test_name} failed: {e}")

    print("\n=== Login API Tests Complete ===\n")
