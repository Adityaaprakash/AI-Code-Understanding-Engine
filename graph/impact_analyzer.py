"""Impact Analyzer module for Phase 3 Code Knowledge Graph (Task 3H).

Provides production-quality, graph-derived impact analysis and structured explanation paths.
Calculates direct vs transitive impact, minimum impact depth, edge-filtered blast radius,
and deterministic path structures without reparsing source code or performing fuzzy name matching.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from code_analyzer.ir import SourceLocation  # noqa: TC001
from graph.contracts import ImpactAnalyzerContract
from graph.enums import EdgeKind, NodeKind  # noqa: TC001
from graph.query_engine import (
    DEPENDENCY_EDGE_KINDS,
    GraphQueryEngine,
    _get_inbound_from_graph,
    _get_node_from_graph,
)

if TYPE_CHECKING:
    from graph.models import CodeGraph
    from graph.nodes import GraphNode
    from graph.store import InMemoryGraphStore


class ImpactPathStep(BaseModel):
    """Represents a single directed step in an impact explanation path.

    Reflects the original stored edge direction (source_id -> target_id via kind).
    In an impact context, source_id is the dependent symbol and target_id is the dependency.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(description="Source symbol node ID (the dependent entity)")
    target_id: str = Field(description="Target symbol node ID (the dependency entity)")
    kind: EdgeKind = Field(description="Semantic EdgeKind of the stored relationship")
    edge_id: str | None = Field(default=None, description="Graph edge identifier if available")


class ImpactPath(BaseModel):
    """Represents a full multi-hop traversal path from the root symbol to an impacted dependent node."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_id: str = Field(description="Final impacted symbol node ID at the end of this path")
    depth: int = Field(description="Number of graph hops from root symbol to target_id")
    node_ids: list[str] = Field(description="Ordered sequence of node IDs from root to target_id")
    steps: list[ImpactPathStep] = Field(description="Ordered sequence of ImpactPathStep transitions along the path")


class ImpactedNode(BaseModel):
    """Represents a single impacted symbol node and its metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol_id: str = Field(description="Unique graph node ID of the impacted symbol")
    name: str | None = Field(default=None, description="Simple name of the impacted symbol if available")
    qualified_name: str | None = Field(default=None, description="Fully qualified name if available")
    node_kind: NodeKind = Field(description="NodeKind (e.g. CLASS, METHOD, FUNCTION, FILE)")
    file_id: str | None = Field(default=None, description="File ID declaring this symbol if applicable")
    location: SourceLocation | None = Field(default=None, description="Source location metadata")
    minimum_depth: int = Field(description="Shortest impact distance (minimum hops) from root symbol")
    relationship_types: list[EdgeKind] = Field(
        description="Sorted list of unique EdgeKinds directly or transitively connecting root to this node"
    )

    @classmethod
    def from_graph_node(
        cls,
        node: GraphNode,
        minimum_depth: int,
        relationship_types: list[EdgeKind] | set[EdgeKind],
    ) -> ImpactedNode:
        """Construct an ImpactedNode from a GraphNode instance."""
        sorted_kinds = sorted(set(relationship_types), key=lambda k: k.value)
        return cls(
            symbol_id=node.id,
            name=node.name,
            qualified_name=node.qualified_name,
            node_kind=node.kind,
            file_id=node.file_id,
            location=node.location,
            minimum_depth=minimum_depth,
            relationship_types=sorted_kinds,
        )


