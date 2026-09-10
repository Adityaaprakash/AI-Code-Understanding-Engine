from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MetricAtK(BaseModel):
    model_config = ConfigDict(frozen=True)
    k_1: float = 0.0
    k_3: float = 0.0
    k_5: float = 0.0
    k_10: float = 0.0

class RetrievalMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)
    mrr: float = 0.0
    precision: MetricAtK = Field(default_factory=MetricAtK)
    recall: MetricAtK = Field(default_factory=MetricAtK)
    hit_rate: MetricAtK = Field(default_factory=MetricAtK)
    ndcg: MetricAtK = Field(default_factory=MetricAtK)

class LatencyMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)
    mean_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0

class TokenMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)
    measured: bool = False
    prompt_tokens: float = 0.0
    completion_tokens: float = 0.0
    total_tokens: float = 0.0

class AnswerQualityMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)
    measured: bool = False
    correctness: float = 0.0
    citation_accuracy: float = 0.0
    citation_completeness: float = 0.0
    hallucination_rate: float = 0.0

class SystemResults(BaseModel):
    model_config = ConfigDict(frozen=True)
    system_id: str
    system_name: str
    query_count: int
    retrieval: RetrievalMetrics = Field(default_factory=RetrievalMetrics)
    latency: LatencyMetrics = Field(default_factory=LatencyMetrics)
    tokens: TokenMetrics = Field(default_factory=TokenMetrics)
    answer_quality: AnswerQualityMetrics = Field(default_factory=AnswerQualityMetrics)

class CategoryMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)
    category: str
    query_count: int
    retrieval: RetrievalMetrics = Field(default_factory=RetrievalMetrics)

class LanguageMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)
    language: str
    query_count: int
    retrieval: RetrievalMetrics = Field(default_factory=RetrievalMetrics)

class GraphSubsetMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)
    system_id: str
    query_count: int
    retrieval: RetrievalMetrics = Field(default_factory=RetrievalMetrics)
    graph_queries_overall: int = 0
    queries_with_graph_candidates: int | None = None
    graph_assisted_discoveries: int | None = None
    graph_only_discoveries: int | None = None
    provenance: str | None = None

class AblationDelta(BaseModel):
    model_config = ConfigDict(frozen=True)
    step_name: str
    mrr_absolute: float = 0.0
    mrr_relative: float = 0.0
    ndcg_5_absolute: float = 0.0
    ndcg_5_relative: float = 0.0
    precision_5_absolute: float = 0.0
    precision_5_relative: float = 0.0
    recall_5_absolute: float = 0.0
    recall_5_relative: float = 0.0
    hit_rate_5_absolute: float = 0.0
    hit_rate_5_relative: float = 0.0

class QueryLevelResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    query_id: str
    system_id: str
    repository_id: str
    category: str
    difficulty: str
    language: str
    graph_grounded: bool
    multi_hop: bool
    retrieved_chunk_ids: list[str]
    relevant_chunk_ids: list[str]
    retrieval: RetrievalMetrics = Field(default_factory=RetrievalMetrics)
    latency_ms: float = 0.0
    evaluation_error: str | None = None

class ResearchComparisonReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    experiment_id: str
    benchmark_version: str
    timestamp: str
    limitations: list[str] = Field(default_factory=list)
    system_configuration: dict[str, Any] = Field(default_factory=dict)

    systems: list[SystemResults] = Field(default_factory=list)
    category_breakdown: dict[str, list[CategoryMetrics]] = Field(default_factory=dict) # key is system_id
    language_breakdown: dict[str, list[LanguageMetrics]] = Field(default_factory=dict) # key is system_id
    graph_breakdown: list[GraphSubsetMetrics] = Field(default_factory=list)

    ablation_deltas: list[AblationDelta] = Field(default_factory=list)

    query_results: list[QueryLevelResult] = Field(default_factory=list)
