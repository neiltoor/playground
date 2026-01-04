"""Service for logging and retrieving user activity."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import text

from app.database import create_db_engine


class ActivityService:
    """Service for logging and retrieving user activity."""

    @staticmethod
    def log_login(username: str, ip_address: str, user_agent: Optional[str] = None, success: bool = True):
        """Log a login attempt."""
        ActivityService._log(
            username=username,
            activity_type="login",
            resource_path="/api/login",
            ip_address=ip_address,
            user_agent=user_agent,
            details=f'{{"success": {str(success).lower()}}}'
        )

    @staticmethod
    def log_api_call(
        username: str,
        endpoint: str,
        method: str,
        ip_address: str,
        status_code: int,
        user_agent: Optional[str] = None
    ):
        """Log an API call."""
        ActivityService._log(
            username=username,
            activity_type="api_call",
            resource_path=endpoint,
            ip_address=ip_address,
            user_agent=user_agent,
            details=f'{{"method": "{method}", "status_code": {status_code}}}'
        )

    @staticmethod
    def _log(
        username: str,
        activity_type: str,
        resource_path: str,
        ip_address: str,
        user_agent: Optional[str] = None,
        details: Optional[str] = None
    ):
        """Internal method to insert log entry."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO activity_log
                        (username, activity_type, resource_path, ip_address, user_agent, details, timestamp)
                        VALUES (:username, :activity_type, :resource_path, :ip_address, :user_agent, :details, :timestamp)
                    """),
                    {
                        "username": username,
                        "activity_type": activity_type,
                        "resource_path": resource_path,
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "details": details,
                        "timestamp": datetime.utcnow()
                    }
                )
                conn.commit()
        except Exception as e:
            print(f"Error logging activity: {e}")

    @staticmethod
    def get_activity_logs(
        limit: int = 100,
        offset: int = 0,
        username: Optional[str] = None,
        activity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve activity logs with optional filters."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                query = "SELECT * FROM activity_log WHERE 1=1"
                params = {}

                if username:
                    query += " AND username = :username"
                    params["username"] = username

                if activity_type:
                    query += " AND activity_type = :activity_type"
                    params["activity_type"] = activity_type

                query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"
                params["limit"] = limit
                params["offset"] = offset

                result = conn.execute(text(query), params)

                return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"Error retrieving activity logs: {e}")
            return []

    @staticmethod
    def get_activity_count(
        username: Optional[str] = None,
        activity_type: Optional[str] = None
    ) -> int:
        """Get total count of activity logs with optional filters."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                query = "SELECT COUNT(*) FROM activity_log WHERE 1=1"
                params = {}

                if username:
                    query += " AND username = :username"
                    params["username"] = username

                if activity_type:
                    query += " AND activity_type = :activity_type"
                    params["activity_type"] = activity_type

                result = conn.execute(text(query), params)
                return result.scalar() or 0
        except Exception as e:
            print(f"Error counting activity logs: {e}")
            return 0

    @staticmethod
    def get_activity_stats() -> Dict[str, Any]:
        """Get aggregated activity statistics."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                # Total activities by type
                result = conn.execute(text("""
                    SELECT activity_type, COUNT(*) as count
                    FROM activity_log
                    GROUP BY activity_type
                """))
                by_type = {row.activity_type: row.count for row in result}

                # Activities in last 24 hours
                result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM activity_log
                    WHERE timestamp > NOW() - INTERVAL '24 hours'
                """))
                last_24h = result.scalar() or 0

                # Unique users today
                result = conn.execute(text("""
                    SELECT COUNT(DISTINCT username) as count
                    FROM activity_log
                    WHERE timestamp > NOW() - INTERVAL '24 hours'
                """))
                unique_users_today = result.scalar() or 0

                return {
                    "by_type": by_type,
                    "last_24_hours": last_24h,
                    "unique_users_today": unique_users_today
                }
        except Exception as e:
            print(f"Error getting activity stats: {e}")
            return {"by_type": {}, "last_24_hours": 0, "unique_users_today": 0}
