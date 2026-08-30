"""Graph traversal and query engine implementation for Code Knowledge Graph."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Literal

from graph.contracts import GraphQueryEngineContract
from graph.enums import EdgeKind

if TYPE_CHECKING:
    from collections.abc import Iterable

    from graph.edges import GraphEdge
    from graph.models import CodeGraph
    from graph.nodes import GraphNode
    from graph.store import InMemoryGraphStore

# ──────────────────────────────────────────────────────────────────────────────
# Default Semantic Dependency Edge Policy
# Excludes structural containment edges (DECLARES, CONTAINS, EXPORTS)
# ──────────────────────────────────────────────────────────────────────────────

DEPENDENCY_EDGE_KINDS: frozenset[EdgeKind] = frozenset(
    [
        EdgeKind.IMPORTS,
        EdgeKind.USES,
        EdgeKind.CALLS,
        EdgeKind.REFERENCES,
        EdgeKind.EXTENDS,
        EdgeKind.IMPLEMENTS,
        EdgeKind.TYPED_AS,
        EdgeKind.READS,
        EdgeKind.WRITES,
        EdgeKind.FIELD_ACCESS,
    ]
)


def _get_node_from_graph(graph: CodeGraph | InMemoryGraphStore, node_id: str) -> GraphNode | None:
    """Helper to extract a node by ID from either CodeGraph or InMemoryGraphStore."""
    if hasattr(graph, "get_node"):
        return graph.get_node(node_id)
    return None


def _get_outbound_from_graph(
    graph: CodeGraph | InMemoryGraphStore, source_id: str, kind: EdgeKind | None = None
) -> list[GraphEdge]:
    """Helper to retrieve outbound edges from CodeGraph or InMemoryGraphStore."""
    return graph.get_outbound_edges(source_id, kind=kind)


def _get_inbound_from_graph(
    graph: CodeGraph | InMemoryGraphStore, target_id: str, kind: EdgeKind | None = None
) -> list[GraphEdge]:
    """Helper to retrieve inbound edges from CodeGraph or InMemoryGraphStore."""
    return graph.get_inbound_edges(target_id, kind=kind)


def _sort_nodes_deterministically(nodes: Iterable[GraphNode]) -> list[GraphNode]:
    """Sort a collection of GraphNode instances deterministically.

    Primary sort key: (node.kind.value, node.qualified_name, node.id).
    """
    return sorted(
        nodes,
        key=lambda n: (
            n.kind.value,
            n.qualified_name or "",
            n.id,
        ),
    )


class GraphQueryEngine(GraphQueryEngineContract):
    """Engine for performing graph traversals, caller/callee queries, and dependency/impact analysis.

    Operates purely on GraphNode and GraphEdge data without invoking parsers,
    symbol resolution, or language-specific logic.
    """

    # ──────────────────────────────────────────────────────────────────────────
    # Generic Edge & Neighbor Queries
    # ──────────────────────────────────────────────────────────────────────────

    def get_outbound_edges(
        self,
        node_id: str,
        graph: CodeGraph | InMemoryGraphStore,
        kind: EdgeKind | None = None,
    ) -> list[GraphEdge]:
        """Retrieve outbound edges originating from node_id."""
        return _get_outbound_from_graph(graph, node_id, kind=kind)

    def get_inbound_edges(
        self,
        node_id: str,
        graph: CodeGraph | InMemoryGraphStore,
        kind: EdgeKind | None = None,
    ) -> list[GraphEdge]:
        """Retrieve inbound edges terminating at node_id."""
        return _get_inbound_from_graph(graph, node_id, kind=kind)

    def get_outbound_neighbors(
        self,
        node_id: str,
        graph: CodeGraph | InMemoryGraphStore,
        kind: EdgeKind | None = None,
    ) -> list[GraphNode]:
        """Retrieve target nodes connected via outbound edges from node_id."""
        edges = self.get_outbound_edges(node_id, graph, kind=kind)
        target_ids = {e.target_id for e in edges}
        nodes = [_get_node_from_graph(graph, tid) for tid in target_ids]
        valid_nodes = [n for n in nodes if n is not None]
        return _sort_nodes_deterministically(valid_nodes)

    def get_inbound_neighbors(
        self,
        node_id: str,
        graph: CodeGraph | InMemoryGraphStore,
        kind: EdgeKind | None = None,
    ) -> list[GraphNode]:
        """Retrieve source nodes connected via inbound edges to node_id."""
        edges = self.get_inbound_edges(node_id, graph, kind=kind)
        source_ids = {e.source_id for e in edges}
        nodes = [_get_node_from_graph(graph, sid) for sid in source_ids]
        valid_nodes = [n for n in nodes if n is not None]
        return _sort_nodes_deterministically(valid_nodes)

    # ──────────────────────────────────────────────────────────────────────────
    # Callers & Callees (Strictly EdgeKind.CALLS)
    # ──────────────────────────────────────────────────────────────────────────

    def get_callers(self, symbol_id: str, graph: CodeGraph | InMemoryGraphStore) -> list[GraphNode]:
        """Retrieve all nodes that directly call the specified target symbol_id.

        Uses inbound EdgeKind.CALLS edges (caller → CALLS → symbol_id).
        """
        return self.get_inbound_neighbors(symbol_id, graph, kind=EdgeKind.CALLS)

    def get_callees(self, symbol_id: str, graph: CodeGraph | InMemoryGraphStore) -> list[GraphNode]:
        """Retrieve all nodes directly called by the specified source symbol_id.

        Uses outbound EdgeKind.CALLS edges (symbol_id → CALLS → callee).
        """
        return self.get_outbound_neighbors(symbol_id, graph, kind=EdgeKind.CALLS)

    # ──────────────────────────────────────────────────────────────────────────
    # Dependencies & Dependents Analysis
    # ──────────────────────────────────────────────────────────────────────────

    def get_dependencies(
        self,
        node_id: str,
        graph: CodeGraph | InMemoryGraphStore,
        max_depth: int | None = 1,
        edge_kinds: set[EdgeKind] | list[EdgeKind] | None = None,
    ) -> list[GraphNode]:
        """Retrieve semantic dependency closure for node_id up to max_depth.

        Following outbound dependency relationships (node_id → DEPENDENCY → target).
        Excludes structural DECLARES/CONTAINS edges by default.

        Args:
            node_id: Root node ID.
            graph: CodeGraph or InMemoryGraphStore container.
            max_depth: Traversal depth limit (1 = direct dependencies, None = unlimited).
            edge_kinds: Optional custom edge kinds filter. Defaults to DEPENDENCY_EDGE_KINDS.
        """
        kinds = set(edge_kinds) if edge_kinds is not None else set(DEPENDENCY_EDGE_KINDS)
        return self.traverse(
            node_id=node_id,
            graph=graph,
            direction="outbound",
            edge_kinds=kinds,
            max_depth=max_depth,
        )

    def get_dependents(
        self,
        node_id: str,
        graph: CodeGraph | InMemoryGraphStore,
        max_depth: int | None = 1,
        edge_kinds: set[EdgeKind] | list[EdgeKind] | None = None,
    ) -> list[GraphNode]:
        """Retrieve semantic dependent closure for node_id up to max_depth.

        Following inbound dependency relationships (dependent → DEPENDENCY → node_id).
        Excludes structural DECLARES/CONTAINS edges by default.

        Args:
            node_id: Target node ID.
            graph: CodeGraph or InMemoryGraphStore container.
            max_depth: Traversal depth limit (1 = direct dependents, None = unlimited).
            edge_kinds: Optional custom edge kinds filter. Defaults to DEPENDENCY_EDGE_KINDS.
        """
        kinds = set(edge_kinds) if edge_kinds is not None else set(DEPENDENCY_EDGE_KINDS)
        return self.traverse(
            node_id=node_id,
            graph=graph,
            direction="inbound",
            edge_kinds=kinds,
            max_depth=max_depth,
        )

    def get_impact_radius(
        self,
        node_id: str,
        graph: CodeGraph | InMemoryGraphStore,
        max_depth: int = 5,
    ) -> list[GraphNode]:
        """Compute reverse impact radius / blast radius for a node modification up to max_depth.

        Equivalent to get_dependents with max_depth=5.
        """
        return self.get_dependents(node_id, graph, max_depth=max_depth)

    # ──────────────────────────────────────────────────────────────────────────
    # Generic BFS Graph Traversal with Cycle Prevention
    # ──────────────────────────────────────────────────────────────────────────

    def traverse(
        self,
        node_id: str,
        graph: CodeGraph | InMemoryGraphStore,
        direction: Literal["outbound", "inbound"] = "outbound",
        edge_kinds: set[EdgeKind] | list[EdgeKind] | None = None,
        max_depth: int | None = None,
    ) -> list[GraphNode]:
        """Perform Breadth-First Search (BFS) graph traversal with cycle prevention.

        Args:
            node_id: Starting root node ID.
            graph: CodeGraph or InMemoryGraphStore container.
            direction: 'outbound' (follow targets) or 'inbound' (follow sources).
            edge_kinds: Optional set/list of EdgeKind filters.
            max_depth: Depth limit (1 = direct neighbors, None = unlimited).

        Returns:
            Deterministically sorted list of visited GraphNode instances (excluding root).
        """
        root_node = _get_node_from_graph(graph, node_id)
        if root_node is None:
            return []

        allowed_kinds = set(edge_kinds) if edge_kinds is not None else None

        visited: set[str] = {node_id}
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        result_nodes: list[GraphNode] = []

        while queue:
            curr_id, curr_depth = queue.popleft()

            if max_depth is not None and curr_depth >= max_depth:
                continue

            if direction == "outbound":
                edges = _get_outbound_from_graph(graph, curr_id)
            else:
                edges = _get_inbound_from_graph(graph, curr_id)

            for edge in edges:
                if allowed_kinds is not None and edge.kind not in allowed_kinds:
                    continue

                neighbor_id = edge.target_id if direction == "outbound" else edge.source_id

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    neighbor_node = _get_node_from_graph(graph, neighbor_id)
                    if neighbor_node is not None:
                        result_nodes.append(neighbor_node)
                        queue.append((neighbor_id, curr_depth + 1))

        return _sort_nodes_deterministically(result_nodes)
