# alembic/env.py
"""
Alembic migration environment — async PostgreSQL setup.

Configuration is sourced exclusively from backend.db.config.DatabaseSettings
(which reads from the .env file / environment variables).  No credentials
are hardcoded here.

This env.py supports both:
    alembic upgrade head      (async migration runner)
    alembic downgrade base    (async migration runner)
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import TYPE_CHECKING

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

import backend.db.models  # noqa: F401 — registers all models onto Base.metadata
from alembic import context
from backend.db.base import Base
from backend.db.config import db_settings

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

# Alembic Config object (gives access to alembic.ini values)
config = context.config

# Override sqlalchemy.url from application settings — never use alembic.ini value
database_url = db_settings.require_database_url()
config.set_main_option("sqlalchemy.url", database_url)

# Set up Python logging from alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = Base.metadata


# ──────────────────────────────────────────────────────────────────────────────
# Offline migrations (generate SQL script without connecting to DB)
# ──────────────────────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL without connecting."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ──────────────────────────────────────────────────────────────────────────────
# Online migrations (connect to a live database)
# ──────────────────────────────────────────────────────────────────────────────
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations inside a sync-bridge."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # no pool for migration runs
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using the async engine."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
