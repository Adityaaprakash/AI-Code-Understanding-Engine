"""In-process high-performance graph store implementation with O(1) adjacency indexing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from graph.contracts import GraphStoreContract
from graph.models import CodeGraph

if TYPE_CHECKING:
    from collections.abc import Iterable

    from graph.edges import GraphEdge
    from graph.enums import EdgeKind, NodeKind
    from graph.nodes import GraphNode


class InMemoryGraphStore(GraphStoreContract):
    """In-memory, indexed storage engine for Code Knowledge Graph nodes and edges.

    Provides fast O(1)-ish node/edge lookups, adjacency indices, graph consistency
    checks, conflict detection, and async GraphStoreContract persistence methods.
    """

    def __init__(self, repository_id: str | None = None) -> None:
        """Initialize empty graph store.

        Args:
            repository_id: Optional default repository ID for isolated operations.
        """
        self.repository_id = repository_id
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}

        # Adjacency indexes mapping node IDs to sets of edge IDs
        self._outbound_index: dict[str, set[str]] = {}
        self._inbound_index: dict[str, set[str]] = {}
        self._outbound_kind_index: dict[tuple[str, EdgeKind], set[str]] = {}
        self._inbound_kind_index: dict[tuple[str, EdgeKind], set[str]] = {}

        # Persistent storage map for GraphStoreContract repository snapshots
        self._saved_graphs: dict[str, CodeGraph] = {}

    @property
    def node_count(self) -> int:
        """Total number of nodes stored."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Total number of edges stored."""
        return len(self._edges)

    def clear(self) -> None:
        """Clear all nodes, edges, and index structures."""
        self._nodes.clear()
        self._edges.clear()
        self._outbound_index.clear()
        self._inbound_index.clear()
        self._outbound_kind_index.clear()
        self._inbound_kind_index.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # Node Storage Operations
    # ──────────────────────────────────────────────────────────────────────────

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the store.

        Idempotent for identical nodes; raises ValueError if a node with the same ID
        already exists with conflicting attributes.
        """
        if node.id in self._nodes:
            existing = self._nodes[node.id]
            if existing == node:
                return  # Idempotent re-insertion
            raise ValueError(
                f"Conflicting node with ID '{node.id}' already exists in store: "
                f"existing={existing}, new={node}"
            )
        self._nodes[node.id] = node

    def add_nodes(self, nodes: Iterable[GraphNode]) -> None:
        """Add multiple nodes to the store."""
        for node in nodes:
            self.add_node(node)

    def get_node(self, node_id: str) -> GraphNode | None:
        """Retrieve a node by ID, or None if not found."""
        return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        """Check if a node ID exists in the store."""
        return node_id in self._nodes

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all incident edges to preserve graph consistency.

        Returns True if the node existed and was removed, False otherwise.
        """
        if node_id not in self._nodes:
            return False

        # Find and remove all incident outbound and inbound edges
        outbound_edge_ids = list(self._outbound_index.get(node_id, set()))
        inbound_edge_ids = list(self._inbound_index.get(node_id, set()))

        for eid in outbound_edge_ids + inbound_edge_ids:
            self.remove_edge(eid)

        del self._nodes[node_id]
        return True

    def get_nodes_by_kind(self, kind: NodeKind) -> list[GraphNode]:
        """Return all nodes matching a specific NodeKind sorted by ID."""
        matched = [n for n in self._nodes.values() if n.kind == kind]
        return sorted(matched, key=lambda n: n.id)

    # ──────────────────────────────────────────────────────────────────────────
    # Edge Storage Operations & Indexing
    # ──────────────────────────────────────────────────────────────────────────

    def add_edge(self, edge: GraphEdge, enforce_consistency: bool = True) -> None:
        """Add an edge to the store and update adjacency indexes.

        Args:
            edge: GraphEdge instance to add.
            enforce_consistency: If True, requires both source_id and target_id
                to exist in the store.

        Raises:
            ValueError: If source or target node is missing (when enforce_consistency=True),
                or if a conflicting edge with the same ID already exists.
        """
        if enforce_consistency:
            if edge.source_id not in self._nodes:
                raise ValueError(
                    f"Cannot add edge '{edge.id}': source node '{edge.source_id}' "
                    "does not exist in store."
                )
            if edge.target_id not in self._nodes:
                raise ValueError(
                    f"Cannot add edge '{edge.id}': target node '{edge.target_id}' "
                    "does not exist in store."
                )

        if edge.id in self._edges:
            existing = self._edges[edge.id]
            if existing == edge:
                return  # Idempotent re-insertion
            raise ValueError(
                f"Conflicting edge with ID '{edge.id}' already exists in store: "
                f"existing={existing}, new={edge}"
            )

        self._edges[edge.id] = edge

        # Update adjacency indexes
        self._outbound_index.setdefault(edge.source_id, set()).add(edge.id)
        self._inbound_index.setdefault(edge.target_id, set()).add(edge.id)
        self._outbound_kind_index.setdefault((edge.source_id, edge.kind), set()).add(edge.id)
        self._inbound_kind_index.setdefault((edge.target_id, edge.kind), set()).add(edge.id)

    def add_edges(self, edges: Iterable[GraphEdge], enforce_consistency: bool = True) -> None:
        """Add multiple edges to the store."""
        for edge in edges:
            self.add_edge(edge, enforce_consistency=enforce_consistency)

    def get_edge(self, edge_id: str) -> GraphEdge | None:
        """Retrieve an edge by ID, or None if not found."""
        return self._edges.get(edge_id)

    def has_edge(self, edge_id: str) -> bool:
        """Check if an edge ID exists in the store."""
        return edge_id in self._edges

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge by ID and update indexes.

        Returns True if the edge existed and was removed, False otherwise.
        """
        if edge_id not in self._edges:
            return False

        edge = self._edges.pop(edge_id)

        # Clean index entries
        if edge.source_id in self._outbound_index:
            self._outbound_index[edge.source_id].discard(edge.id)
            if not self._outbound_index[edge.source_id]:
                del self._outbound_index[edge.source_id]

        if edge.target_id in self._inbound_index:
            self._inbound_index[edge.target_id].discard(edge.id)
            if not self._inbound_index[edge.target_id]:
                del self._inbound_index[edge.target_id]

        out_key = (edge.source_id, edge.kind)
        if out_key in self._outbound_kind_index:
            self._outbound_kind_index[out_key].discard(edge.id)
            if not self._outbound_kind_index[out_key]:
                del self._outbound_kind_index[out_key]

        in_key = (edge.target_id, edge.kind)
        if in_key in self._inbound_kind_index:
            self._inbound_kind_index[in_key].discard(edge.id)
            if not self._inbound_kind_index[in_key]:
                del self._inbound_kind_index[in_key]

        return True

    # ──────────────────────────────────────────────────────────────────────────
    # Fast Indexed Adjacency Queries
    # ──────────────────────────────────────────────────────────────────────────

    def get_outbound_edges(self, source_id: str, kind: EdgeKind | None = None) -> list[GraphEdge]:
        """Retrieve outbound edges originating from source_id, optionally filtered by kind.

        Returns deterministically sorted list by edge.id.
        """
        if kind is not None:
            edge_ids = self._outbound_kind_index.get((source_id, kind), set())
        else:
            edge_ids = self._outbound_index.get(source_id, set())

        edges = [self._edges[eid] for eid in edge_ids if eid in self._edges]
        return sorted(edges, key=lambda e: e.id)

    def get_inbound_edges(self, target_id: str, kind: EdgeKind | None = None) -> list[GraphEdge]:
        """Retrieve inbound edges terminating at target_id, optionally filtered by kind.

        Returns deterministically sorted list by edge.id.
        """
        if kind is not None:
            edge_ids = self._inbound_kind_index.get((target_id, kind), set())
        else:
            edge_ids = self._inbound_index.get(target_id, set())

        edges = [self._edges[eid] for eid in edge_ids if eid in self._edges]
        return sorted(edges, key=lambda e: e.id)

    def get_neighbors(
        self, node_id: str, kind: EdgeKind | None = None, direction: str = "both"
    ) -> list[GraphNode]:
        """Retrieve adjacent nodes connected to node_id.

        Args:
            node_id: ID of the central node.
            kind: Optional EdgeKind filter.
            direction: 'outbound', 'inbound', or 'both'.

        Returns:
            Deterministically sorted list of neighboring GraphNode instances.
        """
        neighbor_ids: set[str] = set()

        if direction in ("outbound", "both"):
            for edge in self.get_outbound_edges(node_id, kind=kind):
                neighbor_ids.add(edge.target_id)

        if direction in ("inbound", "both"):
            for edge in self.get_inbound_edges(node_id, kind=kind):
                neighbor_ids.add(edge.source_id)

        nodes = [self._nodes[nid] for nid in neighbor_ids if nid in self._nodes]
        return sorted(nodes, key=lambda n: n.id)

    # ──────────────────────────────────────────────────────────────────────────
    # Container Conversion & Serialization
    # ──────────────────────────────────────────────────────────────────────────

    def to_codegraph(
        self, repository_id: str | None = None, metadata: dict[str, Any] | None = None
    ) -> CodeGraph:
        """Export internal state to a CodeGraph container model."""
        repo_id = repository_id or self.repository_id or "default_repository"
        return CodeGraph(
            repository_id=repo_id,
            nodes=dict(self._nodes),
            edges=dict(self._edges),
            metadata=metadata or {},
        )

    @classmethod
    def from_codegraph(
        cls, graph: CodeGraph, enforce_consistency: bool = False
    ) -> InMemoryGraphStore:
        """Construct an InMemoryGraphStore populated from a CodeGraph model."""
        store = cls(repository_id=graph.repository_id)
        store.add_nodes(graph.nodes.values())
        store.add_edges(graph.edges.values(), enforce_consistency=enforce_consistency)
        return store

    # ──────────────────────────────────────────────────────────────────────────
    # GraphStoreContract Implementation
    # ──────────────────────────────────────────────────────────────────────────

    async def save_graph(self, graph: CodeGraph) -> None:
        """Persist a CodeGraph snapshot in the store's repository repository map."""
        self._saved_graphs[graph.repository_id] = graph.model_copy(deep=True)

    async def load_graph(self, repository_id: str) -> CodeGraph:
        """Load a persisted CodeGraph snapshot by repository_id."""
        if repository_id not in self._saved_graphs:
            raise KeyError(f"No graph stored for repository ID '{repository_id}'.")
        return self._saved_graphs[repository_id].model_copy(deep=True)

    async def delete_graph(self, repository_id: str) -> None:
        """Delete a persisted CodeGraph snapshot for repository_id."""
        if repository_id in self._saved_graphs:
            del self._saved_graphs[repository_id]
