# tests/conftest.py
"""
Reusable pytest fixtures for the AI Code Understanding Engine.

Provides:
  - `app_instance`: Fresh FastAPI application instance.
  - `async_client`: Asynchronous httpx.AsyncClient connected via ASGITransport.
  - `sync_client`: Synchronous FastAPI TestClient instance.
  - `database_url`: PostgreSQL DSN from environment or db_settings.
  - `db_engine`: Async SQLAlchemy engine instance connected to PostgreSQL.
  - `db_session`: Transactional AsyncSession with automatic rollback for test isolation.
"""

import os
from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.db.config import db_settings
from backend.main import create_app


@pytest.fixture
def app_instance() -> FastAPI:
    """Provide a fresh FastAPI application instance for testing."""
    return create_app()


@pytest.fixture
def sync_client(app_instance: FastAPI) -> TestClient:
    """Provide a synchronous Starlette/FastAPI TestClient instance."""
    return TestClient(app_instance)


@pytest.fixture
async def async_client(app_instance: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous httpx.AsyncClient wired to the FastAPI application."""
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture(scope="session")
def database_url() -> str | None:
    """Return the PostgreSQL connection URL from DATABASE_URL env var or db_settings."""
    url = os.getenv("DATABASE_URL")
    if not url:
        try:
            url = db_settings.require_database_url()
        except RuntimeError:
            return None
    return url


@pytest.fixture
async def db_engine(database_url: str | None) -> AsyncGenerator[AsyncEngine | None, None]:
    """
    Provide an async SQLAlchemy engine connected to PostgreSQL.
    Yields None if PostgreSQL is unconfigured or unreachable.
    """
    if not database_url:
        yield None
        return

    engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        yield engine
    except Exception:
        yield None
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine | None) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a transactional AsyncSession for database integration tests.
    Skips the test if PostgreSQL is unreachable.
    Rolls back the outer transaction upon test completion for 100% test isolation.
    """
    if db_engine is None:
        pytest.skip("PostgreSQL database is unreachable or DATABASE_URL is unconfigured")

    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        async with session_factory(bind=connection) as session:
            try:
                yield session
            finally:
                await session.close()
                if transaction.is_active:
                    await transaction.rollback()
