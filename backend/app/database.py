from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from app.config import settings


def create_db_engine():
    """Create SQLAlchemy engine for database connection."""
    return create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )


def check_database_connection() -> bool:
    """Check if database connection is healthy."""
    try:
        engine = create_db_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False
    except Exception as e:
        print(f"Database connection error: {e}")
        return False


def get_database_url() -> str:
    """Get database URL from settings."""
    return settings.DATABASE_URL
