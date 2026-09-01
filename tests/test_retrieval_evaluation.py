"""Unit and integration test suite for Phase 5G Retrieval Evaluation & Benchmark (RetrievalBenchmarkRunner)."""

import pytest

from evaluation.benchmark import RetrievalBenchmarkRunner
from evaluation.dataset import get_synthetic_benchmark_dataset
from evaluation.models import BenchmarkReport, SystemAggregateMetrics


@pytest.fixture
def runner() -> RetrievalBenchmarkRunner:
    return RetrievalBenchmarkRunner(repository_id="test-bench-repo", top_k=5)


@pytest.mark.unit
def test_dataset_loader() -> None:
    """TC-1: Ground truth benchmark dataset loads deterministically."""
    chunks, queries = get_synthetic_benchmark_dataset(repository_id="test-repo")

    assert len(chunks) >= 10
    assert len(queries) == 7
    query_categories = {q.category for q in queries}
    assert len(query_categories) == 7


@pytest.mark.unit
def test_benchmark_execution(runner: RetrievalBenchmarkRunner) -> None:
    """TC-2: Full benchmark execution completes and produces valid BenchmarkReport."""
    report = runner.run_benchmark()

    assert isinstance(report, BenchmarkReport)
    assert report.benchmark_version == "v1"
    assert len(report.systems) == 6
    assert len(report.query_results) == 7 * 6


@pytest.mark.unit
def test_ablation_comparison(runner: RetrievalBenchmarkRunner) -> None:
    """TC-3: Ablation comparison includes Vector-only vs BM25 vs Graph vs Hybrid + Reranker."""
    report = runner.run_benchmark()
    systems_map: dict[str, SystemAggregateMetrics] = {s.system_name: s for s in report.systems}

    assert RetrievalBenchmarkRunner.SYSTEM_A_BM25 in systems_map
    assert RetrievalBenchmarkRunner.SYSTEM_B_VECTOR in systems_map
    assert RetrievalBenchmarkRunner.SYSTEM_C_GRAPH in systems_map
    assert RetrievalBenchmarkRunner.SYSTEM_D_BM25_VECTOR in systems_map
    assert RetrievalBenchmarkRunner.SYSTEM_E_HYBRID_RRF in systems_map
    assert RetrievalBenchmarkRunner.SYSTEM_F_HYBRID_RERANK in systems_map

    hybrid_rerank = systems_map[RetrievalBenchmarkRunner.SYSTEM_F_HYBRID_RERANK]
    vector_only = systems_map[RetrievalBenchmarkRunner.SYSTEM_B_VECTOR]

    # Full hybrid + rerank should outperform vector baseline on comprehensive test set
    assert hybrid_rerank.mean_recall >= vector_only.mean_recall
    assert hybrid_rerank.mrr >= vector_only.mrr


@pytest.mark.unit
def test_category_breakdown(runner: RetrievalBenchmarkRunner) -> None:
    """TC-4: Benchmark produces category-level metric breakdowns."""
    report = runner.run_benchmark()

    assert len(report.category_breakdown) > 0
    categories = {c.category for c in report.category_breakdown}
    assert len(categories) == 7


@pytest.mark.unit
def test_source_contribution_analysis(runner: RetrievalBenchmarkRunner) -> None:
    """TC-5: Source contribution analysis calculates ground truth chunk discovery across branches."""
    report = runner.run_benchmark()
    source_info = report.source_contribution

    assert source_info.total_relevant_found > 0
    assert (
        source_info.bm25_only_found
        + source_info.vector_only_found
        + source_info.graph_only_found
        + source_info.bm25_vector_found
        + source_info.bm25_graph_found
        + source_info.vector_graph_found
        + source_info.all_three_found
    ) == source_info.total_relevant_found


@pytest.mark.unit
def test_report_json_serialization(runner: RetrievalBenchmarkRunner) -> None:
    """TC-6: BenchmarkReport serializes cleanly to Pydantic JSON and back."""
    report = runner.run_benchmark()
    json_str = report.model_dump_json()

    roundtrip = BenchmarkReport.model_validate_json(json_str)

    assert roundtrip.benchmark_version == report.benchmark_version
    assert roundtrip.repository_id == report.repository_id
    assert len(roundtrip.systems) == len(report.systems)


@pytest.mark.unit
def test_benchmark_reproducibility(runner: RetrievalBenchmarkRunner) -> None:
    """TC-7: Running benchmark twice on same setup yields 100% identical metrics."""
    report1 = runner.run_benchmark()
    report2 = runner.run_benchmark()

    for s1, s2 in zip(report1.systems, report2.systems, strict=True):
        assert s1.system_name == s2.system_name
        assert s1.mean_precision == pytest.approx(s2.mean_precision)
        assert s1.mean_recall == pytest.approx(s2.mean_recall)
        assert s1.mrr == pytest.approx(s2.mrr)
