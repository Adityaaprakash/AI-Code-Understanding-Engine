# backend/api/v1/query.py
"""API Router for codebase search and chat."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import AppException
from backend.db.models.repository import Repository
from backend.db.session import get_db_session
from backend.schemas.query import (
    GroundedAnswerResponse,
    QueryRequest,
    QueryResponse,
    SearchResultItem,
)
from backend.services.query import query_service

router = APIRouter(prefix="/query", tags=["Query and Search"])


@router.post(
    "",
    summary="Execute a code search or grounded chat query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
)
async def process_query(
    request: QueryRequest, session: AsyncSession = Depends(get_db_session)
) -> QueryResponse:
    """Execute a retrieved structural search and optional LLM context assembly.

    Leverages Phase 5 and Phase 6 internal capabilities.
    """
    repo_id_str = str(request.repository_id)

    # 1. Enforce Repository Isolation
    db_repo = await session.get(Repository, request.repository_id)
    if not db_repo:
        raise AppException(
            "Repository not found", code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND
        )

    # 2. Extract Phase 5 and 6 results
    ui_results, ui_answer = query_service.process_query(
        query=request.query,
        repository_id=repo_id_str,
        top_k=request.top_k,
        generate_answer=request.generate_answer,
    )

    plan = query_service.planner.plan(request.query)

    answer_resp = None
    if ui_answer:
        answer_resp = GroundedAnswerResponse(**ui_answer)

    return QueryResponse(
        repository_id=request.repository_id,
        query=plan.query,
        normalized_query=plan.normalized_query,
        intent=plan.primary_intent.value
        if hasattr(plan.primary_intent, "value")
        else str(plan.primary_intent),
        results=[SearchResultItem(**r) for r in ui_results],
        answer=answer_resp,
    )
