import os
import json
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


def load_config_file(config_path: str = "/data/config.json") -> Dict[str, Any]:
    """
    Load configuration from JSON file.

    Falls back to empty dict if file doesn't exist.
    """
    try:
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load config file {config_path}: {e}")
    return {}


class Settings:
    """Application settings loaded from /data/config.json or environment variables."""

    # Load config file
    _config = load_config_file()

    # Database
    DATABASE_URL: str = (
        _config.get("database", {}).get("url") or
        os.getenv("DATABASE_URL") or
        "postgresql://raguser:ragpassword@postgres:5432/ragdb"
    )

    # LLM Providers - OpenRouter
    OPENROUTER_API_KEY: str = (
        _config.get("llm_providers", {}).get("openrouter", {}).get("api_key") or
        os.getenv("OPENROUTER_API_KEY") or
        ""
    )
    OPENROUTER_BASE_URL: str = (
        _config.get("llm_providers", {}).get("openrouter", {}).get("base_url") or
        "https://openrouter.ai/api/v1"
    )
    OPENROUTER_DEFAULT_MODEL: str = (
        _config.get("llm_providers", {}).get("openrouter", {}).get("default_model") or
        "xai/grok-beta"
    )

    # LLM Providers - Anthropic (via OpenRouter)
    ANTHROPIC_API_KEY: str = (
        _config.get("llm_providers", {}).get("anthropic", {}).get("api_key") or
        os.getenv("ANTHROPIC_API_KEY") or
        OPENROUTER_API_KEY  # Fallback to OpenRouter key
    )
    ANTHROPIC_BASE_URL: str = (
        _config.get("llm_providers", {}).get("anthropic", {}).get("base_url") or
        "https://openrouter.ai/api/v1"  # Use OpenRouter for Anthropic models
    )
    ANTHROPIC_DEFAULT_MODEL: str = (
        _config.get("llm_providers", {}).get("anthropic", {}).get("default_model") or
        "anthropic/claude-3.5-sonnet"  # OpenRouter model name
    )

    # Legacy LLM Model (fallback)
    LLM_MODEL: str = os.getenv("LLM_MODEL", OPENROUTER_DEFAULT_MODEL)

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
    AUTH_FILE_PATH: str = "/data/auth"

    def validate(self) -> bool:
        """Validate required settings."""
        if not self.OPENROUTER_API_KEY and not self.ANTHROPIC_API_KEY:
            print("Warning: No API keys configured for LLM providers")
            print("Please set API keys in /data/config.json or environment variables")
            return False
        return True


settings = Settings()
