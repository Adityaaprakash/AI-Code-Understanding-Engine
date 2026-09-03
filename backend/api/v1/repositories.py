# backend/api/v1/repositories.py
"""API Router for managing repositories and triggering indexing jobs."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import AppException
from backend.db.models.job import Job
from backend.db.models.repository import Repository
from backend.db.session import get_db_session
from backend.schemas.repositories import JobResponse, RepositoryCreate, RepositoryResponse

router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.post(
    "",
    summary="Add a new repository",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_repository(
    repo_in: RepositoryCreate, session: AsyncSession = Depends(get_db_session)
) -> RepositoryResponse:
    """Register a new repository to the CodeLens AI system."""
    if repo_in.source_type not in ("github", "local"):
        raise AppException(
            message="source_type must be 'github' or 'local'",
            code="INVALID_SOURCE_TYPE",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    db_repo = Repository(
        name=repo_in.name,
        source_type=repo_in.source_type,
        url=repo_in.url,
        local_path=repo_in.local_path,
        default_branch=repo_in.default_branch,
        status="pending",
    )
    session.add(db_repo)
    await session.commit()
    await session.refresh(db_repo)
    return db_repo  # type: ignore


@router.get(
    "",
    summary="List all repositories",
    response_model=list[RepositoryResponse],
)
async def list_repositories(
    session: AsyncSession = Depends(get_db_session),
) -> list[RepositoryResponse]:
    """Retrieve all tracked repositories."""
    result = await session.execute(select(Repository).order_by(Repository.created_at.desc()))
    return result.scalars().all()  # type: ignore


@router.get(
    "/{repo_id}",
    summary="Get a repository by ID",
    response_model=RepositoryResponse,
)
async def get_repository(
    repo_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
) -> RepositoryResponse:
    """Retrieve repository metadata by its ID."""
    db_repo = await session.get(Repository, repo_id)
    if not db_repo:
        raise AppException(
            "Repository not found", code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND
        )
    return db_repo  # type: ignore


@router.post(
    "/{repo_id}/index",
    summary="Trigger an indexing job for a repository",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_indexing(
    repo_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
) -> JobResponse:
    """Create an asynchronous job to index the repository."""
    db_repo = await session.get(Repository, repo_id)
    if not db_repo:
        raise AppException(
            "Repository not found", code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND
        )

    # Note: We rely on the async backend worker to pick this up via DB
    job = Job(
        repository_id=db_repo.id,
        kind="full_index",
        status="pending",
        payload={"branch": db_repo.default_branch},
    )
    session.add(job)

    db_repo.status = "indexing"  # Optimistic state update

    await session.commit()
    await session.refresh(job)
    return job  # type: ignore


@router.get(
    "/{repo_id}/index-status",
    summary="Get indexing jobs for a repository",
    response_model=list[JobResponse],
)
async def get_index_status(
    repo_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
) -> list[JobResponse]:
    """Retrieve the recent indexing jobs for a repository to monitor progress."""
    # Ensure repo exists
    db_repo = await session.get(Repository, repo_id)
    if not db_repo:
        raise AppException(
            "Repository not found", code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND
        )

    result = await session.execute(
        select(Job).where(Job.repository_id == repo_id).order_by(Job.scheduled_at.desc())
    )
    return result.scalars().all()  # type: ignore
