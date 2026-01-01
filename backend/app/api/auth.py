from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from app.models import LoginRequest, LoginResponse, UserInfo
from app.auth import authenticate_user, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES


router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT token.

    Reads credentials from /data/auth file (username:password format).
    Returns JWT token valid for 24 hours.

    Args:
        request: Login credentials (username and password)

    Returns:
        JWT access token, token type, and username

    Raises:
        HTTPException 401: If credentials are invalid
        HTTPException 500: If auth file is missing or malformed
    """
    try:
        # Authenticate against /data/auth file
        if not authenticate_user(request.username, request.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create JWT token
        token_data = {"sub": request.username}
        expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(token_data, expires)

        # Return token
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            username=request.username
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication system not configured. Contact administrator."
        )
    except Exception as e:
        # Log error but don't expose internals to user
        print(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during authentication"
        )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(username: str = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Protected endpoint requiring valid JWT token.

    Args:
        username: Current user (from JWT token dependency)

    Returns:
        User information

    Raises:
        HTTPException 401: If token is invalid or expired
    """
    return UserInfo(username=username)
