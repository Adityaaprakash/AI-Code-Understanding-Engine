"""Pydantic data models for embedding inputs, results, and batch processing."""

import math
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EmbeddingInput(BaseModel):
    """Structured representation of text input for embedding providers.

    Preserves chunk identity, formatted embedding text, and model context without
    duplicating Canonical IR objects.
    """

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    model_name: str
    embedding_version: str

    @field_validator("chunk_id", "text", "model_name", "embedding_version")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        """Ensure string fields are non-empty and stripped."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v.strip()


class EmbeddingResult(BaseModel):
    """Immutable representation of a generated dense vector embedding for a CodeChunk."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    vector: list[float]
    dimension: int
    provider_name: str
    model_name: str
    embedding_version: str
    repository_id: str
    commit_id: str | None = None
    commit_sha: str | None = None

    @field_validator(
        "chunk_id", "provider_name", "model_name", "embedding_version", "repository_id"
    )
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        """Ensure core metadata strings are non-empty."""
        if not v or not v.strip():
            raise ValueError("Identity strings cannot be empty or whitespace")
        return v.strip()

    @field_validator("dimension")
    @classmethod
    def validate_dimension_positive(cls, v: int) -> int:
        """Ensure dimension is positive."""
        if v <= 0:
            raise ValueError(f"Dimension must be > 0, got {v}")
        return v

    @field_validator("vector")
    @classmethod
    def validate_vector_values(cls, v: list[float]) -> list[float]:
        """Ensure vector is non-empty and contains only finite numbers (no NaN, Inf)."""
        if not v:
            raise ValueError("Vector cannot be empty")
        for val in v:
            if math.isnan(val) or math.isinf(val):
                raise ValueError("Vector contains non-finite values (NaN or Inf)")
        return v

    @model_validator(mode="after")
    def validate_vector_dimension_match(self) -> Self:
        """Ensure vector length matches configured dimension."""
        if len(self.vector) != self.dimension:
            raise ValueError(
                f"Vector length ({len(self.vector)}) does not match declared dimension ({self.dimension})"
            )
        return self


class EmbeddingFailure(BaseModel):
    """Structured representation of a failed embedding attempt for a CodeChunk."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    error_message: str
    retryable: bool = False


class EmbeddingBatchResult(BaseModel):
    """Container for batch embedding generation results and partial failures."""

    model_config = ConfigDict(frozen=True)

    results: list[EmbeddingResult]
    failures: list[EmbeddingFailure] = Field(default_factory=list)
    provider_name: str
    model_name: str
    dimension: int
    embedding_version: str

    @property
    def total_chunks(self) -> int:
        """Total number of chunks processed in the batch request."""
        return len(self.results) + len(self.failures)

    @property
    def succeeded_count(self) -> int:
        """Number of successfully embedded chunks."""
        return len(self.results)

    @property
    def failed_count(self) -> int:
        """Number of failed chunk embeddings."""
        return len(self.failures)

    @property
    def has_failures(self) -> bool:
        """Check if any chunk embeddings failed."""
        return len(self.failures) > 0
