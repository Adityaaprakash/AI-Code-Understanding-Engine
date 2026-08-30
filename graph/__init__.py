"""Code Knowledge Graph package (Phase 3).

Provides language-independent graph schema, models, edges, containers,
storage engines, traversal query engines, and abstract contracts for symbol resolution,
relationship extraction, graph persistence, traversal, and impact analysis.
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
from graph.query_engine import DEPENDENCY_EDGE_KINDS, GraphQueryEngine
from graph.store import InMemoryGraphStore

__all__ = [
    "DEPENDENCY_EDGE_KINDS",
    "CodeGraph",
    "EdgeKind",
    "GraphBuilderContract",
    "GraphEdge",
    "GraphNode",
    "GraphQueryEngine",
    "GraphQueryEngineContract",
    "GraphStoreContract",
    "ImportResolverContract",
    "InMemoryGraphStore",
    "NodeKind",
    "ReferenceResolverContract",
    "RelationshipExtractorContract",
    "ResolutionStatus",
    "SymbolRegistrarContract",
    "generate_edge_id",
]
