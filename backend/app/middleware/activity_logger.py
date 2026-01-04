"""Middleware to log user activity to database."""

from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.activity_service import ActivityService


class ActivityLoggerMiddleware(BaseHTTPMiddleware):
    """Middleware to log authenticated API calls to database."""

    # Endpoints to track (only log authenticated API calls)
    TRACKED_ENDPOINTS = [
        "/api/upload",
        "/api/query",
        "/api/documents",
        "/api/llm-compare",
        "/api/me",
        "/api/activity",
    ]

    # Endpoints to skip (login logged separately, health is public)
    SKIP_ENDPOINTS = [
        "/api/login",
        "/api/health",
    ]

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Only log tracked endpoints
        path = request.url.path

        # Skip non-API or excluded endpoints
        if not path.startswith("/api/") or any(path.startswith(ep) for ep in self.SKIP_ENDPOINTS):
            return response

        # Only log if it's a tracked endpoint
        if not any(path.startswith(ep) for ep in self.TRACKED_ENDPOINTS):
            return response

        # Extract user from JWT if present
        username = await self._extract_username(request)

        if username:
            # Log activity
            ActivityService.log_api_call(
                username=username,
                endpoint=path,
                method=request.method,
                ip_address=self._get_client_ip(request),
                status_code=response.status_code,
                user_agent=request.headers.get("user-agent")
            )

        return response

    async def _extract_username(self, request: Request) -> Optional[str]:
        """Extract username from Authorization header."""
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        try:
            from app.auth import verify_token
            token = auth_header.split(" ")[1]
            user_info = verify_token(token)
            return user_info.get("username")
        except Exception:
            return None

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP, considering X-Forwarded-For from nginx."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
