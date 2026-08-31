"""Pydantic data models for lexical BM25 indexing and search results."""

import math
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from code_analyzer.parsers.models import Language
from retrieval.enums import ChunkType


class LexicalDocument(BaseModel):
    """Immutable representation of a code chunk prepared for lexical indexing.

    Stores chunk identity, path, language, revision metadata, and code-aware field tokens.
    Does NOT duplicate the full source code or Canonical IR objects.
    """

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    repository_id: str
    commit_id: str | None = None
    commit_sha: str | None = None
    file_path: str
    symbol_name: str | None = None
    chunk_type: ChunkType
    language: Language
    field_tokens: dict[str, list[str]] = Field(default_factory=dict)
    all_tokens: list[str] = Field(default_factory=list)
    doc_len: int

    @field_validator("chunk_id", "repository_id", "file_path")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        """Ensure core identity strings are non-empty and stripped."""
        if not v or not v.strip():
            raise ValueError("Identity string cannot be empty or whitespace")
        return v.strip()

    @field_validator("doc_len")
    @classmethod
    def validate_doc_len_non_negative(cls, v: int) -> int:
        """Ensure document length is non-negative."""
        if v < 0:
            raise ValueError(f"doc_len must be >= 0, got {v}")
        return v


class LexicalSearchResult(BaseModel):
    """Immutable representation of a single BM25 search result candidate."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    score: float
    rank: int
    repository_id: str
    commit_id: str | None = None
    commit_sha: str | None = None
    file_path: str
    symbol_name: str | None = None
    chunk_type: ChunkType
    language: Language

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
        """Ensure BM25 score is finite (not NaN or Inf)."""
        if math.isnan(v) or math.isinf(v):
            raise ValueError("BM25 score must be a finite float number")
        return v

    @field_validator("rank")
    @classmethod
    def validate_rank_positive(cls, v: int) -> int:
        """Ensure rank is 1-indexed and positive."""
        if v <= 0:
            raise ValueError(f"Rank must be >= 1, got {v}")
        return v


class LexicalSearchResultSet(BaseModel):
    """Container for BM25 search results across a repository query."""

    model_config = ConfigDict(frozen=True)

    query: str
    repository_id: str | None = None
    results: list[LexicalSearchResult] = Field(default_factory=list)
    total_matches: int = 0

    @model_validator(mode="after")
    def validate_total_matches(self) -> Self:
        """Ensure total_matches matches or exceeds result list length."""
        if self.total_matches < len(self.results):
            object.__setattr__(self, "total_matches", len(self.results))
        return self
