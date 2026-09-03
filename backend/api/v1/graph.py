# backend/api/v1/graph.py
"""API Router for Knowledge Graph structural exploration."""

from fastapi import APIRouter

from backend.schemas.graph import GraphTraversalResponse
from backend.services.graph_service import graph_service

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])


@router.get(
    "",
    summary="Traverse the Knowledge Graph",
    response_model=GraphTraversalResponse,
)
async def traverse_graph(source_node_id: str, depth: int = 1) -> GraphTraversalResponse:
    """Explore structural and semantic graph relationships from a root node."""
    return graph_service.traverse(source_node_id, depth)
