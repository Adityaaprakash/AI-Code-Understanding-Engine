"""Pydantic data models for search query preprocessing and classification."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QueryKind(StrEnum):
    """Supported search query classification categories in CodeLens AI retrieval pipeline."""

    IDENTIFIER = "identifier"
    QUALIFIED_IDENTIFIER = "qualified_identifier"
    NATURAL_LANGUAGE = "natural_language"
    MIXED = "mixed"
    RELATIONSHIP = "relationship"
    PATH_OR_FILE = "path_or_file"
    UNKNOWN = "unknown"


class ProcessedQuery(BaseModel):
    """Immutable representation of a preprocessed, normalized, and classified search query."""

    model_config = ConfigDict(frozen=True)

    original_query: str
    normalized_query: str
    tokens: list[str] = Field(default_factory=list)
    identifier_tokens: list[str] = Field(default_factory=list)
    text_tokens: list[str] = Field(default_factory=list)
    qualified_name_candidates: list[str] = Field(default_factory=list)
    query_kind: QueryKind = QueryKind.UNKNOWN
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("original_query", "normalized_query")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        """Ensure original and normalized queries are non-empty."""
        if not v or not v.strip():
            raise ValueError("Query string cannot be empty or whitespace")
        return v
