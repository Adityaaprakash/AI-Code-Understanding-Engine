# backend/api/v1/impact.py
"""API Router for Impact Analysis (Phase 3 blast radius)."""

from fastapi import APIRouter

from backend.schemas.graph import ImpactAnalysisResponse
from backend.services.graph_service import graph_service

router = APIRouter(prefix="/impact", tags=["Impact Analysis"])


@router.get(
    "",
    summary="Calculate change impact radius",
    response_model=ImpactAnalysisResponse,
)
async def get_impact_analysis(source_node_id: str, depth: int = 3) -> ImpactAnalysisResponse:
    """Compute the reverse blast radius of modifying a specific node."""
    return graph_service.analyze_impact(source_node_id, depth)
