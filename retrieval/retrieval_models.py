"""Pydantic data models for Phase 5 retrieval contracts and search result candidates."""

import math
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from code_analyzer.parsers.models import Language
from retrieval.enums import ChunkType, RetrievalSource
from retrieval.query_models import ProcessedQuery


class LexicalRetrievalRequest(BaseModel):
    """Immutable request specification for lexical retrieval execution."""

    model_config = ConfigDict(frozen=True)

    query: str | ProcessedQuery
    repository_id: str
    top_k: int = 10
    language: Language | None = None
    chunk_type: ChunkType | None = None
    file_path: str | None = None
    commit_sha: str | None = None

    @field_validator("repository_id")
    @classmethod
    def validate_repository_id(cls, v: str) -> str:
        """Ensure repository_id is non-empty."""
        if not v or not v.strip():
            raise ValueError("repository_id cannot be empty or whitespace")
        return v.strip()

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, v: int) -> int:
        """Ensure top_k is positive (> 0)."""
        if v <= 0:
            raise ValueError(f"top_k must be > 0, got {v}")
        return v


class RetrievalResult(BaseModel):
    """Immutable representation of a single ranked retrieval candidate."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    score: float
    rank: int
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
    sources: list[RetrievalSource] = Field(default_factory=list)
    bm25_rank: int | None = None
    vector_rank: int | None = None
    graph_rank: int | None = None
    bm25_score: float | None = None
    vector_score: float | None = None
    graph_score: float | None = None
    fused_score: float | None = None
    rerank_score: float | None = None

    @field_validator("chunk_id", "repository_id", "file_path")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        """Ensure core identity strings are non-empty."""
        if not v or not v.strip():
            raise ValueError("Identity string cannot be empty or whitespace")
        return v.strip()

    @field_validator(
        "score", "bm25_score", "vector_score", "graph_score", "fused_score", "rerank_score"
    )
    @classmethod
    def validate_finite_scores(cls, v: float | None) -> float | None:
        """Ensure scores are finite float numbers if present."""
        if v is not None and (math.isnan(v) or math.isinf(v)):
            raise ValueError("Retrieval score must be a finite float number")
        return v

    @field_validator("rank", "bm25_rank", "vector_rank", "graph_rank")
    @classmethod
    def validate_rank_positive(cls, v: int | None) -> int | None:
        """Ensure ranks are 1-indexed and positive if present."""
        if v is not None and v <= 0:
            raise ValueError(f"Rank must be >= 1, got {v}")
        return v


class RetrievalResultSet(BaseModel):
    """Immutable container for Phase 5 ranked retrieval results and latency observability."""

    model_config = ConfigDict(frozen=True)

    query: ProcessedQuery
    repository_id: str
    results: list[RetrievalResult] = Field(default_factory=list)
    total_matches: int = 0
    preprocessing_latency_ms: float = 0.0
    retrieval_latency_ms: float = 0.0
    fusion_latency_ms: float = 0.0
    reranking_latency_ms: float = 0.0
    total_latency_ms: float = 0.0


    @field_validator("repository_id")
    @classmethod
    def validate_repository_id(cls, v: str) -> str:
        """Ensure repository_id is non-empty."""
        if not v or not v.strip():
            raise ValueError("repository_id cannot be empty or whitespace")
        return v.strip()

    @model_validator(mode="after")
    def validate_total_matches(self) -> Self:
        """Ensure total_matches matches or exceeds result list length."""
        if self.total_matches < len(self.results):
            object.__setattr__(self, "total_matches", len(self.results))
        return self
