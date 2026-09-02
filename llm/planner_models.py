"""Data models for Phase 6A Query Intent & Query Planning."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from llm.enums import (
    AnswerStyle,
    GraphStrategy,
    QueryIntent,
    QueryScope,
    RelationshipType,
    RetrievalStrategy,
)
from llm.exceptions import InvalidQueryError
from retrieval.query_models import ProcessedQuery


class QueryPlan(BaseModel):
    """Immutable, deterministic query plan produced by Phase 6A QueryPlanner.

    Serves as the central control signal for downstream Phase 5 retrieval and
    Phase 6 context expansion, ranking, pruning, and answer generation.
    """

    model_config = ConfigDict(frozen=True)

    query: str = Field(..., description="Original raw input query string.")
    normalized_query: str = Field(..., description="Normalized query string.")
    processed_query: ProcessedQuery = Field(
        ...,
        description="Phase 5 ProcessedQuery object containing preprocessed tokens and metadata.",
    )

    primary_intent: QueryIntent = Field(
        default=QueryIntent.UNKNOWN, description="Primary intent classification."
    )
    secondary_intents: list[QueryIntent] = Field(
        default_factory=list,
        description="Secondary intents present in compound/multi-part queries.",
    )

    target_entities: list[str] = Field(
        default_factory=list,
        description="Deduplicated list of identified target entity/symbol names.",
    )
    explicit_entities: list[str] = Field(
        default_factory=list, description="Entities explicitly mentioned in the query text."
    )
    inferred_entities: list[str] = Field(
        default_factory=list, description="Entities inferred from context or rules."
    )

    identifiers: list[str] = Field(
        default_factory=list, description="Code identifiers extracted from the query."
    )
    natural_language_terms: list[str] = Field(
        default_factory=list, description="Prose terms extracted from the query."
    )

    relationship_type: RelationshipType = Field(
        default=RelationshipType.NONE, description="Extracted structural code relationship type."
    )
    retrieval_strategy: RetrievalStrategy = Field(
        default=RetrievalStrategy.HYBRID,
        description="Recommended downstream retrieval engine strategy.",
    )
    graph_strategy: GraphStrategy = Field(
        default=GraphStrategy.NONE, description="Recommended graph expansion strategy."
    )

    scope: QueryScope = Field(
        default=QueryScope.UNKNOWN, description="Granular code scope implied by the query."
    )
    answer_style: AnswerStyle = Field(
        default=AnswerStyle.EXPLANATION, description="Recommended answer formatting style."
    )

    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Deterministic confidence score for the plan."
    )
    reason_codes: list[str] = Field(
        default_factory=list, description="Explainability reason codes triggering classification."
    )
    operations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Structured bounded operation sequence for compound queries.",
    )
    has_negation: bool = Field(
        default=False, description="Flag indicating presence of negation in query."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible metadata dictionary."
    )

    @field_validator("query", "normalized_query")
    @classmethod
    def _validate_non_empty_string(cls, v: str) -> str:
        """Ensure string fields are not empty or whitespace-only."""
        if not v or not v.strip():
            raise InvalidQueryError("Query and normalized_query cannot be empty or whitespace-only")
        return v
