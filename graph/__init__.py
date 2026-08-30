"""Code Knowledge Graph package (Phase 3).

Provides language-independent graph schema, models, edges, containers,
storage engines, traversal query engines, impact analyzers, and abstract contracts for symbol resolution,
relationship extraction, graph persistence, traversal, and initial impact analysis.
"""

from graph.contracts import (
    GraphBuilderContract,
    GraphQueryEngineContract,
    GraphStoreContract,
    ImpactAnalyzerContract,
    ImportResolverContract,
    ReferenceResolverContract,
    RelationshipExtractorContract,
    SymbolRegistrarContract,
)
from graph.edges import GraphEdge, generate_edge_id
from graph.enums import EdgeKind, NodeKind, ResolutionStatus
from graph.impact_analyzer import (
    ImpactAnalysisResult,
    ImpactAnalyzer,
    ImpactedNode,
    ImpactPath,
    ImpactPathStep,
)
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
    "ImpactAnalysisResult",
    "ImpactAnalyzer",
    "ImpactAnalyzerContract",
    "ImpactPath",
    "ImpactPathStep",
    "ImpactedNode",
    "ImportResolverContract",
    "InMemoryGraphStore",
    "NodeKind",
    "ReferenceResolverContract",
    "RelationshipExtractorContract",
    "ResolutionStatus",
    "SymbolRegistrarContract",
    "generate_edge_id",
]
