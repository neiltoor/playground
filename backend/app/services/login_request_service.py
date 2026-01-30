"""Service for managing login requests and CAPTCHA."""

import secrets
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from sqlalchemy import text

from app.database import create_db_engine


# In-memory CAPTCHA store (expires after 5 minutes)
# Format: {challenge_id: {"answer": str, "expires": datetime}}
_captcha_store: Dict[str, Dict] = {}


class LoginRequestService:
    """Service for login requests and CAPTCHA management."""

    AUTH_FILE_PATH = "/data/auth"

    @staticmethod
    def generate_captcha() -> Dict[str, str]:
        """Generate a simple math CAPTCHA."""
        # Clean expired CAPTCHAs
        LoginRequestService._cleanup_captchas()

        # Generate math problem
        num1 = random.randint(1, 20)
        num2 = random.randint(1, 20)
        operation = random.choice(['+', '-'])

        if operation == '+':
            answer = num1 + num2
            question = f"What is {num1} + {num2}?"
        else:
            # Ensure positive result
            if num1 < num2:
                num1, num2 = num2, num1
            answer = num1 - num2
            question = f"What is {num1} - {num2}?"

        challenge_id = secrets.token_urlsafe(16)
        _captcha_store[challenge_id] = {
            "answer": str(answer),
            "expires": datetime.utcnow() + timedelta(minutes=5)
        }

        return {"challenge_id": challenge_id, "question": question}

    @staticmethod
    def verify_captcha(challenge_id: str, answer: str) -> bool:
        """Verify CAPTCHA answer."""
        LoginRequestService._cleanup_captchas()

        if challenge_id not in _captcha_store:
            return False

        captcha_data = _captcha_store.pop(challenge_id)
        return captcha_data["answer"] == answer.strip()

    @staticmethod
    def _cleanup_captchas():
        """Remove expired CAPTCHAs."""
        now = datetime.utcnow()
        expired = [k for k, v in _captcha_store.items() if v["expires"] < now]
        for k in expired:
            del _captcha_store[k]

    @staticmethod
    def create_request(
        email: str,
        reason: str,
        ip_address: str,
        user_agent: Optional[str]
    ) -> Dict[str, Any]:
        """Create a new login request."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                # Check if email already has pending request
                result = conn.execute(
                    text("SELECT id FROM login_requests WHERE email = :email AND status = 'pending'"),
                    {"email": email}
                )
                if result.fetchone():
                    return {"success": False, "error": "A pending request for this email already exists"}

                # Check if email exists but was rejected - allow resubmission
                now = datetime.utcnow()
                conn.execute(
                    text("""
                        INSERT INTO login_requests (email, reason, status, request_ip, user_agent, created_at, updated_at)
                        VALUES (:email, :reason, 'pending', :ip_address, :user_agent, :now, :now)
                        ON CONFLICT (email) DO UPDATE SET
                            reason = :reason,
                            status = 'pending',
                            request_ip = :ip_address,
                            user_agent = :user_agent,
                            updated_at = :now,
                            reviewed_by = NULL,
                            reviewed_at = NULL,
                            assigned_username = NULL,
                            notes = NULL
                    """),
                    {
                        "email": email,
                        "reason": reason,
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "now": now
                    }
                )
                conn.commit()
                return {"success": True}
        except Exception as e:
            print(f"Error creating login request: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_requests(
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get login requests with optional filtering."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                query = "SELECT * FROM login_requests WHERE 1=1"
                params = {}

                if status:
                    query += " AND status = :status"
                    params["status"] = status

                query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
                params["limit"] = limit
                params["offset"] = offset

                result = conn.execute(text(query), params)
                return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"Error getting login requests: {e}")
            return []

    @staticmethod
    def get_request_count(status: Optional[str] = None) -> int:
        """Get count of login requests."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                query = "SELECT COUNT(*) FROM login_requests WHERE 1=1"
                params = {}

                if status:
                    query += " AND status = :status"
                    params["status"] = status

                result = conn.execute(text(query), params)
                return result.scalar() or 0
        except Exception as e:
            print(f"Error counting login requests: {e}")
            return 0

    @staticmethod
    def get_pending_count() -> int:
        """Get count of pending requests."""
        return LoginRequestService.get_request_count(status="pending")

    @staticmethod
    def approve_request(
        request_id: int,
        username: str,
        password: str,
        role: str,
        admin_username: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve a login request and add user to auth file."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                # Get the request
                result = conn.execute(
                    text("SELECT * FROM login_requests WHERE id = :id AND status = 'pending'"),
                    {"id": request_id}
                )
                request = result.fetchone()
                if not request:
                    return {"success": False, "error": "Request not found or already processed"}

                # Check username doesn't exist in auth file
                if LoginRequestService._username_exists(username):
                    return {"success": False, "error": f"Username '{username}' already exists"}

                # Add to auth file
                if not LoginRequestService._add_to_auth_file(username, password, role):
                    return {"success": False, "error": "Failed to update auth file"}

                # Update request status
                now = datetime.utcnow()
                conn.execute(
                    text("""
                        UPDATE login_requests
                        SET status = 'approved',
                            reviewed_by = :admin,
                            reviewed_at = :now,
                            assigned_username = :username,
                            notes = :notes,
                            updated_at = :now
                        WHERE id = :id
                    """),
                    {
                        "id": request_id,
                        "admin": admin_username,
                        "now": now,
                        "username": username,
                        "notes": notes
                    }
                )
                conn.commit()
                return {"success": True, "username": username}
        except Exception as e:
            print(f"Error approving login request: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def reject_request(
        request_id: int,
        admin_username: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reject a login request."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT id FROM login_requests WHERE id = :id AND status = 'pending'"),
                    {"id": request_id}
                )
                if not result.fetchone():
                    return {"success": False, "error": "Request not found or already processed"}

                now = datetime.utcnow()
                conn.execute(
                    text("""
                        UPDATE login_requests
                        SET status = 'rejected',
                            reviewed_by = :admin,
                            reviewed_at = :now,
                            notes = :notes,
                            updated_at = :now
                        WHERE id = :id
                    """),
                    {
                        "id": request_id,
                        "admin": admin_username,
                        "now": now,
                        "notes": notes
                    }
                )
                conn.commit()
                return {"success": True}
        except Exception as e:
            print(f"Error rejecting login request: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _username_exists(username: str) -> bool:
        """Check if username exists in auth file."""
        try:
            auth_file = Path(LoginRequestService.AUTH_FILE_PATH)
            if not auth_file.exists():
                return False
            with open(auth_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split(':')
                        if parts and parts[0] == username:
                            return True
            return False
        except Exception as e:
            print(f"Error checking username: {e}")
            return False

    @staticmethod
    def _add_to_auth_file(username: str, password: str, role: str) -> bool:
        """Add a new user to the auth file."""
        try:
            auth_file = Path(LoginRequestService.AUTH_FILE_PATH)
            with open(auth_file, 'a') as f:
                f.write(f"\n{username}:{password}:{role}")
            return True
        except Exception as e:
            print(f"Error writing to auth file: {e}")
            return False
