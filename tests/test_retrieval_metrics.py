"""Unit test suite for Phase 5G retrieval evaluation metric calculations."""

import pytest

from evaluation.metrics import (
    calculate_hit_rate_at_k,
    calculate_ndcg_at_k,
    calculate_percentiles,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_reciprocal_rank,
)
from retrieval.exceptions import EvaluationMetricError


@pytest.mark.unit
def test_precision_at_k_exact() -> None:
    """Test Precision@K math."""
    retrieved = ["A", "B", "C", "D"]
    relevant = {"A", "C"}

    assert calculate_precision_at_k(retrieved, relevant, k=4) == 2.0 / 4.0  # 0.5
    assert calculate_precision_at_k(retrieved, relevant, k=2) == 1.0 / 2.0  # 0.5
    assert calculate_precision_at_k(retrieved, relevant, k=1) == 1.0 / 1.0  # 1.0


@pytest.mark.unit
def test_recall_at_k_exact() -> None:
    """Test Recall@K math."""
    retrieved = ["A", "B", "C", "D"]
    relevant = {"A", "C", "E"}

    assert calculate_recall_at_k(retrieved, relevant, k=4) == 2.0 / 3.0
    assert calculate_recall_at_k(retrieved, relevant, k=2) == 1.0 / 3.0


@pytest.mark.unit
def test_hit_rate_at_k_exact() -> None:
    """Test HitRate@K math."""
    retrieved = ["X", "Y", "A", "Z"]
    relevant = {"A", "B"}

    assert calculate_hit_rate_at_k(retrieved, relevant, k=1) == 0.0
    assert calculate_hit_rate_at_k(retrieved, relevant, k=2) == 0.0
    assert calculate_hit_rate_at_k(retrieved, relevant, k=3) == 1.0
    assert calculate_hit_rate_at_k(retrieved, relevant, k=4) == 1.0


@pytest.mark.unit
def test_reciprocal_rank_exact() -> None:
    """Test Reciprocal Rank (RR) math."""
    assert calculate_reciprocal_rank(["A", "B", "C"], {"A"}) == 1.0 / 1.0  # 1.0
    assert calculate_reciprocal_rank(["X", "A", "C"], {"A"}) == 1.0 / 2.0  # 0.5
    assert calculate_reciprocal_rank(["X", "Y", "Z"], {"A"}) == 0.0


@pytest.mark.unit
def test_ndcg_at_k_exact() -> None:
    """Test NDCG@K math with graded relevance."""
    retrieved = ["A", "B", "C"]
    relevant = {"A": 2, "B": 1, "C": 0}

    ndcg = calculate_ndcg_at_k(retrieved, relevant, k=3)
    assert 0.0 <= ndcg <= 1.0
    assert ndcg == 1.0  # Ideal ordering retrieved


@pytest.mark.unit
def test_percentiles_exact() -> None:
    """Test P50 and P95 percentile calculation."""
    values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    p50, p95 = calculate_percentiles(values)

    assert p50 == pytest.approx(55.0, abs=1.0)
    assert p95 > p50


@pytest.mark.unit
def test_empty_and_zero_handling() -> None:
    """Test metric functions with empty lists and zero results."""
    assert calculate_precision_at_k([], {"A"}, k=5) == 0.0
    assert calculate_recall_at_k(["A"], set(), k=5) == 0.0
    assert calculate_hit_rate_at_k([], set(), k=5) == 0.0
    assert calculate_reciprocal_rank([], {"A"}) == 0.0
    assert calculate_ndcg_at_k([], {"A": 1}, k=5) == 0.0
    assert calculate_percentiles([]) == (0.0, 0.0)


@pytest.mark.unit
def test_invalid_k_raises_error() -> None:
    """Test invalid k <= 0 raises EvaluationMetricError."""
    with pytest.raises(EvaluationMetricError):
        calculate_precision_at_k(["A"], {"A"}, k=0)

    with pytest.raises(EvaluationMetricError):
        calculate_recall_at_k(["A"], {"A"}, k=-1)
