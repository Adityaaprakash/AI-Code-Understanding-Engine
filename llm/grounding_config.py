"""Configuration models for Grounding Verification (Phase 6H)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm.exceptions import InvalidGroundingConfigError


class GroundingVerificationConfig(BaseModel):
    """Immutable configuration tuning grounding scores, thresholds, and behavior."""

    model_config = ConfigDict(frozen=True)

    supported_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum score bounded (0-1) representing fully supported claim.",
    )
    partial_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum score bounded (0-1) representing partially supported claim.",
    )

    weight_citation_validity: float = Field(
        default=0.2,
        ge=0.0,
        description="Score weight given strictly for citation resolution validity.",
    )
    weight_lexical_overlap: float = Field(
        default=0.8,
        ge=0.0,
        description="Score weight for deterministic token/lexical matching alignment.",
    )

    lexical_min_token_length: int = Field(
        default=3,
        ge=1,
        description="Minimum length threshold for lexical token matching overlap calculation.",
    )

    citation_marker_prefix: str = Field(
        default="[CTX:", description="Leading string pattern signaling a citation."
    )
    citation_marker_suffix: str = Field(
        default="]", description="Trailing string pattern bounding a citation marker."
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Custom experimental config fields."
    )

    @model_validator(mode="after")
    def validate_thresholds(self) -> "GroundingVerificationConfig":
        """Assures thresholds behave monotonically."""
        if self.supported_threshold <= self.partial_threshold:
            raise InvalidGroundingConfigError(
                "supported_threshold must strictly exceed partial_threshold."
            )
        return self
