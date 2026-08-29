"""Graph container models for Code Knowledge Graph representation."""

from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from graph.edges import GraphEdge
from graph.enums import EdgeKind, NodeKind
from graph.nodes import GraphNode


class CodeGraph(BaseModel):
    """Container data model for Code Knowledge Graph storage and operations."""

    model_config = ConfigDict(frozen=False)

    repository_id: str
    nodes: dict[str, GraphNode] = Field(default_factory=dict)
    edges: dict[str, GraphEdge] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("repository_id")
    @classmethod
    def validate_repository_id(cls, v: str) -> str:
        """Ensure repository_id is non-empty."""
        if not v or not v.strip():
            raise ValueError("repository_id cannot be empty or whitespace")
        return v.strip()

    @property
    def node_count(self) -> int:
        """Total number of nodes in the graph."""
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Total number of edges in the graph."""
        return len(self.edges)

    def add_node(self, node: GraphNode) -> None:
        """Add or update a node in the graph."""
        self.nodes[node.id] = node

    def add_nodes(self, nodes: Iterable[GraphNode]) -> None:
        """Add multiple nodes to the graph."""
        for node in nodes:
            self.add_node(node)

    def add_edge(self, edge: GraphEdge) -> None:
        """Add or update an edge in the graph."""
        self.edges[edge.id] = edge

    def add_edges(self, edges: Iterable[GraphEdge]) -> None:
        """Add multiple edges to the graph."""
        for edge in edges:
            self.add_edge(edge)

    def get_node(self, node_id: str) -> GraphNode | None:
        """Retrieve a node by its ID."""
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: str) -> GraphEdge | None:
        """Retrieve an edge by its ID."""
        return self.edges.get(edge_id)

    def get_nodes_by_kind(self, kind: NodeKind) -> list[GraphNode]:
        """Return all nodes of a specific NodeKind."""
        return [node for node in self.nodes.values() if node.kind == kind]

    def get_outbound_edges(self, source_id: str, kind: EdgeKind | None = None) -> list[GraphEdge]:
        """Retrieve all outbound edges originating from the given source node ID."""
        return [
            edge
            for edge in self.edges.values()
            if edge.source_id == source_id and (kind is None or edge.kind == kind)
        ]

    def get_inbound_edges(self, target_id: str, kind: EdgeKind | None = None) -> list[GraphEdge]:
        """Retrieve all inbound edges terminating at the given target node ID."""
        return [
            edge
            for edge in self.edges.values()
            if edge.target_id == target_id and (kind is None or edge.kind == kind)
        ]

    def get_neighbors(
        self, node_id: str, kind: EdgeKind | None = None, direction: str = "both"
    ) -> list[GraphNode]:
        """Retrieve adjacent nodes connected to the specified node ID.

        Args:
            node_id: ID of the central node.
            kind: Optional EdgeKind filter.
            direction: Direction of edges to follow ('outbound', 'inbound', or 'both').

        Returns:
            List of neighboring GraphNode instances.
        """
        neighbor_ids: set[str] = set()

        if direction in ("outbound", "both"):
            for edge in self.get_outbound_edges(node_id, kind=kind):
                neighbor_ids.add(edge.target_id)

        if direction in ("inbound", "both"):
            for edge in self.get_inbound_edges(node_id, kind=kind):
                neighbor_ids.add(edge.source_id)

        return [self.nodes[nid] for nid in neighbor_ids if nid in self.nodes]

    def to_dict(self) -> dict[str, Any]:
        """Serialize CodeGraph to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CodeGraph":
        """Construct CodeGraph from dictionary."""
        return cls.model_validate(data)
