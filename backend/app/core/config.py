"""
Application Configuration using Pydantic Settings.

All settings are loaded from environment variables or .env file.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl


class Settings(BaseSettings):
    """
    Central configuration class.
    Values are read from environment variables (case-insensitive).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "CodeBattle"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Security / JWT ────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-at-least-32-characters-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://codebattle:codebattle_password@localhost:5432/codebattle_db"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # ── Frontend ──────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Matchmaking ───────────────────────────────────────────────────────────
    MATCHMAKING_RATING_RANGE: int = 100      # ±100 rating for opponent search
    MATCHMAKING_TIMEOUT_SECONDS: int = 60    # Give up after 60s
    MATCHMAKING_POLL_INTERVAL: int = 2       # Check queue every 2s


# Singleton settings instance used throughout the application
settings = Settings()
