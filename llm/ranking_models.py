"""Data models for TASK-6C Context Ranking."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from llm.enums import RelationshipType
from llm.expansion_models import GraphExpansionCandidate
from retrieval.retrieval_models import RetrievalResult


class ContextRankingScoreBreakdown(BaseModel):
    """Immutable breakdown of individual scoring dimension components [0.0, 1.0]."""

    model_config = ConfigDict(frozen=True)

    retrieval_relevance: float = Field(
        default=0.0, description="Normalized Phase 5 retrieval relevance score."
    )
    query_entity_match: float = Field(
        default=0.0, description="Score for matching explicit query target entities/symbols."
    )
    intent_alignment: float = Field(
        default=0.0, description="Score for alignment with primary and secondary query intents."
    )
    relationship_alignment: float = Field(
        default=0.0, description="Score for matching requested structural relationship types."
    )
    provenance_strength: float = Field(
        default=0.0, description="Score for multi-source evidence (Retrieval + Graph Expansion)."
    )
    graph_proximity: float = Field(
        default=0.0, description="Score for graph proximity (depth decay)."
    )
    scope_alignment: float = Field(
        default=0.0, description="Score for matching QueryPlan scope constraints."
    )
    locality: float = Field(default=0.0, description="Score for file/package context locality.")


class RankedContextCandidate(BaseModel):
    """Immutable representation of a context candidate with final rank, score, and explanations."""

    model_config = ConfigDict(frozen=True)

    candidate_id: str = Field(description="Unique candidate identifier.")
    rank: int = Field(description="1-indexed final rank position assigned by ranker.")
    final_score: float = Field(description="Weighted final score assigned by ranker.")
    score_breakdown: ContextRankingScoreBreakdown = Field(
        description="Detailed component score breakdown across all ranking dimensions."
    )
    reason_codes: list[str] = Field(
        default_factory=list, description="Structured explanation reason codes for ranking."
    )

    # Candidate attributes and traceability
    node_id: str | None = Field(default=None, description="Associated graph node ID if present.")
    symbol_name: str | None = Field(default=None, description="Simple symbol name.")
    qualified_name: str | None = Field(default=None, description="Fully qualified symbol name.")
    node_kind: str | None = Field(
        default=None, description="NodeKind or ChunkType category string."
    )
    file_path: str | None = Field(default=None, description="File path of the code entity.")
    start_line: int | None = Field(default=None, description="Start line in source file.")
    end_line: int | None = Field(default=None, description="End line in source file.")
    source: str = Field(
        default="UNKNOWN",
        description="Evidence source identifier (e.g. RETRIEVAL, GRAPH_EXPANSION, RETRIEVAL+GRAPH_EXPANSION).",
    )
    anchor_id: str | None = Field(
        default=None, description="Originating graph expansion anchor ID."
    )
    relationship_type: RelationshipType = Field(
        default=RelationshipType.NONE, description="Primary relationship type leading to candidate."
    )
    traversal_depth: int = Field(
        default=0, description="Graph traversal depth from anchor (0 for direct retrieval)."
    )
    retrieval_chunk_id: str | None = Field(
        default=None, description="Originating Phase 5 retrieval chunk ID if available."
    )
    retrieval_score: float | None = Field(
        default=None, description="Raw or normalized Phase 5 retrieval score."
    )

    # Underlying candidate object preservation
    original_candidate: GraphExpansionCandidate | RetrievalResult | None = Field(
        default=None, description="Full un-pruned underlying candidate object."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible candidate metadata."
    )


class ContextRankingResult(BaseModel):
    """Immutable result container for candidate context ranking."""

    model_config = ConfigDict(frozen=True)

    ranked_candidates: list[RankedContextCandidate] = Field(
        default_factory=list, description="Deterministically ordered list of ranked candidates."
    )
    total_candidates: int = Field(
        default=0, description="Total number of candidates ranked (equals input count)."
    )
    ranking_latency_ms: float = Field(
        default=0.0, description="Time taken to perform candidate ranking in milliseconds."
    )
    ranking_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Observability metrics and metadata."
    )
