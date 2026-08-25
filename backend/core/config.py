# backend/core/config.py
"""
Application-wide configuration settings loaded from environment variables.

Uses Pydantic Settings (v2) to read configuration from `.env` or system environment.
Integrates with `db_settings` from `backend.db.config` to maintain a single source
of truth for database configuration.
"""

from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.db.config import db_settings


def parse_cors_origins(v: list[str] | str) -> list[str]:
    """Parse a comma-separated string or list of origins into a list of strings."""
    if isinstance(v, str):
        if not v.strip():
            return []
        return [origin.strip() for origin in v.split(",")]
    return v


CorsOrigins = Annotated[list[str], BeforeValidator(parse_cors_origins)]


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App Metadata
    APP_NAME: str = "CodeLens AI — AI Code Understanding Engine"
    APP_ENV: str = Field(default="development")
    APP_SECRET_KEY: str = Field(default="changeme")
    APP_PORT: int = Field(default=8000)

    # API Routing
    API_V1_STR: str = "/api/v1"

    # CORS
    CORS_ORIGINS: CorsOrigins = Field(default=["http://localhost:3000", "http://localhost:5173"])


# Singleton settings instance
settings = Settings()

__all__ = ["Settings", "db_settings", "settings"]
