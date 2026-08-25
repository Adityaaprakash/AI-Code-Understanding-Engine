# backend/db/session.py
"""
Async SQLAlchemy engine and session factory.

Usage (application code — TASK-1D will wire this into FastAPI dependency injection):

    from backend.db.session import async_session_factory

    async with async_session_factory() as session:
        result = await session.execute(select(Repository))
        repos = result.scalars().all()

The engine is created lazily from DatabaseSettings so that import of this
module does not require a live database connection.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.db.config import db_settings

# ──────────────────────────────────────────────────────────────────────────────
# Engine
# One engine per process. Pool settings are conservative defaults;
# tune via environment variables when needed.
# ──────────────────────────────────────────────────────────────────────────────
engine: AsyncEngine = create_async_engine(
    db_settings.require_database_url(),
    echo=False,  # set echo=True in dev to log all SQL
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # discard stale connections automatically
)

# ──────────────────────────────────────────────────────────────────────────────
# Session factory
# expire_on_commit=False: keep attribute access after commit without re-query.
# ──────────────────────────────────────────────────────────────────────────────
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async generator yielding a database session.

    Intended for use as a FastAPI dependency (TASK-1D).
    Can also be used directly as an async context manager in worker code.

    Example (FastAPI):
        @router.get("/repos")
        async def list_repos(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
