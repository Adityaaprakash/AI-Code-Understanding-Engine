"""Pure mathematical metrics module for Phase 5G Retrieval Evaluation."""

import math
from typing import Sequence

from retrieval.exceptions import EvaluationMetricError


def calculate_precision_at_k(
    retrieved: Sequence[str],
    relevant: set[str] | dict[str, int],
    k: int,
) -> float:
    """Calculate Precision@K metric.

    Precision@K = |Retrieved@K ∩ Relevant| / K

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        relevant: Set or dict of ground truth relevant chunk IDs.
        k: Cutoff depth (must be > 0).

    Returns:
        Precision score in range [0.0, 1.0].
    """
    if k <= 0:
        raise EvaluationMetricError(f"k must be > 0, got {k}")

    if not retrieved or not relevant:
        return 0.0

    retrieved_k = retrieved[:k]
    relevant_set = set(relevant.keys()) if isinstance(relevant, dict) else set(relevant)

    relevant_retrieved = sum(1 for chunk_id in retrieved_k if chunk_id in relevant_set)
    return relevant_retrieved / float(k)


def calculate_recall_at_k(
    retrieved: Sequence[str],
    relevant: set[str] | dict[str, int],
    k: int,
) -> float:
    """Calculate Recall@K metric.

    Recall@K = |Retrieved@K ∩ Relevant| / |Total Relevant|

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        relevant: Set or dict of ground truth relevant chunk IDs.
        k: Cutoff depth (must be > 0).

    Returns:
        Recall score in range [0.0, 1.0].
    """
    if k <= 0:
        raise EvaluationMetricError(f"k must be > 0, got {k}")

    if not retrieved or not relevant:
        return 0.0

    retrieved_k = retrieved[:k]
    relevant_set = set(relevant.keys()) if isinstance(relevant, dict) else set(relevant)

    if not relevant_set:
        return 0.0

    relevant_retrieved = sum(1 for chunk_id in retrieved_k if chunk_id in relevant_set)
    return relevant_retrieved / float(len(relevant_set))


def calculate_hit_rate_at_k(
    retrieved: Sequence[str],
    relevant: set[str] | dict[str, int],
    k: int,
) -> float:
    """Calculate HitRate@K (Hit Ratio) metric.

    HitRate@K = 1.0 if |Retrieved@K ∩ Relevant| > 0 else 0.0

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        relevant: Set or dict of ground truth relevant chunk IDs.
        k: Cutoff depth (must be > 0).

    Returns:
        1.0 if at least one relevant item is in top K, else 0.0.
    """
    if k <= 0:
        raise EvaluationMetricError(f"k must be > 0, got {k}")

    if not retrieved or not relevant:
        return 0.0

    retrieved_k = retrieved[:k]
    relevant_set = set(relevant.keys()) if isinstance(relevant, dict) else set(relevant)

    for chunk_id in retrieved_k:
        if chunk_id in relevant_set:
            return 1.0

    return 0.0


def calculate_reciprocal_rank(
    retrieved: Sequence[str],
    relevant: set[str] | dict[str, int],
) -> float:
    """Calculate Reciprocal Rank (RR) metric.

    RR = 1 / rank_of_first_relevant_result (1-indexed) or 0.0 if not found.

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        relevant: Set or dict of ground truth relevant chunk IDs.

    Returns:
        Reciprocal rank score in range [0.0, 1.0].
    """
    if not retrieved or not relevant:
        return 0.0

    relevant_set = set(relevant.keys()) if isinstance(relevant, dict) else set(relevant)

    for rank, chunk_id in enumerate(retrieved, start=1):
        if chunk_id in relevant_set:
            return 1.0 / float(rank)

    return 0.0


def calculate_ndcg_at_k(
    retrieved: Sequence[str],
    relevant: set[str] | dict[str, int],
    k: int,
) -> float:
    """Calculate Normalized Discounted Cumulative Gain (NDCG@K).

    NDCG@K = DCG@K / IDCG@K

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        relevant: Dict mapping chunk_id to grade score >= 1, or set of chunk_ids (default grade 1).
        k: Cutoff depth (must be > 0).

    Returns:
        NDCG score in range [0.0, 1.0].
    """
    if k <= 0:
        raise EvaluationMetricError(f"k must be > 0, got {k}")

    if not retrieved or not relevant:
        return 0.0

    graded_map: dict[str, int] = (
        relevant if isinstance(relevant, dict) else {cid: 1 for cid in relevant}
    )

    if not graded_map:
        return 0.0

    retrieved_k = retrieved[:k]

    # Calculate DCG@K
    dcg = 0.0
    for idx, chunk_id in enumerate(retrieved_k, start=1):
        rel_val = float(graded_map.get(chunk_id, 0))
        if rel_val > 0.0:
            dcg += rel_val / math.log2(idx + 1)

    # Calculate IDCG@K
    ideal_scores = sorted(graded_map.values(), reverse=True)[:k]
    idcg = 0.0
    for idx, rel_val in enumerate(ideal_scores, start=1):
        if rel_val > 0.0:
            idcg += float(rel_val) / math.log2(idx + 1)

    if idcg <= 0.0:
        return 0.0

    return dcg / idcg


def calculate_percentiles(values: Sequence[float]) -> tuple[float, float]:
    """Calculate P50 (median) and P95 latency percentiles.

    Args:
        values: Sequence of numeric values.

    Returns:
        Tuple of (P50, P95). Returns (0.0, 0.0) for empty input.
    """
    if not values:
        return (0.0, 0.0)

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    def percentile(p: float) -> float:
        if n == 1:
            return sorted_vals[0]
        k = (n - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_vals[int(k)]
        d0 = sorted_vals[int(f)] * (c - k)
        d1 = sorted_vals[int(c)] * (k - f)
        return d0 + d1

    p50 = percentile(0.50)
    p95 = percentile(0.95)
    return (p50, p95)
