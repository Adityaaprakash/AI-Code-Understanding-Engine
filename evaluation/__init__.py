"""Phase 5G Retrieval Evaluation package."""

from evaluation.benchmark import RetrievalBenchmarkRunner
from evaluation.dataset import get_synthetic_benchmark_dataset
from evaluation.metrics import (
    calculate_hit_rate_at_k,
    calculate_ndcg_at_k,
    calculate_percentiles,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_reciprocal_rank,
)
from evaluation.models import (
    BenchmarkReport,
    CategoryAggregateMetrics,
    EvaluationQuery,
    QueryCategory,
    QueryEvaluationResult,
    SourceContributionAnalysis,
    SystemAggregateMetrics,
)

__all__ = [
    "BenchmarkReport",
    "CategoryAggregateMetrics",
    "EvaluationQuery",
    "QueryCategory",
    "QueryEvaluationResult",
    "RetrievalBenchmarkRunner",
    "SourceContributionAnalysis",
    "SystemAggregateMetrics",
    "calculate_hit_rate_at_k",
    "calculate_ndcg_at_k",
    "calculate_percentiles",
    "calculate_precision_at_k",
    "calculate_recall_at_k",
    "calculate_reciprocal_rank",
    "get_synthetic_benchmark_dataset",
]
