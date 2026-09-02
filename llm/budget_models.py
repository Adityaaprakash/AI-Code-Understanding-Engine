"""Data models for TASK-6E Context Token Budgeting & Context Packing."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from llm.enums import (
    ContextOverflowPolicy,
    ContextPackingReasonCode,
    RelationshipType,
    TokenCountMode,
)
from llm.ranking_models import ContextRankingScoreBreakdown, RankedContextCandidate


class PackedContextItem(BaseModel):
    """Immutable packed candidate item ready for downstream LLM context assembly and grounding."""

    model_config = ConfigDict(frozen=True)

    candidate_id: str = Field(description="Unique candidate identifier.")
    rank: int = Field(description="Original 1-indexed relevance rank position.")
    final_score: float = Field(description="Final relevance ranking score.")
    repository_id: str = Field(
        default="default_repo",
        description="Originating repository identifier for provenance.",
    )
    file_path: str | None = Field(default=None, description="Source file path.")
    start_line: int | None = Field(default=None, description="Start line number in source file.")
    end_line: int | None = Field(default=None, description="End line number in source file.")
    symbol_name: str | None = Field(default=None, description="Simple symbol name if available.")
    qualified_name: str | None = Field(
        default=None, description="Fully qualified symbol name if available."
    )
    node_id: str | None = Field(default=None, description="Associated graph node ID if present.")
    node_kind: str | None = Field(default=None, description="NodeKind or chunk category.")
    source: str = Field(default="UNKNOWN", description="Evidence source identifier.")
    relationship_type: RelationshipType = Field(
        default=RelationshipType.NONE, description="Primary relationship leading to candidate."
    )
    formatted_code: str = Field(
        description="Exact formatted text (header + snippet) passed downstream and counted."
    )
    code_tokens: int = Field(description="Token count of the raw snippet body.")
    header_tokens: int = Field(description="Token count of the header wrapper metadata.")
    token_count: int = Field(description="Total token count of formatted_code.")
    truncated: bool = Field(
        default=False,
        description="Flag indicating if candidate content was truncated to fit budget.",
    )
    original_token_count: int | None = Field(
        default=None, description="Original un-truncated token count if truncated."
    )
    reason_codes: list[str] = Field(
        default_factory=list, description="Original ranking reason codes."
    )
    score_breakdown: ContextRankingScoreBreakdown | None = Field(
        default=None, description="Component score breakdown."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible candidate metadata."
    )


class ContextOmissionRecord(BaseModel):
    """Immutable audit record explaining why a candidate was omitted during token budgeting."""

    model_config = ConfigDict(frozen=True)

    candidate_id: str = Field(description="Unique candidate identifier of the omitted item.")
    omission_reason: ContextPackingReasonCode | str = Field(
        description="Structured reason code explaining context budget omission."
    )
    details: str = Field(description="Human-readable explanation for omission decision.")
    candidate_token_count: int = Field(
        description="Total token count of the candidate at time of evaluation."
    )
    available_budget_at_omission: int = Field(
        description="Remaining usable evidence budget when candidate was evaluated."
    )
    original_candidate: RankedContextCandidate | None = Field(
        default=None, description="Original candidate candidate object."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible omission decision metadata."
    )


class ContextPackingStats(BaseModel):
    """Immutable summary statistics for context window budgeting and evidence utilization."""

    model_config = ConfigDict(frozen=True)

    total_model_context_limit: int = Field(
        default=0, description="Total configured model context window limit."
    )
    reserved_system_tokens: int = Field(
        default=0, description="Tokens reserved for system instructions."
    )
    reserved_query_tokens: int = Field(default=0, description="Tokens reserved for user query.")
    reserved_output_tokens: int = Field(
        default=0, description="Tokens reserved for model answer generation."
    )
    safety_margin_tokens: int = Field(
        default=0, description="Tokens reserved for safety margin buffer."
    )
    usable_evidence_budget: int = Field(default=0, description="Net usable evidence token budget.")
    packed_evidence_tokens: int = Field(
        default=0, description="Total tokens consumed by packed evidence items."
    )
    remaining_evidence_budget: int = Field(
        default=0, description="Unused evidence tokens remaining in budget."
    )
    utilization_ratio: float = Field(
        default=0.0,
        description="Ratio of packed evidence tokens to usable evidence budget [0.0, 1.0].",
    )
    input_candidate_count: int = Field(
        default=0, description="Total candidates received from 6D pruner."
    )
    packed_candidate_count: int = Field(
        default=0, description="Total candidates successfully packed into context."
    )
    omitted_candidate_count: int = Field(
        default=0, description="Total candidates omitted due to budget constraints."
    )
    token_count_mode: TokenCountMode = Field(
        default=TokenCountMode.ESTIMATED, description="Token counting mode (EXACT or ESTIMATED)."
    )
    overflow_policy: ContextOverflowPolicy = Field(
        default=ContextOverflowPolicy.SKIP, description="Overflow handling policy."
    )


class PackedContext(BaseModel):
    """Immutable container for the final bounded context package ready for LLM consumption (6F)."""

    model_config = ConfigDict(frozen=True)

    query: str = Field(description="User query string.")
    query_plan_summary: dict[str, Any] = Field(
        default_factory=dict, description="Summary of Phase 6A query plan control signals."
    )
    packed_items: list[PackedContextItem] = Field(
        default_factory=list,
        description="Ordered list of packed context items fitting within budget.",
    )
    omitted_records: list[ContextOmissionRecord] = Field(
        default_factory=list,
        description="Audit records for all candidates omitted due to budget limits.",
    )
    stats: ContextPackingStats = Field(
        description="Comprehensive context budgeting and evidence utilization statistics."
    )
    formatted_context_str: str = Field(
        default="", description="Complete concatenated context string ready for prompt packing."
    )
    packing_latency_ms: float = Field(
        default=0.0, description="Execution time for context packing in milliseconds."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Observability metrics and metadata."
    )
