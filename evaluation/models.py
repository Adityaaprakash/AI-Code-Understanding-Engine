"""Pydantic data models for Phase 5G Retrieval Evaluation & Benchmarking."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QueryCategory(StrEnum):
    """Supported evaluation query classification categories."""

    SEMANTIC = "semantic"
    IDENTIFIER = "identifier"
    RELATIONSHIP = "relationship"
    DEPENDENCY = "dependency"
    IMPLEMENTATION = "implementation"
    CONFIGURATION = "configuration"
    MIXED = "mixed"


class EvaluationQuery(BaseModel):
    """Immutable representation of a ground truth evaluation benchmark query."""

    model_config = ConfigDict(frozen=True)

    query_id: str
    question: str
    repository_id: str
    category: QueryCategory
    relevant_chunk_ids: list[str]
    graded_relevance: dict[str, int] = Field(default_factory=dict)
    commit_sha: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("query_id", "question", "repository_id")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Evaluation query string cannot be empty")
        return v.strip()

    @field_validator("relevant_chunk_ids")
    @classmethod
    def validate_relevant_chunk_ids(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("relevant_chunk_ids list cannot be empty for ground truth query")
        return v


class QueryEvaluationResult(BaseModel):
    """Immutable evaluation metrics record for a single query execution against a system."""

    model_config = ConfigDict(frozen=True)

    query_id: str
    system_name: str
    category: QueryCategory
    top_k: int
    retrieved_chunk_ids: list[str]
    relevant_chunk_ids: list[str]
    precision: float
    recall: float
    hit_rate: float
    mrr: float
    ndcg: float = 0.0
    latency_ms: float = 0.0


class SystemAggregateMetrics(BaseModel):
    """Aggregated evaluation metrics summary across all queries for a specific retrieval system configuration."""

    model_config = ConfigDict(frozen=True)

    system_name: str
    num_queries: int
    mean_precision: float
    mean_recall: float
    mean_hit_rate: float
    mrr: float
    mean_ndcg: float
    mean_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float


class CategoryAggregateMetrics(BaseModel):
    """Aggregated metrics summary broken down by query category for a retrieval system."""

    model_config = ConfigDict(frozen=True)

    category: QueryCategory
    system_name: str
    num_queries: int
    mean_precision: float
    mean_recall: float
    mean_hit_rate: float
    mrr: float
    mean_ndcg: float


class SourceContributionAnalysis(BaseModel):
    """Analysis of ground truth chunk discovery across independent retrieval branch sources."""

    model_config = ConfigDict(frozen=True)

    bm25_only_found: int = 0
    vector_only_found: int = 0
    graph_only_found: int = 0
    bm25_vector_found: int = 0
    bm25_graph_found: int = 0
    vector_graph_found: int = 0
    all_three_found: int = 0
    total_relevant_found: int = 0


class BenchmarkReport(BaseModel):
    """Complete, serializable benchmark report containing system metrics, category breakdowns, and query logs."""

    model_config = ConfigDict(frozen=True)

    benchmark_version: str = "v1"
    repository_id: str
    top_k: int
    systems: list[SystemAggregateMetrics]
    category_breakdown: list[CategoryAggregateMetrics]
    source_contribution: SourceContributionAnalysis
    query_results: list[QueryEvaluationResult]
