"""Data models for TASK-6B Graph-Aware Context Expansion."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from llm.enums import RelationshipType


class GraphExpansionAnchor(BaseModel):
    """Immutable representation of a graph expansion starting point."""

    model_config = ConfigDict(frozen=True)

    anchor_id: str = Field(description="Unique graph node ID or symbol ID of the anchor.")
    anchor_type: str = Field(
        default="SYMBOL",
        description="Type category of anchor (e.g. SYMBOL, NODE, FILE, RETRIEVAL_RESULT).",
    )
    symbol_name: str | None = Field(
        default=None, description="Simple name of the anchor symbol if available."
    )
    qualified_name: str | None = Field(
        default=None, description="Fully qualified symbol name if available."
    )
    file_path: str | None = Field(default=None, description="File path of the anchor if available.")
    retrieval_chunk_id: str | None = Field(
        default=None, description="Originating Phase 5 retrieval chunk ID if mapped."
    )


class GraphExpansionCandidateStep(BaseModel):
    """Represents a single directed edge transition in a graph expansion path."""

    model_config = ConfigDict(frozen=True)

    source_id: str = Field(description="Source graph node ID of the transition.")
    target_id: str = Field(description="Target graph node ID of the transition.")
    relationship_type: RelationshipType = Field(
        description="Semantic relationship type of the transition."
    )
    edge_kind: str | None = Field(default=None, description="Phase 3 EdgeKind string if available.")


class GraphExpansionCandidatePath(BaseModel):
    """Represents the deterministic traversal path from anchor to an expanded candidate."""

    model_config = ConfigDict(frozen=True)

    anchor_id: str = Field(description="Starting anchor ID.")
    target_node_id: str = Field(description="Final expanded target graph node ID.")
    depth: int = Field(description="Number of graph hops from anchor to target.")
    node_ids: list[str] = Field(
        description="Ordered list of graph node IDs along the path from anchor to target."
    )
    steps: list[GraphExpansionCandidateStep] = Field(
        default_factory=list, description="Ordered sequence of directed edge steps."
    )


class GraphExpansionCandidate(BaseModel):
    """Immutable representation of a structurally expanded context candidate."""

    model_config = ConfigDict(frozen=True)

    candidate_id: str = Field(description="Unique candidate identifier.")
    node_id: str = Field(description="Graph node ID of the expanded code entity.")
    symbol_name: str | None = Field(default=None, description="Simple symbol name.")
    qualified_name: str | None = Field(default=None, description="Fully qualified symbol name.")
    node_kind: str = Field(description="NodeKind category string (e.g. FUNCTION, CLASS, FILE).")
    file_path: str | None = Field(default=None, description="File path declaring the symbol.")
    start_line: int | None = Field(default=None, description="Start line in source code.")
    end_line: int | None = Field(default=None, description="End line in source code.")

    source: str = Field(
        default="GRAPH_EXPANSION",
        description="Evidence source identifier (e.g. GRAPH_EXPANSION or RETRIEVAL+GRAPH_EXPANSION).",
    )
    anchor_id: str = Field(description="Anchor ID triggering this expansion candidate.")
    relationship_type: RelationshipType = Field(
        description="Primary relationship type leading to candidate."
    )
    traversal_depth: int = Field(description="Shortest traversal depth from anchor to candidate.")
    expansion_reason: str = Field(
        description="Structured explanation code describing why candidate was expanded."
    )
    path: GraphExpansionCandidatePath | None = Field(
        default=None, description="Full deterministic expansion path from anchor to candidate."
    )
    retrieval_chunk_id: str | None = Field(
        default=None,
        description="Linked Phase 5 retrieval chunk ID if candidate was in retrieval results.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible candidate metadata."
    )


class GraphExpansionResult(BaseModel):
    """Immutable result container for graph-aware context expansion."""

    model_config = ConfigDict(frozen=True)

    candidates: list[GraphExpansionCandidate] = Field(
        default_factory=list, description="Deterministically ordered list of expanded candidates."
    )
    anchors: list[GraphExpansionAnchor] = Field(
        default_factory=list, description="Deduplicated anchors used for graph expansion."
    )
    expanded_node_count: int = Field(
        default=0, description="Total number of unique graph nodes expanded."
    )
    max_depth_reached: int = Field(
        default=0, description="Maximum traversal depth reached during expansion."
    )
    truncated: bool = Field(
        default=False, description="Flag indicating if expansion was stopped by budget limits."
    )
    expansion_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Execution metrics and metadata."
    )
