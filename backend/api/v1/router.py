# backend/api/v1/router.py
"""API v1 router foundation.

Business endpoints (repositories, queries, symbols, impact analysis) will be
attached to this router in future development tasks (Phase 2 through Phase 7).
"""

from typing import Any

from fastapi import APIRouter

from backend.api.v1.graph import router as graph_router
from backend.api.v1.impact import router as impact_router
from backend.api.v1.query import router as query_router
from backend.api.v1.repositories import router as repositories_router
from backend.api.v1.symbols import router as symbols_router

api_v1_router = APIRouter()

api_v1_router.include_router(repositories_router)
api_v1_router.include_router(query_router)
api_v1_router.include_router(symbols_router)
api_v1_router.include_router(graph_router)
api_v1_router.include_router(impact_router)


@api_v1_router.get("", summary="API v1 root info", response_model=dict[str, Any])
@api_v1_router.get(
    "/", summary="API v1 root info", response_model=dict[str, Any], include_in_schema=False
)
async def api_v1_root() -> dict[str, Any]:
    """Root metadata endpoint for API v1."""
    return {
        "message": "CodeLens AI API v1",
        "status": "active",
        "version": "v1",
    }


__all__ = ["api_v1_router"]
