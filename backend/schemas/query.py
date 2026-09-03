# backend/schemas/query.py
"""Schemas for phase 5 and phase 6 search and query APIs."""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    """Payload for submitting a codebase query."""

    query: str = Field(..., description="The natural language or code query.")
    repository_id: uuid.UUID = Field(..., description="ID of the repository to query against.")
    top_k: int = Field(
        10, ge=1, le=100, description="Maximum number of context candidate chunks to retrieve."
    )

    # Optional flags to switch between raw search and grounded chat
    generate_answer: bool = Field(True, description="If true, execute Phase 6 LLM generation.")


class SearchResultItem(BaseModel):
    """Metadata for a retrieved code chunk."""

    chunk_id: str
    file_path: str
    language: str
    score: float
    rank: int
    symbol_name: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    content: str | None = None


class GroundedAnswerResponse(BaseModel):
    """The generated answer with its grounding verification."""

    answer_text: str
    intent: str
    overall_status: str
    supported_claims: int
    total_claims: int
    generation_latency_ms: float
    metadata: dict[str, Any]


class QueryResponse(BaseModel):
    """Response encapsulating both search results and optionally an LLM answer."""

    model_config = ConfigDict(from_attributes=True)

    repository_id: uuid.UUID
    query: str
    normalized_query: str
    intent: str

    results: list[SearchResultItem]
    answer: GroundedAnswerResponse | None = None
