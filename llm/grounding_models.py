"""Pydantic data models for Grounding and Citation Verification (Phase 6H)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from llm.enums import CitationStatus, ClaimStatus, GroundingReasonCode, GroundingStatus


class CitationReference(BaseModel):
    """Immutable representation of a citation marker extracted from an answer."""

    model_config = ConfigDict(frozen=True)

    marker: str = Field(..., description="The raw citation marker string (e.g., '[CTX:item-123]').")
    context_id: str | None = Field(None, description="The parsed context-item ID, if present.")
    status: CitationStatus = Field(
        default=CitationStatus.UNRESOLVED,
        description="Verification status of the citation against the available context.",
    )
    reason_codes: list[GroundingReasonCode] = Field(
        default_factory=list, description="Reason codes describing the citation interpretation."
    )


class GroundingClaim(BaseModel):
    """Immutable representation of an extracted factual claim and its evidence support."""

    model_config = ConfigDict(frozen=True)

    claim_id: str = Field(..., description="A unique deterministic ID for the extracted claim.")
    text: str = Field(..., description="The extracted claim text.")
    order_index: int = Field(..., description="Position/order index of the claim in the answer.")
    citations: list[CitationReference] = Field(
        default_factory=list, description="List of citations physically mapped to this claim."
    )
    supported_context_ids: list[str] = Field(
        default_factory=list,
        description="List of context IDs successfully supporting this claim after checking.",
    )
    evidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Deterministic support score evaluating this claim against the provided evidence.",
    )
    status: ClaimStatus = Field(
        default=ClaimStatus.UNVERIFIABLE,
        description="Final Support verification status of the claim.",
    )
    reason_codes: list[GroundingReasonCode] = Field(
        default_factory=list, description="Reasons justifying the assigned claim status."
    )


class GroundingMetrics(BaseModel):
    """Calculated deterministic metrics reflecting overall verification quality."""

    model_config = ConfigDict(frozen=True)

    total_claims: int = Field(0, description="Total number of claims extracted.")
    supported_claims: int = Field(0, description="Number of fully supported claims.")
    partially_supported_claims: int = Field(0, description="Number of partially supported claims.")
    unsupported_claims: int = Field(0, description="Number of decisively unsupported claims.")
    uncited_claims: int = Field(0, description="Number of claims without citations.")

    total_citations: int = Field(0, description="Total number of citations parsed.")
    valid_citations: int = Field(
        0, description="Number of citations successfully mapping to known context IDs."
    )
    invalid_citations: int = Field(
        0, description="Citations failing resolution or matching unknown IDs."
    )

    citation_coverage: float = Field(
        0.0, ge=0.0, le=1.0, description="Ratio of claims possessing at least one citation."
    )
    grounding_coverage: float = Field(
        0.0, ge=0.0, le=1.0, description="Ratio of supported claims vs total claims."
    )
    average_support_score: float = Field(
        0.0, ge=0.0, le=1.0, description="Mean evidence score across claims."
    )


class GroundingVerificationResult(BaseModel):
    """Immutable final verification structured result of TASK-6H."""

    model_config = ConfigDict(frozen=True)

    answer_id: str = Field(
        ..., description="ID matching the input GeneratedAnswer metadata if available."
    )
    claims: list[GroundingClaim] = Field(
        ..., description="List of all extracted claims mapping to contextual support."
    )
    metrics: GroundingMetrics = Field(
        ..., description="Calculated aggregate metrics describing support confidence."
    )
    overall_status: GroundingStatus = Field(
        ..., description="The definitive comprehensive grounding resolution status."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Execution logging attributes and verifiable thresholds."
    )
