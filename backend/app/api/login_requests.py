"""Login request API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status

from app.auth import require_admin
from app.models import (
    CaptchaChallenge,
    LoginRequestCreate,
    LoginRequestResponse,
    LoginRequestEntry,
    LoginRequestsResponse,
    ApproveLoginRequestModel,
    RejectLoginRequestModel
)
from app.services.login_request_service import LoginRequestService


router = APIRouter()


@router.get("/captcha", response_model=CaptchaChallenge)
async def get_captcha():
    """Get a new CAPTCHA challenge for login request."""
    captcha = LoginRequestService.generate_captcha()
    return CaptchaChallenge(
        challenge_id=captcha["challenge_id"],
        question=captcha["question"]
    )


@router.post("/request-login", response_model=LoginRequestResponse)
async def create_login_request(request: LoginRequestCreate, req: Request):
    """
    Submit a login request (public endpoint).

    Requires valid CAPTCHA answer.
    """
    # Verify CAPTCHA
    if not LoginRequestService.verify_captcha(request.captcha_id, request.captcha_answer):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired CAPTCHA. Please try again."
        )

    # Get client info
    ip_address = req.headers.get("x-forwarded-for", req.client.host if req.client else "unknown")
    if "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()
    user_agent = req.headers.get("user-agent")

    # Create request
    result = LoginRequestService.create_request(
        email=request.email,
        reason=request.reason,
        ip_address=ip_address,
        user_agent=user_agent
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result.get("error", "A pending request for this email already exists.")
        )

    return LoginRequestResponse(
        message="Your login request has been submitted. An administrator will review it shortly.",
        email=request.email
    )


@router.get("/login-requests", response_model=LoginRequestsResponse)
async def get_login_requests(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, pattern=r'^(pending|approved|rejected)$'),
    admin_user: dict = Depends(require_admin)
):
    """
    Get login requests. Admin only.
    """
    requests = LoginRequestService.get_requests(
        limit=limit,
        offset=offset,
        status=status
    )

    total = LoginRequestService.get_request_count(status=status)

    return LoginRequestsResponse(
        requests=[LoginRequestEntry(**r) for r in requests],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/login-requests/pending-count")
async def get_pending_count(admin_user: dict = Depends(require_admin)):
    """Get count of pending login requests. Admin only."""
    count = LoginRequestService.get_pending_count()
    return {"pending_count": count}


@router.post("/login-requests/{request_id}/approve")
async def approve_login_request(
    request_id: int,
    approval: ApproveLoginRequestModel,
    admin_user: dict = Depends(require_admin)
):
    """
    Approve a login request. Admin only.

    Creates user credentials and adds to auth file.
    """
    result = LoginRequestService.approve_request(
        request_id=request_id,
        username=approval.username,
        password=approval.password,
        role=approval.role,
        admin_username=admin_user["username"],
        notes=approval.notes
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return {
        "message": f"Request approved. User '{result['username']}' created successfully.",
        "username": result["username"]
    }


@router.post("/login-requests/{request_id}/reject")
async def reject_login_request(
    request_id: int,
    rejection: RejectLoginRequestModel,
    admin_user: dict = Depends(require_admin)
):
    """
    Reject a login request. Admin only.
    """
    result = LoginRequestService.reject_request(
        request_id=request_id,
        admin_username=admin_user["username"],
        notes=rejection.notes
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return {"message": "Request rejected."}
