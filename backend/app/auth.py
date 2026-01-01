import os
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt


# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours
AUTH_FILE_PATH = "/data/auth"

# Security scheme
security = HTTPBearer()


def read_auth_file() -> Dict[str, str]:
    """
    Read and parse the /data/auth file.

    Format: username:password (one per line)

    Returns:
        Dictionary mapping username -> password

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

                # Parse username:password format
                if ':' not in line:
                    raise ValueError(f"Invalid format on line {line_num}: missing ':' separator")

                parts = line.split(':', 1)
                if len(parts) != 2:
                    raise ValueError(f"Invalid format on line {line_num}")

                username = parts[0].strip()
                password = parts[1].strip()

                if not username or not password:
                    raise ValueError(f"Empty username or password on line {line_num}")

                users[username] = password

        return users

    except Exception as e:
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise
        raise ValueError(f"Error reading auth file: {str(e)}")


def authenticate_user(username: str, password: str) -> bool:
    """
    Authenticate user against /data/auth file.

    Args:
        username: Username to authenticate
        password: Password to verify (plaintext)

    Returns:
        True if credentials are valid, False otherwise
    """
    try:
        users = read_auth_file()

        if username not in users:
            return False

        # Plaintext password comparison (as requested)
        return users[username] == password

    except FileNotFoundError:
        # If auth file doesn't exist, authentication fails
        return False
    except Exception as e:
        # Log error but don't expose details to user
        print(f"Authentication error: {e}")
        return False


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


def verify_token(token: str) -> str:
    """
    Verify and decode JWT token.

    Args:
        token: JWT token string to verify

    Returns:
        Username from token payload

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

        if username is None:
            raise credentials_exception

        return username

    except JWTError as e:
        if "expired" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise credentials_exception


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    FastAPI dependency to get current authenticated user from JWT token.

    Extracts Bearer token from Authorization header, validates it, and returns username.

    Args:
        credentials: HTTP Bearer credentials from request header

    Returns:
        Username of authenticated user

    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    token = credentials.credentials
    username = verify_token(token)
    return username
