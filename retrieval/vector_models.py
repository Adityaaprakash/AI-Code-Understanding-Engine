"""Pydantic data models for vector document storage and vector search results."""

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from code_analyzer.parsers.models import Language
from retrieval.enums import ChunkType


class VectorDocument(BaseModel):
    """Internal representation of a vector-indexed code chunk embedding."""

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
    file_path: str
    language: Language
    chunk_type: ChunkType
    symbol_name: str | None = None
    qualified_name: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "chunk_id", "provider_name", "model_name", "embedding_version", "repository_id", "file_path"
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
        """Ensure dimension is positive (> 0)."""
        if v <= 0:
            raise ValueError(f"Dimension must be > 0, got {v}")
        return v

    @field_validator("vector")
    @classmethod
    def validate_vector_finite(cls, v: list[float]) -> list[float]:
        """Ensure vector contains only finite floats."""
        if not v:
            raise ValueError("Vector cannot be empty")
        for val in v:
            if math.isnan(val) or math.isinf(val):
                raise ValueError("Vector contains non-finite values (NaN or Inf)")
        return v


class VectorSearchResult(BaseModel):
    """Immutable representation of a raw vector search match from the vector index."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    score: float
    repository_id: str
    commit_id: str | None = None
    commit_sha: str | None = None
    file_path: str
    language: Language
    chunk_type: ChunkType
    symbol_name: str | None = None
    qualified_name: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("chunk_id", "repository_id", "file_path")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        """Ensure identity strings are non-empty."""
        if not v or not v.strip():
            raise ValueError("Identity string cannot be empty or whitespace")
        return v.strip()

    @field_validator("score")
    @classmethod
    def validate_finite_score(cls, v: float) -> float:
        """Ensure similarity score is a finite float."""
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Score must be a finite float number")
        return v
