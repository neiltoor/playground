import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://raguser:ragpassword@postgres:5432/ragdb"
    )

    # OpenRouter API
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    # LLM Model Selection
    # Options: "x-ai/grok-beta" or "google/gemini-flash-1.5-8b"
    LLM_MODEL: str = os.getenv("LLM_MODEL", "google/gemini-flash-1.5-8b")

    # Application settings
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    TOP_K_RETRIEVAL: int = int(os.getenv("TOP_K_RETRIEVAL", "5"))

    # Upload directory
    UPLOAD_DIR: str = "/app/uploads"

    # Supported file types
    ALLOWED_EXTENSIONS: set = {".pdf", ".txt", ".docx", ".md"}

    # Authentication settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours
    AUTH_FILE_PATH: str = "/tmp/auth"

    def validate(self) -> bool:
        """Validate required settings."""
        if not self.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is required")
        return True


settings = Settings()
