"""Configuration models for TASK-6C Context Ranking."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm.exceptions import InvalidRankingConfigError


class ContextRankingConfig(BaseModel):
    """Immutable configuration governing candidate context ranking weights and bounds."""

    model_config = ConfigDict(frozen=True)

    # Configurable scoring weights
    weight_retrieval_relevance: float = Field(
        default=0.30, ge=0.0, le=1.0, description="Weight for Phase 5 retrieval relevance score."
    )
    weight_query_entity_match: float = Field(
        default=0.25, ge=0.0, le=1.0, description="Weight for direct query target symbol matching."
    )
    weight_intent_alignment: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Weight for primary/secondary intent alignment."
    )
    weight_relationship_alignment: float = Field(
        default=0.10, ge=0.0, le=1.0, description="Weight for structural relationship alignment."
    )
    weight_provenance_strength: float = Field(
        default=0.10, ge=0.0, le=1.0, description="Weight for multi-source provenance evidence."
    )
    weight_graph_proximity: float = Field(
        default=0.05, ge=0.0, le=1.0, description="Weight for graph traversal proximity."
    )
    weight_scope_alignment: float = Field(
        default=0.03, ge=0.0, le=1.0, description="Weight for QueryPlan scope alignment."
    )
    weight_locality: float = Field(
        default=0.02, ge=0.0, le=1.0, description="Weight for file/package locality."
    )

    # Graph proximity decay parameter
    graph_proximity_decay: float = Field(
        default=0.5,
        ge=0.0,
        le=5.0,
        description="Decay rate factor applied to graph traversal depth: 1.0 / (1.0 + depth * decay).",
    )

    # Tie-break rounding precision
    tie_break_precision: int = Field(
        default=6,
        ge=1,
        le=12,
        description="Decimal precision for score rounding prior to tie-break.",
    )

    @model_validator(mode="after")
    def validate_total_weights(self) -> Self:
        """Ensure total sum of weights is strictly positive (> 0.0)."""
        total = (
            self.weight_retrieval_relevance
            + self.weight_query_entity_match
            + self.weight_intent_alignment
            + self.weight_relationship_alignment
            + self.weight_provenance_strength
            + self.weight_graph_proximity
            + self.weight_scope_alignment
            + self.weight_locality
        )
        if total <= 0.0:
            raise InvalidRankingConfigError(
                f"Total ranking weights must be strictly > 0.0, got total={total}"
            )
        return self
