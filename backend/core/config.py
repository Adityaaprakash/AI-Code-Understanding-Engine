# backend/core/config.py
"""
Application-wide configuration settings loaded from environment variables.

Uses Pydantic Settings (v2) to read configuration from `.env` or system environment.
Integrates with `db_settings` from `backend.db.config` to maintain a single source
of truth for database configuration.
"""

import json
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.db.config import db_settings


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
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000", "http://localhost:5173"])

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse a comma-separated string, JSON string, or list of origins."""
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    parsed = json.loads(v_str)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed]
                except Exception:
                    pass
            if not v_str:
                return []
            return [origin.strip() for origin in v_str.split(",")]
        if isinstance(v, list):
            return [str(origin).strip() for origin in v]
        return []


# Singleton settings instance
settings = Settings()

__all__ = ["Settings", "db_settings", "settings"]