class ImpactAnalysisResult(BaseModel):
    """Container model for complete, structured impact analysis results."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository_id: str | None = Field(default=None, description="Repository ID of the analyzed graph")
    root_symbol_id: str = Field(description="Symbol ID of the modified root node")
    root_name: str | None = Field(default=None, description="Simple name of the modified root node if available")
    root_qualified_name: str | None = Field(default=None, description="Qualified name of the modified root node")
    root_node_kind: NodeKind = Field(description="NodeKind of the modified root node")
    max_depth: int | None = Field(default=None, description="Max depth limit used during analysis (None = unlimited)")
    total_impacted: int = Field(description="Total number of unique impacted dependent nodes")
    impacted_nodes: list[ImpactedNode] = Field(
        description="List of impacted dependent nodes, sorted deterministically by (minimum_depth, symbol_id)"
    )
    paths: list[ImpactPath] = Field(
        description="List of impact explanation paths from root to impacted nodes, sorted deterministically"
    )

    @property
    def impacted_symbol_ids(self) -> list[str]:
        """Convenience accessor returning list of unique impacted symbol IDs."""
        return [node.symbol_id for node in self.impacted_nodes]

    def get_impacted_node(self, symbol_id: str) -> ImpactedNode | None:
        """Lookup an ImpactedNode by symbol_id."""
        for node in self.impacted_nodes:
            if node.symbol_id == symbol_id:
                return node
        return None

    def get_paths_for_node(self, symbol_id: str) -> list[ImpactPath]:
        """Lookup all impact explanation paths terminating at symbol_id."""
        return [p for p in self.paths if p.target_id == symbol_id]


class ImpactAnalyzer(ImpactAnalyzerContract):
    """Deterministic, graph-based Impact Analyzer operating on the Code Knowledge Graph."""

    def __init__(self, query_engine: GraphQueryEngine | None = None) -> None:
        self.query_engine = query_engine or GraphQueryEngine()

    def analyze_impact(
        self,
        node_id: str,
        graph: CodeGraph | InMemoryGraphStore,
        max_depth: int | None = None,
        edge_kinds: set[EdgeKind] | list[EdgeKind] | None = None,
    ) -> ImpactAnalysisResult:
        """Compute structured impact analysis result for a modified symbol node.

        Traverses reverse dependency edges (inbound edges where source depends on target)
        using BFS to ensure minimum-depth calculation and cycle-safe path extraction.
        """
        root_node = _get_node_from_graph(graph, node_id)
        if root_node is None:
            raise KeyError(f"Root node '{node_id}' not found in graph.")

        allowed_kinds = set(edge_kinds) if edge_kinds is not None else set(DEPENDENCY_EDGE_KINDS)

        # Handle max_depth = 0 edge case: 0 impacted nodes
        if max_depth is not None and max_depth == 0:
            return ImpactAnalysisResult(
                repository_id=getattr(graph, "repository_id", None),
                root_symbol_id=root_node.id,
                root_name=root_node.name,
                root_qualified_name=root_node.qualified_name,
                root_node_kind=root_node.kind,
                max_depth=0,
                total_impacted=0,
                impacted_nodes=[],
                paths=[],
            )

        # BFS Data Structures
        min_depth_map: dict[str, int] = {}
        rel_types_map: dict[str, set[EdgeKind]] = {}
        node_map: dict[str, GraphNode] = {}
        all_paths: list[ImpactPath] = []

        # Queue elements: (curr_node_id, curr_depth, curr_path_node_ids, curr_path_steps)
        queue: deque[tuple[str, int, list[str], list[ImpactPathStep]]] = deque()
        queue.append((node_id, 0, [node_id], []))

        # Track visited path tuples to prevent duplicate path loops
        visited_path_tuples: set[tuple[str, ...]] = set()

        while queue:
            curr_id, curr_depth, path_nodes, path_steps = queue.popleft()

            if max_depth is not None and curr_depth >= max_depth:
                continue

            inbound_edges = _get_inbound_from_graph(graph, curr_id)

            for edge in inbound_edges:
                if edge.kind not in allowed_kinds:
                    continue

                dependent_id = edge.source_id  # The node that depends on curr_id

                # Self-loop protection & Root exclusion: do not treat root itself as an impacted dependent
                if dependent_id == node_id:
                    continue

                # Cycle safety on current path: prevent infinite loop recursion
                if dependent_id in path_nodes:
                    continue

                next_depth = curr_depth + 1
                dependent_node = _get_node_from_graph(graph, dependent_id)
                if dependent_node is None:
                    continue

                # Save node reference
                node_map[dependent_id] = dependent_node

                # Update minimum depth
                if dependent_id not in min_depth_map or next_depth < min_depth_map[dependent_id]:
                    min_depth_map[dependent_id] = next_depth

                # Update relationship types
                rel_types_map.setdefault(dependent_id, set()).add(edge.kind)

                # Create step preserving original stored edge direction (source_id -> target_id via kind)
                step = ImpactPathStep(
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    kind=edge.kind,
                    edge_id=edge.id,
                )

                new_path_nodes = [*path_nodes, dependent_id]
                new_path_steps = [*path_steps, step]
                path_tuple = tuple(new_path_nodes)

                if path_tuple in visited_path_tuples:
                    continue
                visited_path_tuples.add(path_tuple)

                impact_path = ImpactPath(
                    target_id=dependent_id,
                    depth=next_depth,
                    node_ids=new_path_nodes,
                    steps=new_path_steps,
                )
                all_paths.append(impact_path)

                queue.append((dependent_id, next_depth, new_path_nodes, new_path_steps))

        # Build ImpactedNode list
        impacted_nodes: list[ImpactedNode] = []
        for sid, node in node_map.items():
            impacted_nodes.append(
                ImpactedNode.from_graph_node(
                    node=node,
                    minimum_depth=min_depth_map[sid],
                    relationship_types=rel_types_map[sid],
                )
            )

        # Deterministic sorting
        # Sort impacted_nodes by minimum_depth ascending, then symbol_id ascending
        impacted_nodes.sort(key=lambda n: (n.minimum_depth, n.symbol_id))

        # Sort paths by depth ascending, target_id ascending, then node_ids tuple
        all_paths.sort(key=lambda p: (p.depth, p.target_id, tuple(p.node_ids)))

        return ImpactAnalysisResult(
            repository_id=getattr(graph, "repository_id", None),
            root_symbol_id=root_node.id,
            root_name=root_node.name,
            root_qualified_name=root_node.qualified_name,
            root_node_kind=root_node.kind,
            max_depth=max_depth,
            total_impacted=len(impacted_nodes),
            impacted_nodes=impacted_nodes,
            paths=all_paths,
        )
