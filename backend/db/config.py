# backend/db/config.py
"""
Database configuration loaded from environment variables via pydantic-settings.

The single authoritative source of database connection configuration for both
the FastAPI application and the Alembic migration environment.

Environment variables (see .env.example):
    DATABASE_URL — required asyncpg DSN, e.g.
                   postgresql+asyncpg://codelens:secret@localhost:5432/codelens
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database connection settings sourced from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unrelated env vars
    )

    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")

    def require_database_url(self) -> str:
        """Return the configured URL or fail before a database connection is attempted."""
        if self.database_url is None:
            message = "DATABASE_URL must be configured with a postgresql+asyncpg URL"
            raise RuntimeError(message)
        return self.database_url


# Module-level singleton — import this in session.py and alembic/env.py
db_settings = DatabaseSettings()
