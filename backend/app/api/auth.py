from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.models import LoginRequest, LoginResponse, UserInfo
from app.auth import authenticate_user, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from app.services.activity_service import ActivityService


router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, req: Request):
    """
    Authenticate user and return JWT token.

    Reads credentials from /data/auth file (username:password:role format).
    Returns JWT token valid for 24 hours.

    Args:
        request: Login credentials (username and password)
        req: FastAPI Request object for logging IP/user-agent

    Returns:
        JWT access token, token type, username, and role

    Raises:
        HTTPException 401: If credentials are invalid
        HTTPException 500: If auth file is missing or malformed
    """
    # Get client info for logging
    ip_address = req.headers.get("x-forwarded-for", req.client.host if req.client else "unknown")
    if "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()
    user_agent = req.headers.get("user-agent")

    try:
        # Authenticate against /data/auth file
        user_info = authenticate_user(request.username, request.password)

        if not user_info:
            # Log failed login attempt
            ActivityService.log_login(
                username=request.username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create JWT token with role
        token_data = {"sub": user_info["username"], "role": user_info["role"]}
        expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(token_data, expires)

        # Log successful login
        ActivityService.log_login(
            username=user_info["username"],
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )

        # Return token with role
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            username=user_info["username"],
            role=user_info["role"]
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
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Protected endpoint requiring valid JWT token.

    Args:
        user: Current user dict (from JWT token dependency)

    Returns:
        User information including role

    Raises:
        HTTPException 401: If token is invalid or expired
    """
    return UserInfo(username=user["username"], role=user["role"])
