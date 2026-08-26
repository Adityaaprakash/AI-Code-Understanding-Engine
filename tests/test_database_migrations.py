"""Optional real-PostgreSQL verification for the TASK-1C migration lifecycle."""

import asyncio
import os
import subprocess
import sys

import asyncpg
import pytest

EXPECTED_TABLES = {
    "repositories",
    "commits",
    "files",
    "symbols",
    "chunks",
    "jobs",
    "index_versions",
}


def _postgres_url(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _table_names(database_url: str) -> set[str]:
    connection = await asyncpg.connect(_postgres_url(database_url))
    try:
        rows = await connection.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        return {row["tablename"] for row in rows}
    finally:
        await connection.close()


@pytest.mark.db
@pytest.mark.integration
@pytest.mark.skipif(
    "DATABASE_URL" not in os.environ,
    reason="requires DATABASE_URL for a real PostgreSQL integration test",
)
def test_initial_migration_upgrade_downgrade_upgrade_lifecycle() -> None:
    """Run the lifecycle against PostgreSQL; SQLite and mocks are never used."""
    database_url = os.environ["DATABASE_URL"]
    command = [sys.executable, "-m", "alembic"]

    for revision in ("head", "base", "head"):
        action = "downgrade" if revision == "base" else "upgrade"
        subprocess.run([*command, action, revision], check=True)

    tables = asyncio.run(_table_names(database_url))
    assert {t for t in tables if t != "alembic_version"} == EXPECTED_TABLES
