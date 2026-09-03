# backend/schemas/graph.py
"""Schemas for Phase 3 Identity Mapping, Traversal, and Impact Analysis APIs."""

import uuid

from pydantic import BaseModel


class SymbolResponseItem(BaseModel):
    """Metadata for a resolved code symbol."""

    node_id: str
    name: str
    qualified_name: str
    kind: str
    file_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    language: str | None = None


class SymbolSearchResponse(BaseModel):
    """Response containing a list of matched symbols."""

    repository_id: uuid.UUID
    query: str
    results: list[SymbolResponseItem]


class GraphEdgeSchema(BaseModel):
    source_id: str
    target_id: str
    kind: str


class GraphTraversalResponse(BaseModel):
    """Response containing graph traversal nodes and edges."""

    source_node_id: str
    depth: int
    nodes: list[SymbolResponseItem]
    edges: list[GraphEdgeSchema]


class ImpactNodeSchema(SymbolResponseItem):
    impact_score: float
    categories: list[str]


class ImpactAnalysisResponse(BaseModel):
    """Response characterizing the blast radius of a code change."""

    source_node_id: str
    depth: int
    impacted_nodes: list[ImpactNodeSchema]
    total_impact_score: float
