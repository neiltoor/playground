"""Activity log API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import require_admin
from app.models import ActivityLogEntry, ActivityLogsResponse, ActivityStatsResponse
from app.services.activity_service import ActivityService


router = APIRouter()


@router.get("/activity", response_model=ActivityLogsResponse)
async def get_activity_logs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    username: Optional[str] = None,
    activity_type: Optional[str] = None,
    admin_user: dict = Depends(require_admin)
):
    """
    Get activity logs. Admin only.

    Args:
        limit: Max number of records to return (1-1000)
        offset: Number of records to skip
        username: Filter by username
        activity_type: Filter by activity type (login, api_call)

    Returns:
        Paginated list of activity logs
    """
    logs = ActivityService.get_activity_logs(
        limit=limit,
        offset=offset,
        username=username,
        activity_type=activity_type
    )

    total = ActivityService.get_activity_count(
        username=username,
        activity_type=activity_type
    )

    return ActivityLogsResponse(
        logs=[ActivityLogEntry(**log) for log in logs],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/activity/stats", response_model=ActivityStatsResponse)
async def get_activity_stats(
    admin_user: dict = Depends(require_admin)
):
    """
    Get activity statistics. Admin only.

    Returns:
        Aggregated activity statistics including counts by type,
        activities in last 24 hours, and unique users today.
    """
    stats = ActivityService.get_activity_stats()
    return ActivityStatsResponse(**stats)
