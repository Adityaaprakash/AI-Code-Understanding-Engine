"""Code Knowledge Graph package (Phase 3).

Provides language-independent graph schema, models, edges, containers,
and abstract contracts for symbol resolution, relationship extraction,
graph persistence, traversal, and impact analysis.
"""

from graph.contracts import (
    GraphBuilderContract,
    GraphQueryEngineContract,
    GraphStoreContract,
    ImportResolverContract,
    ReferenceResolverContract,
    RelationshipExtractorContract,
    SymbolRegistrarContract,
)
from graph.edges import GraphEdge, generate_edge_id
from graph.enums import EdgeKind, NodeKind, ResolutionStatus
from graph.models import CodeGraph
from graph.nodes import GraphNode

__all__ = [
    "CodeGraph",
    "EdgeKind",
    "GraphBuilderContract",
    "GraphEdge",
    "GraphNode",
    "GraphQueryEngineContract",
    "GraphStoreContract",
    "ImportResolverContract",
    "NodeKind",
    "ReferenceResolverContract",
    "RelationshipExtractorContract",
    "ResolutionStatus",
    "SymbolRegistrarContract",
    "generate_edge_id",
]
