"""Data models representing directed edges and identity generation in the Code Knowledge Graph."""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from code_analyzer.ir import Reference, ReferenceKind, SourceLocation
from graph.enums import EdgeKind, ResolutionStatus

# Namespace UUID for Code Knowledge Graph edges
CODELENS_GRAPH_EDGE_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://codelens.ai/graph/edge/v1")


def generate_edge_id(
    source_id: str,
    target_id: str,
    kind: EdgeKind | str,
    source_line: int | None = None,
) -> str:
    """Generate a deterministic UUID string for a graph edge.

    Args:
        source_id: Unique identifier of the source node.
        target_id: Unique identifier of the target node or target reference name.
        kind: EdgeKind enum or string representation.
        source_line: Optional line number of the reference occurrence.

    Returns:
        Deterministic UUID v5 string.
    """
    kind_str = kind.value if hasattr(kind, "value") else str(kind)
    components = [
        f"src={source_id.strip()}",
        f"tgt={target_id.strip()}",
        f"kind={kind_str.lower()}",
    ]
    if source_line is not None:
        components.append(f"line={source_line}")

    seed_key = "|".join(components)
    return str(uuid.uuid5(CODELENS_GRAPH_EDGE_NAMESPACE, seed_key))


class GraphEdge(BaseModel):
    """Immutable directed edge representation in the Code Knowledge Graph."""

    model_config = ConfigDict(frozen=True)

    id: str
    source_id: str
    target_id: str
    kind: EdgeKind
    resolution_status: ResolutionStatus = ResolutionStatus.UNRESOLVED
    confidence: float = 1.0
    source_location: SourceLocation | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "source_id", "target_id")
    @classmethod
    def validate_non_empty_ids(cls, v: str) -> str:
        """Ensure node/edge IDs are non-empty and non-whitespace."""
        if not v or not v.strip():
            raise ValueError("ID fields cannot be empty or whitespace")
        return v.strip()

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure edge confidence score is in valid [0.0, 1.0] interval."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Confidence score must be between 0.0 and 1.0, got {v}")
        return v

    @classmethod
    def from_ir_reference(cls, ref: Reference, repository_id: str | None = None) -> "GraphEdge":
        """Construct a GraphEdge from a Canonical Code IR Reference entity.

        Args:
            ref: Canonical Code IR Reference entity.
            repository_id: Optional parent repository ID.

        Returns:
            Derived GraphEdge instance.
        """
        # Map IR ReferenceKind to EdgeKind
        kind_mapping: dict[ReferenceKind, EdgeKind] = {
            ReferenceKind.CALL: EdgeKind.CALLS,
            ReferenceKind.IMPORT: EdgeKind.IMPORTS,
            ReferenceKind.EXTENDS: EdgeKind.EXTENDS,
            ReferenceKind.IMPLEMENTS: EdgeKind.IMPLEMENTS,
            ReferenceKind.OVERRIDE: EdgeKind.OVERRIDES,
            ReferenceKind.FIELD_ACCESS: EdgeKind.FIELD_ACCESS,
            ReferenceKind.TYPE_USAGE: EdgeKind.TYPED_AS,
            ReferenceKind.VARIABLE_USAGE: EdgeKind.READS,
        }

        edge_kind = kind_mapping.get(ref.ref_kind, EdgeKind.REFERENCES)

        source_id = ref.source_symbol_id or ref.source_file_id or ref.id
        target_id = ref.target_symbol_id or ref.target_qualified_name

        resolution_status = (
            ResolutionStatus.RESOLVED if ref.target_symbol_id else ResolutionStatus.UNRESOLVED
        )

        source_line = ref.source_location.start_line if ref.source_location else None

        edge_id = generate_edge_id(
            source_id=source_id,
            target_id=target_id,
            kind=edge_kind,
            source_line=source_line,
        )

        attributes: dict[str, Any] = {
            "target_qualified_name": ref.target_qualified_name,
            "reference_id": ref.id,
        }
        if repository_id:
            attributes["repository_id"] = repository_id
        if ref.metadata:
            attributes.update(ref.metadata)

        return cls(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            kind=edge_kind,
            resolution_status=resolution_status,
            confidence=ref.confidence,
            source_location=ref.source_location,
            attributes=attributes,
        )
