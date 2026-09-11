from pydantic import BaseModel, Field


class MeasurementStats(BaseModel):
    mean: float | None = None
    p50: float | None = None
    p95: float | None = None


class EnvironmentMetadata(BaseModel):
    os: str
    platform: str
    python: str
    cpu: str
    logical_cpus: int
    physical_cpus: int
    ram_bytes: int
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int
    device: str


class FullIndexingMetrics(BaseModel):
    fixture_name: str
    pipeline_stages_measured: list[str] = Field(default_factory=list)
    loc: int
    files: int
    symbols: int
    chunks: int
    time_sec: float
    files_per_sec: float | None = None
    loc_per_sec: float | None = None


class IncrementalIndexingMetrics(BaseModel):
    change_size: str
    total_files_before: int | None = None
    changed_files: int | None = None
    invalidated_files: int | None = None
    invalidated_symbols: int | None = None
    chunks_considered: int | None = None
    chunks_rebuilt: int | None = None
    embeddings_reused: int | None = None
    embeddings_recomputed: int | None = None
    graph_entities_affected: int | None = None
    full_time_sec: float
    incremental_time_sec: float
    speedup: float | None = None
    file_invalidation_reduction_percentage: float | None = None


class FailureAccounting(BaseModel):
    queries_total: int = 0
    queries_succeeded: int = 0
    queries_failed: int = 0
    timeouts: int = 0
    exceptions: int = 0
    fallbacks: int = 0
    repositories_total: int = 0
    repositories_succeeded: int = 0
    repositories_failed: int = 0
    files_failed: int = 0
    embedding_failures: int = 0
    graph_failures: int = 0


class RetrievalLatency(BaseModel):
    system_id: str
    query_count: int
    warmup_count: int
    measurement_count: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    preprocessing_ms: float | None = None
    query_embedding_ms: float | None = None
    vector_retrieval_ms: float | None = None
    bm25_retrieval_ms: float | None = None
    graph_retrieval_ms: float | None = None
    fusion_ms: float | None = None
    reranking_ms: float | None = None
    total_ms: float | None = None


class GraphRetrievalLatency(BaseModel):
    graph_queries: int
    nodes_visited: int | None = None
    edges_traversed: int | None = None
    mean_ms: float
    p50_ms: float
    p95_ms: float


class RerankerLatency(BaseModel):
    candidate_count: int
    query_count: int
    mean_ms: float
    p50_ms: float
    p95_ms: float


class ComponentLatency(BaseModel):
    component: str
    mean_ms: float
    p50_ms: float
    p95_ms: float


class EmbeddingBatchMetrics(BaseModel):
    batch_size: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    warmup_count: int
    measurement_count: int
    throughput_texts_per_sec: float


class EmbeddedMetrics(BaseModel):
    cold_model_initialization_ms: float | None = None
    cold_initialization_plus_first_inference_ms: float | None = None
    batches: list[EmbeddingBatchMetrics] = Field(default_factory=list)


class MemoryMetrics(BaseModel):
    operation: str
    baseline_rss_mb: float
    peak_rss_mb: float
    settled_rss_mb: float
    peak_delta_mb: float


class IndexSizeMetrics(BaseModel):
    component: str
    in_memory_estimate_bytes: int | None = None
    in_memory_estimate_status: str | None = None
    persistent_disk_bytes: int | None = None
    persistent_status: str | None = None


class ScalingMetrics(BaseModel):
    workload: str
    pipeline_stages_measured: list[str] = Field(default_factory=list)
    loc: int
    files: int
    elapsed_seconds: float
    throughput_loc_per_sec: float
    peak_rss_bytes: int
    peak_rss_mb: float


class PerformanceReport(BaseModel):
    experiment_id: str = "9E"
    benchmark_version: str = "9E.1"
    timestamp: str
    environment: EnvironmentMetadata

    fixtures: list[str] = Field(default_factory=list)

    full_indexing: list[FullIndexingMetrics] = Field(default_factory=list)
    incremental_indexing: list[IncrementalIndexingMetrics] = Field(default_factory=list)
    embedding: EmbeddedMetrics | None = None
    retrieval: list[RetrievalLatency] = Field(default_factory=list)
    graph_traversal: list[GraphRetrievalLatency] = Field(default_factory=list)
    reranker: list[RerankerLatency] = Field(default_factory=list)
    components: list[ComponentLatency] = Field(default_factory=list)
    memory: list[MemoryMetrics] = Field(default_factory=list)
    index_size: list[IndexSizeMetrics] = Field(default_factory=list)
    scaling: list[ScalingMetrics] = Field(default_factory=list)
    failure_accounting: FailureAccounting = Field(default_factory=FailureAccounting)

    limitations: list[str] = Field(default_factory=list)
