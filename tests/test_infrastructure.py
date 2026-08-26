# tests/test_infrastructure.py
"""
Test infrastructure verification suite.

Validates that:
  - pytest markers (@pytest.mark.unit, @pytest.mark.api, @pytest.mark.db, @pytest.mark.integration) work properly.
  - app_instance fixture instantiates valid FastAPI app.
  - async_client fixture sends async HTTP requests to the app.
  - db_session fixture provides transactional isolation and rollback against PostgreSQL.
"""

from uuid import uuid4

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.repository import Repository


@pytest.mark.unit
def test_app_instance_fixture(app_instance: FastAPI) -> None:
    """Verify app_instance fixture produces configured FastAPI app."""
    assert isinstance(app_instance, FastAPI)
    assert app_instance.title == "CodeLens AI — AI Code Understanding Engine"


@pytest.mark.api
@pytest.mark.unit
async def test_async_client_fixture(async_client: AsyncClient) -> None:
    """Verify async_client fixture communicates asynchronously with endpoints."""
    health_res = await async_client.get("/health")
    assert health_res.status_code == status.HTTP_200_OK
    assert health_res.json()["status"] == "ok"

    v1_res = await async_client.get("/api/v1")
    assert v1_res.status_code == status.HTTP_200_OK
    assert v1_res.json()["status"] == "active"


@pytest.mark.db
@pytest.mark.integration
async def test_db_session_fixture_isolation_step_1(db_session: AsyncSession) -> None:
    """Verify db_session allows ORM object creation and querying within transaction."""
    test_repo = Repository(
        name="test-infra-repo-1",
        source_type="local",
        local_path="/tmp/test-infra-repo-1",
        default_branch="main",
    )
    db_session.add(test_repo)
    await db_session.flush()
    assert test_repo.id is not None

    stmt = select(Repository).where(Repository.name == "test-infra-repo-1")
    result = await db_session.execute(stmt)
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.local_path == "/tmp/test-infra-repo-1"


@pytest.mark.db
@pytest.mark.integration
async def test_db_session_fixture_isolation_step_2(db_session: AsyncSession) -> None:
    """Verify that previous test's transaction rolled back cleanly (test isolation)."""
    stmt = select(Repository).where(Repository.name == "test-infra-repo-1")
    result = await db_session.execute(stmt)
    fetched = result.scalar_one_or_none()
    assert fetched is None, "Transaction rollback failed: repository from previous test persisted!"


@pytest.mark.db
@pytest.mark.integration
async def test_db_session_commit_and_query_scope(db_session: AsyncSession) -> None:
    """Verify unique object creation inside isolated db_session."""
    unique_name = f"test-repo-{uuid4().hex[:8]}"
    test_repo = Repository(
        name=unique_name,
        source_type="local",
        local_path=f"/tmp/{unique_name}",
        default_branch="main",
    )
    db_session.add(test_repo)
    await db_session.flush()

    stmt = select(Repository).where(Repository.name == unique_name)
    res = await db_session.execute(stmt)
    assert res.scalar_one() is not None
