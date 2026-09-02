"""Data models for TASK-6D Context Deduplication & Pruning."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from llm.enums import PruningReasonCode
from llm.ranking_models import RankedContextCandidate


class PrunedCandidateRecord(BaseModel):
    """Immutable record explaining why a candidate context item was deduplicated or pruned."""

    model_config = ConfigDict(frozen=True)

    candidate_id: str = Field(description="Unique candidate identifier of the pruned item.")
    pruning_reason: PruningReasonCode | str = Field(
        description="Structured reason code explaining exclusion."
    )

    details: str = Field(description="Human-readable explanation for pruning decision.")
    winning_candidate_id: str | None = Field(
        default=None,
        description="Surviving candidate ID if pruned due to deduplication or evidence merging.",
    )
    original_candidate: RankedContextCandidate | None = Field(
        default=None, description="Original ranked candidate object before pruning."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible decision metadata."
    )


class ContextPruningResult(BaseModel):
    """Immutable container for candidate context deduplication and pruning results."""

    model_config = ConfigDict(frozen=True)

    retained_candidates: list[RankedContextCandidate] = Field(
        default_factory=list, description="Surviving candidates after deduplication and pruning."
    )
    pruned_candidates: list[PrunedCandidateRecord] = Field(
        default_factory=list, description="Records for all deduplicated and pruned candidates."
    )
    input_count: int = Field(default=0, description="Total candidates received from ranker.")
    deduplicated_count: int = Field(
        default=0, description="Number of candidates merged due to duplication."
    )
    pruned_count: int = Field(
        default=0, description="Number of candidates removed due to pruning limits/policies."
    )
    output_count: int = Field(default=0, description="Total surviving candidates retained.")
    pruning_latency_ms: float = Field(
        default=0.0, description="Execution time for pruning phase in milliseconds."
    )
    pruning_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Observability metrics and pruning configuration metadata.",
    )
