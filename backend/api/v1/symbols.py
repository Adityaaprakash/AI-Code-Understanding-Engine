# backend/api/v1/symbols.py
"""API Router for Symbol resolution and search (Phase 3)."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import AppException
from backend.db.models.repository import Repository
from backend.db.session import get_db_session
from backend.schemas.graph import SymbolSearchResponse
from backend.services.graph_service import graph_service

router = APIRouter(prefix="/symbols", tags=["Symbols"])


@router.get(
    "",
    summary="Search for code symbols",
    response_model=SymbolSearchResponse,
)
async def search_symbols(
    query: str, repository_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
) -> SymbolSearchResponse:
    """Resolve and identify symbols within a repository."""
    db_repo = await session.get(Repository, repository_id)
    if not db_repo:
        raise AppException(
            "Repository not found", code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND
        )

    results = graph_service.search_symbols(query, str(repository_id))
    return SymbolSearchResponse(repository_id=repository_id, query=query, results=results)
