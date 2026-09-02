"""Immutable expansion configuration model for TASK-6B Graph-Aware Context Expansion."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from llm.enums import GraphStrategy, RelationshipType
from llm.exceptions import InvalidExpansionConfigError


class GraphExpansionConfig(BaseModel):
    """Immutable configuration for controlling bounded graph context expansion."""

    model_config = ConfigDict(frozen=True)

    max_depth: int = Field(
        default=2, description="Maximum traversal depth from graph anchors (>= 0)."
    )
    max_expanded_nodes: int = Field(
        default=50, description="Maximum total nodes expanded during traversal (> 0)."
    )
    max_candidates: int = Field(
        default=50, description="Maximum candidate results returned by expansion (> 0)."
    )
    max_neighbors_per_node: int = Field(
        default=10, description="Maximum outbound/inbound neighbors explored per node (> 0)."
    )

    allowed_relationship_types: list[RelationshipType] | None = Field(
        default=None,
        description="Optional explicit filter for allowed relationship types during traversal.",
    )
    graph_strategy_override: GraphStrategy | None = Field(
        default=None, description="Optional override for QueryPlan graph strategy."
    )

    allow_same_file_expansion: bool = Field(
        default=True, description="Whether expansion within the same file is allowed."
    )
    allow_parent_scope_expansion: bool = Field(
        default=True,
        description="Whether expanding into enclosing class/module scope is allowed.",
    )
    retain_path_metadata: bool = Field(
        default=True, description="Whether full path metadata is preserved on candidates."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible configuration metadata."
    )

    @field_validator("max_depth")
    @classmethod
    def _validate_max_depth(cls, v: int) -> int:
        if v < 0:
            raise InvalidExpansionConfigError(f"max_depth must be >= 0, got {v}")
        return v

    @field_validator("max_expanded_nodes", "max_candidates", "max_neighbors_per_node")
    @classmethod
    def _validate_positive_bounds(cls, v: int) -> int:
        if v <= 0:
            raise InvalidExpansionConfigError(f"Expansion limit must be > 0, got {v}")
        return v
