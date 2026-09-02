"""Configuration model for TASK-6D Context Deduplication & Pruning."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm.exceptions import InvalidPruningConfigError


class ContextPruningConfig(BaseModel):
    """Immutable configuration governing candidate context deduplication and pruning."""

    model_config = ConfigDict(frozen=True)

    enable_exact_deduplication: bool = Field(
        default=True,
        description="Whether to collapse exact candidate identity duplicates.",
    )
    enable_logical_deduplication: bool = Field(
        default=True,
        description="Whether to collapse logical code entity duplicates (same symbol/chunk).",
    )
    enable_near_duplicate_detection: bool = Field(
        default=False,
        description="Whether to collapse near-duplicate candidate representations deterministically.",
    )
    near_duplicate_threshold: float = Field(
        default=0.85,
        description="Deterministic similarity threshold for near-duplicate detection [0.0, 1.0].",
    )
    minimum_score: float = Field(
        default=0.0,
        description="Minimum ranking score threshold required for candidate survival [0.0, 1.0].",
    )
    max_candidates: int | None = Field(
        default=None,
        description="Maximum total candidates to retain (top-K limit). None means unlimited.",
    )
    max_candidates_per_symbol: int | None = Field(
        default=None,
        description="Maximum candidates retained for any single symbol. None means unlimited.",
    )
    max_candidates_per_file: int | None = Field(
        default=None,
        description="Maximum candidates retained for any single file path. None means unlimited.",
    )
    preserve_primary_targets: bool = Field(
        default=True,
        description="Avoid pruning explicit query primary targets if they exist.",
    )
    preserve_multi_source_evidence: bool = Field(
        default=True,
        description="Protect multi-source candidates (Retrieval + Graph Expansion) during pruning.",
    )
    preserve_structural_coverage: bool = Field(
        default=True,
        description="Protect structural relationship coverage candidates required by QueryPlan intent.",
    )

    @model_validator(mode="after")
    def _validate_config(self) -> ContextPruningConfig:
        """Validate pruning configuration bounds and settings."""
        if not (0.0 <= self.near_duplicate_threshold <= 1.0):
            raise InvalidPruningConfigError(
                f"near_duplicate_threshold must be in [0.0, 1.0], got {self.near_duplicate_threshold}"
            )

        if not (0.0 <= self.minimum_score <= 1.0):
            raise InvalidPruningConfigError(
                f"minimum_score must be in [0.0, 1.0], got {self.minimum_score}"
            )

        if self.max_candidates is not None and self.max_candidates <= 0:
            raise InvalidPruningConfigError(
                f"max_candidates must be > 0 if specified, got {self.max_candidates}"
            )

        if self.max_candidates_per_symbol is not None and self.max_candidates_per_symbol <= 0:
            raise InvalidPruningConfigError(
                f"max_candidates_per_symbol must be > 0 if specified, got {self.max_candidates_per_symbol}"
            )

        if self.max_candidates_per_file is not None and self.max_candidates_per_file <= 0:
            raise InvalidPruningConfigError(
                f"max_candidates_per_file must be > 0 if specified, got {self.max_candidates_per_file}"
            )

        return self
