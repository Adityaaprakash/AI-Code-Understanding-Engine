from evaluation.performance_measurements import TimingContext
from evaluation.performance_models import (
    EmbeddingBatchMetrics,
    EnvironmentMetadata,
    FailureAccounting,
    IncrementalIndexingMetrics,
    IndexSizeMetrics,
    MemoryMetrics,
    PerformanceReport,
    RerankerLatency,
    RetrievalLatency,
    ScalingMetrics,
)


def test_timing_context_percentiles():
    timer = TimingContext(warmup_count=3)

    assert timer.mean() == 0.0
    assert timer.p50() == 0.0
    assert timer.p95() == 0.0
    assert timer.sample_count == 0

    for d in [10.0, 20.0, 30.0, 40.0, 50.0]:
        timer.add(d)

    assert timer.sample_count == 5
    assert timer.mean() == 30.0
    assert timer.p50() == 30.0
    assert timer.p95() >= 40.0


def test_embedding_batch_schema():
    batch = EmbeddingBatchMetrics(
        batch_size=8,
        mean_ms=10.0,
        p50_ms=9.0,
        p95_ms=15.0,
        warmup_count=3,
        measurement_count=10,
        throughput_texts_per_sec=800.0,
    )
    assert batch.batch_size == 8
    assert batch.p50_ms == 9.0
    assert batch.throughput_texts_per_sec == 800.0


def test_incremental_speedup():
    inc = IncrementalIndexingMetrics(
        change_size="1 files",
        total_files_before=100,
        changed_files=1,
        invalidated_files=1,
        invalidated_symbols=10,
        chunks_considered=100,
        chunks_rebuilt=1,
        embeddings_reused=99,
        embeddings_recomputed=1,
        graph_entities_affected=2,
        full_time_sec=100.0,
        incremental_time_sec=10.0,
        speedup=10.0,
        file_invalidation_reduction_percentage=99.0,
    )
    assert inc.speedup == 10.0
    assert inc.file_invalidation_reduction_percentage == 99.0


def test_retrieval_abcd_taxonomy():
    abcd_labels = ["System A", "System B", "System C", "System D"]
    for i, sys_name in enumerate(abcd_labels):
        r = RetrievalLatency(
            system_id=sys_name,
            query_count=48,
            warmup_count=5,
            measurement_count=48,
            mean_ms=10.0 * (i + 1),
            p50_ms=9.0 * (i + 1),
            p95_ms=15.0 * (i + 1),
        )
        assert r.system_id in abcd_labels
        assert r.query_count == 48


def test_reranker_invocation_measurement():
    r = RerankerLatency(candidate_count=20, query_count=48, mean_ms=5.0, p50_ms=4.8, p95_ms=6.1)
    assert r.candidate_count == 20
    assert r.query_count == 48
    assert r.mean_ms == 5.0


def test_scaling_schema():
    s = ScalingMetrics(
        workload="medium",
        pipeline_stages_measured=["parsing", "lexical_indexing"],
        loc=10000,
        files=100,
        elapsed_seconds=5.0,
        throughput_loc_per_sec=2000.0,
        peak_rss_bytes=100000,
        peak_rss_mb=100.0,
    )
    assert s.workload == "medium"
    assert s.loc == 10000
    assert s.files == 100


def test_index_size_semantics():
    size = IndexSizeMetrics(
        component="BM25",
        in_memory_estimate_bytes=1024,
        persistent_disk_bytes=None,
        persistent_status="NOT_PERSISTED",
    )
    assert size.in_memory_estimate_bytes == 1024
    assert size.persistent_disk_bytes is None
    assert size.persistent_status == "NOT_PERSISTED"


def test_memory_schema_delta():
    m = MemoryMetrics(
        operation="Initialization",
        baseline_rss_mb=50.0,
        peak_rss_mb=250.0,
        settled_rss_mb=200.0,
        peak_delta_mb=200.0,
    )
    assert m.peak_delta_mb == 200.0


def test_failure_accounting():
    f = FailureAccounting()
    assert f.queries_total == 0
    f.queries_total = 100
    f.queries_succeeded = 98
    f.queries_failed = 2
    assert f.queries_failed == 2
    assert f.queries_succeeded == 98


def test_performance_report_serialization():
    env = EnvironmentMetadata(
        os="Windows",
        platform="Win11",
        python="3.11",
        cpu="Intel",
        logical_cpus=8,
        physical_cpus=4,
        ram_bytes=16000000000,
        embedding_provider="test",
        embedding_model="test",
        embedding_dimensions=384,
        device="cpu",
    )
    report = PerformanceReport(
        experiment_id="9E",
        benchmark_version="9E.1",
        timestamp="2026-09-11T00:00:00Z",
        environment=env,
    )
    json_str = report.model_dump_json()
    assert "experiment_id" in json_str
    assert "environment" in json_str
    assert "failure_accounting" in json_str


def test_graph_fixture_population_schema():
    from graph.enums import EdgeKind, NodeKind
    from graph.models import GraphEdge, GraphNode

    n = GraphNode(
        id="test_id", file_id="f.py", name="f", qualified_name="f.py:f", kind=NodeKind("class")
    )
    e = GraphEdge(id="edge_1", source_id="test_id", target_id="target_id", kind=EdgeKind("calls"))

    assert n.kind == "class"
    assert e.kind == "calls"
