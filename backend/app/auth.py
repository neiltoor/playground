import os
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt


# JWT Configuration - load from config file, env var, or generate
CONFIG_FILE_PATH = "/data/config.json"

def _load_jwt_secret() -> str:
    """Load JWT secret from config file, env var, or generate one."""
    # 1. Try config file first
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config = json.load(f)
            if config.get("jwt_secret_key"):
                print("Loaded JWT secret from /data/config.json")
                return config["jwt_secret_key"]
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        pass

    # 2. Try environment variable
    env_secret = os.getenv("JWT_SECRET_KEY")
    if env_secret and env_secret != "dev-secret-key-change-in-production":
        print("Loaded JWT secret from JWT_SECRET_KEY environment variable")
        return env_secret

    # 3. Generate random key (not recommended for production)
    print("WARNING: JWT secret not found in /data/config.json or JWT_SECRET_KEY env var.")
    print("WARNING: Generated random key - tokens will invalidate on restart!")
    return secrets.token_hex(32)

SECRET_KEY = _load_jwt_secret()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours
AUTH_FILE_PATH = "/data/auth"
LOCKOUT_FILE_PATH = "/data/.lockouts.json"
MAX_FAILED_ATTEMPTS = 20

# Security scheme
security = HTTPBearer()


def read_auth_file() -> Dict[str, Dict[str, str]]:
    """
    Read and parse the /data/auth file.

    Format: username:password:role (one per line)
    Role is optional, defaults to 'user' if not specified.

    Returns:
        Dictionary mapping username -> {"password": str, "role": str}

    Raises:
        FileNotFoundError: If auth file doesn't exist
        ValueError: If file format is invalid
    """
    auth_file = Path(AUTH_FILE_PATH)

    if not auth_file.exists():
        raise FileNotFoundError(f"Auth file not found at {AUTH_FILE_PATH}")

    users = {}

    try:
        with open(auth_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Parse username:password:role format
                if ':' not in line:
                    raise ValueError(f"Invalid format on line {line_num}: missing ':' separator")

                parts = line.split(':')
                if len(parts) < 2:
                    raise ValueError(f"Invalid format on line {line_num}")

                username = parts[0].strip()
                password = parts[1].strip()
                role = parts[2].strip() if len(parts) > 2 else "user"

                if not username or not password:
                    raise ValueError(f"Empty username or password on line {line_num}")

                if role not in ["admin", "user"]:
                    raise ValueError(f"Invalid role '{role}' on line {line_num}. Must be 'admin' or 'user'")

                users[username] = {"password": password, "role": role}

        return users

    except Exception as e:
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise
        raise ValueError(f"Error reading auth file: {str(e)}")


def _read_lockouts() -> Dict[str, Dict]:
    """Read lockout data from file."""
    lockout_file = Path(LOCKOUT_FILE_PATH)
    if not lockout_file.exists():
        return {}
    try:
        with open(lockout_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _write_lockouts(lockouts: Dict[str, Dict]) -> None:
    """Write lockout data to file."""
    lockout_file = Path(LOCKOUT_FILE_PATH)
    try:
        with open(lockout_file, 'w') as f:
            json.dump(lockouts, f)
    except IOError as e:
        print(f"Warning: Could not write lockout file: {e}")


def is_account_locked(username: str) -> bool:
    """Check if an account is locked due to too many failed attempts."""
    lockouts = _read_lockouts()
    user_data = lockouts.get(username)
    if not user_data:
        return False
    return user_data.get("failed_attempts", 0) >= MAX_FAILED_ATTEMPTS


def record_failed_login(username: str) -> int:
    """Record a failed login attempt. Returns current failed count."""
    lockouts = _read_lockouts()
    if username not in lockouts:
        lockouts[username] = {"failed_attempts": 0, "first_failure": datetime.utcnow().isoformat()}
    lockouts[username]["failed_attempts"] += 1
    lockouts[username]["last_failure"] = datetime.utcnow().isoformat()
    _write_lockouts(lockouts)
    return lockouts[username]["failed_attempts"]


def reset_failed_logins(username: str) -> None:
    """Reset failed login count after successful login."""
    lockouts = _read_lockouts()
    if username in lockouts:
        del lockouts[username]
        _write_lockouts(lockouts)


def authenticate_user(username: str, password: str) -> Optional[Dict[str, str]]:
    """
    Authenticate user against /data/auth file.

    Args:
        username: Username to authenticate
        password: Password to verify (plaintext)

    Returns:
        User info dict {"username": str, "role": str} if valid, None otherwise
    """
    try:
        users = read_auth_file()

        if username not in users:
            return None

        user_data = users[username]
        # Plaintext password comparison (as requested)
        if user_data["password"] == password:
            return {"username": username, "role": user_data["role"]}

        return None

    except FileNotFoundError:
        # If auth file doesn't exist, authentication fails
        return None
    except Exception as e:
        # Log error but don't expose details to user
        print(f"Authentication error: {e}")
        return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode in token (should include 'sub' with username)
        expires_delta: Token expiration time (default: 24 hours)

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, str]:
    """
    Verify and decode JWT token.

    Args:
        token: JWT token string to verify

    Returns:
        Dict with username and role from token payload

    Raises:
        HTTPException: If token is invalid, expired, or malformed
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", "user")

        if username is None:
            raise credentials_exception

        return {"username": username, "role": role}

    except JWTError as e:
        if "expired" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise credentials_exception


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, str]:
    """
    FastAPI dependency to get current authenticated user from JWT token.

    Extracts Bearer token from Authorization header, validates it, and returns user info.

    Args:
        credentials: HTTP Bearer credentials from request header

    Returns:
        Dict with username and role of authenticated user

    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    token = credentials.credentials
    return verify_token(token)


def require_admin(user: Dict[str, str] = Depends(get_current_user)) -> Dict[str, str]:
    """
    FastAPI dependency requiring admin role.

    Args:
        user: Current user from get_current_user dependency

    Returns:
        User dict if admin

    Raises:
        HTTPException: If user is not an admin
    """
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user
