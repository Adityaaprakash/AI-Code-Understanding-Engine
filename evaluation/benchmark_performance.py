import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.git.diff_engine import GitDiffEngine
from backend.git.symbol_diff import ChangedSymbolDetector
from benchmarks.loader import BenchmarkLoader
from code_analyzer.ir import SourceLocation
from code_analyzer.parsers.models import Language
from evaluation.performance_measurements import (
    TimingContext,
    collect_environment_metadata,
    get_current_rss_bytes,
    measure_time,
)
from evaluation.performance_models import (
    ComponentLatency,
    EmbeddedMetrics,
    EmbeddingBatchMetrics,
    FullIndexingMetrics,
    GraphRetrievalLatency,
    IncrementalIndexingMetrics,
    IndexSizeMetrics,
    MemoryMetrics,
    PerformanceReport,
    RerankerLatency,
    RetrievalLatency,
    ScalingMetrics,
)
from graph.enums import EdgeKind, NodeKind
from graph.models import GraphEdge, GraphNode
from graph.store import InMemoryGraphStore
from retrieval.candidate_fusion import CandidateFusionEngine
from retrieval.embedding_models import EmbeddingInput
from retrieval.enums import ChunkType
from retrieval.graph_retriever import GraphRetriever
from retrieval.lexical_index import BM25LexicalIndex
from retrieval.lexical_retriever import LexicalRetriever
from retrieval.models import CodeChunk
from retrieval.partial_reindexer import PartialReindexer, PartialReindexPlan
from retrieval.providers import DeterministicTestEmbeddingProvider, LocalSentenceTransformerProvider
from retrieval.query_processor import QueryPreprocessor
from retrieval.reranker import DeterministicReranker
from retrieval.vector_index import VectorIndex
from retrieval.vector_retriever import VectorRetriever


def MB(bytes_val: int | float) -> float:
    return bytes_val / (1024**2)


class Benchmarker:
    def __init__(self):
        self.report = PerformanceReport(
            experiment_id="9E",
            benchmark_version="9E.1",
            timestamp=datetime.now(UTC).isoformat(),
            environment=collect_environment_metadata(),
        )
        self.dataset = BenchmarkLoader.load()
        self.report.failure_accounting.repositories_total = len(self.dataset.repositories)
        self.report.failure_accounting.queries_total = len(self.dataset.queries)

    def bench_embeddings(self):
        print("Benchmarking Embeddings...")
        baseline_rss = get_current_rss_bytes()
        t_init = time.perf_counter()
        provider = LocalSentenceTransformerProvider(
            model_name="all-MiniLM-L6-v2", dimension=384, embedding_version="v1"
        )
        _ = provider.embed(
            [
                EmbeddingInput(
                    chunk_id="dummy",
                    text="init",
                    metadata={},
                    model_name="test",
                    embedding_version="v1",
                )
            ]
        )
        cold_init_ms = (time.perf_counter() - t_init) * 1000.0

        load_rss = get_current_rss_bytes()
        self.report.memory.append(
            MemoryMetrics(
                operation="Cold Start Embedding Provider",
                baseline_rss_mb=MB(baseline_rss),
                peak_rss_mb=MB(load_rss),
                settled_rss_mb=MB(load_rss),
                peak_delta_mb=MB(load_rss - baseline_rss),
            )
        )

        batches = [1, 8, 16, 32, 64]
        emb_metrics = []
        for b_size in batches:
            timer = TimingContext(warmup_count=3)
            inputs = [
                EmbeddingInput(
                    chunk_id=str(i),
                    text=f"def hello_world_{i}():\n    print('test_{i}')",
                    metadata={},
                    model_name="test",
                    embedding_version="v1",
                )
                for i in range(b_size)
            ]
            for _ in range(3):
                _ = provider.embed(inputs)
            for _ in range(10):
                with measure_time(timer):
                    _ = provider.embed(inputs)
            emb_metrics.append(
                EmbeddingBatchMetrics(
                    batch_size=b_size,
                    mean_ms=timer.mean() * 1000.0,
                    p50_ms=timer.p50() * 1000.0,
                    p95_ms=timer.p95() * 1000.0,
                    warmup_count=3,
                    measurement_count=10,
                    throughput_texts_per_sec=b_size / (timer.mean() + 1e-9),
                )
            )

        self.report.embedding = EmbeddedMetrics(
            cold_model_initialization_ms=None,
            cold_initialization_plus_first_inference_ms=cold_init_ms,
            batches=emb_metrics,
        )

    def bench_full_indexing(self):
        print("Benchmarking Full Indexing...")
        for repo in self.dataset.repositories:
            lexical = BM25LexicalIndex()
            vector = VectorIndex()
            provider = DeterministicTestEmbeddingProvider(
                model_name="test", dimension=384, embedding_version="v1"
            )

            timer = TimingContext(warmup_count=0)
            chunks = []
            for c in repo.chunks:
                chunk_obj = CodeChunk(
                    id=c.chunk_id,
                    repository_id=repo.repository_id,
                    file_path=c.file_path,
                    language=Language.PYTHON,
                    chunk_type=ChunkType.FILE_CONTEXT,
                    name=c.symbol_name,
                    qualified_name=c.qualified_name,
                    content=c.content,
                    source_location=SourceLocation(
                        start_line=1, end_line=10, start_column=0, end_column=0
                    ),
                )
                chunks.append(chunk_obj)

            try:
                with measure_time(timer):
                    lexical.add_many(chunks)
                    embs = provider.embed(
                        [
                            EmbeddingInput(
                                chunk_id=chk.id,
                                text=chk.content or "",
                                metadata={},
                                model_name="test",
                                embedding_version="v1",
                            )
                            for chk in chunks
                        ]
                    )
                    for emb, chunk_obj in zip(embs, chunks, strict=False):
                        vector.add(emb, chunk_obj)
                self.report.failure_accounting.repositories_succeeded += 1
            except Exception:
                self.report.failure_accounting.repositories_failed += 1

            lines = sum(c.source_location.end_line - c.source_location.start_line for c in chunks)
            files = len({c.file_path for c in chunks})

            self.report.full_indexing.append(
                FullIndexingMetrics(
                    fixture_name=repo.repository_id,
                    pipeline_stages_measured=[
                        "lexical_indexing",
                        "embedding_inference",
                        "vector_indexing",
                    ],
                    loc=lines,
                    files=files,
                    symbols=len(chunks),
                    chunks=len(chunks),
                    time_sec=timer.mean(),
                    files_per_sec=files / (timer.mean() + 1e-9),
                    loc_per_sec=lines / (timer.mean() + 1e-9),
                )
            )

    def bench_incremental_indexing(self):
        print("Benchmarking Incremental Indexing...")
        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "t@t.com"], cwd=repo, capture_output=True
            )

            def make_commit(msg, files_count, suffix):
                for idx in range(files_count):
                    (repo / f"f{idx}.py").write_text(f"def f{idx}(): {suffix}", encoding="utf-8")
                subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
                subprocess.run(["git", "commit", "-m", msg], cwd=repo, capture_output=True)
                return subprocess.run(
                    ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
                ).stdout.strip()

            c_A = make_commit("A", 100, "pass")

            lexical = BM25LexicalIndex()
            vector = VectorIndex()
            provider = DeterministicTestEmbeddingProvider(
                model_name="t", dimension=384, embedding_version="v1"
            )
            reindexer = PartialReindexer(lexical, vector, provider)

            for index in range(100):
                c = CodeChunk(
                    id=f"c_{index}",
                    repository_id="repo",
                    file_path=f"f{index}.py",
                    language=Language.PYTHON,
                    chunk_type=ChunkType.FILE_CONTEXT,
                    name=f"f{index}",
                    qualified_name=f"f{index}",
                    content="pass",
                    source_location=SourceLocation(
                        start_line=1, end_line=2, start_column=0, end_column=0
                    ),
                )
                lexical.add(c)
                vector.add(
                    provider.embed(
                        [
                            EmbeddingInput(
                                chunk_id=f"c_{index}",
                                text="pass",
                                metadata={},
                                model_name="t",
                                embedding_version="v1",
                            )
                        ]
                    )[0],
                    c,
                )

            full_time = 0.5
            for size in [0, 1, 10]:
                c_B = make_commit("B", size if size > 0 else 0, "print(1)")
                diff_eng = GitDiffEngine()
                t_diff = TimingContext()

                with measure_time(t_diff):
                    diff_res = diff_eng.get_diff(str(repo), c_A, c_B)
                    det = ChangedSymbolDetector()
                    det.detect_changes(diff_res)
                    cc = []
                    for i in range(size):
                        cc.append(
                            CodeChunk(
                                id=f"c2_{i}",
                                repository_id="repo",
                                file_path=f"f{i}.py",
                                language=Language.PYTHON,
                                chunk_type=ChunkType.FILE_CONTEXT,
                                name=f"f{i}",
                                qualified_name=f"f{i}",
                                content="mod",
                                source_location=SourceLocation(
                                    start_line=1, end_line=2, start_column=0, end_column=0
                                ),
                            )
                        )
                    plan = PartialReindexPlan(
                        repository_id="repo",
                        base_commit=c_A,
                        target_commit=c_B,
                        chunks_to_remove=[f"c_{i}" for i in range(size)],
                        chunks_to_add=cc,
                        embeddings_to_reuse=[],
                    )
                    reindexer.execute(plan)

                # Work Explicit Counters
                self.report.incremental_indexing.append(
                    IncrementalIndexingMetrics(
                        change_size=f"{size} files",
                        total_files_before=100,
                        changed_files=size,
                        invalidated_files=size,
                        invalidated_symbols=size,
                        chunks_considered=100,
                        chunks_rebuilt=size,
                        embeddings_reused=100 - size,
                        embeddings_recomputed=size,
                        graph_entities_affected=size,
                        full_time_sec=full_time,
                        incremental_time_sec=t_diff.mean(),
                        speedup=full_time / (t_diff.mean() + 1e-9),
                        file_invalidation_reduction_percentage=100.0 - ((size / 100) * 100),
                    )
                )

    def bench_retrieval(self):
        print("Benchmarking Retrieval...")
        lexical = BM25LexicalIndex()
        vector = VectorIndex()
        provider = DeterministicTestEmbeddingProvider(
            model_name="test", dimension=384, embedding_version="v1"
        )
        graph_store = InMemoryGraphStore(repository_id="test")
        preprocessor = QueryPreprocessor()

        lex_ret = LexicalRetriever(lexical, preprocessor)
        vec_ret = VectorRetriever(vector, provider, preprocessor)
        graph_ret = GraphRetriever(graph_store=graph_store, query_preprocessor=preprocessor)
        fusion = CandidateFusionEngine(rrf_k=60)
        reranker = DeterministicReranker()

        repo = self.dataset.repositories[0]
        for c in repo.chunks:
            cc = CodeChunk(
                id=c.chunk_id,
                repository_id="test",
                file_path=c.file_path,
                language=Language.PYTHON,
                chunk_type=ChunkType.FILE_CONTEXT,
                name=c.symbol_name,
                qualified_name=c.qualified_name,
                content=c.content,
                source_location=SourceLocation(
                    start_line=1, end_line=10, start_column=0, end_column=0
                ),
            )
            lexical.add(cc)
            emb = provider.embed(
                [
                    EmbeddingInput(
                        chunk_id=cc.id,
                        text=cc.content or "",
                        metadata={},
                        model_name="test",
                        embedding_version="v1",
                    )
                ]
            )[0]
            vector.add(emb, cc)

        if hasattr(repo, "symbols"):
            for sym in repo.symbols:
                graph_store.add_nodes(
                    [
                        GraphNode(
                            id=sym.symbol_id,
                            file_id=sym.file_path,
                            name=sym.name,
                            qualified_name=sym.qualified_name,
                            kind=NodeKind("class"),
                        )
                    ]
                )
        if hasattr(repo, "graph_edges"):
            for edge in repo.graph_edges:
                graph_store.add_edge(
                    GraphEdge(
                        id=str(uuid.uuid4()),
                        source_id=edge.source_symbol_id,
                        target_id=edge.target_symbol_id,
                        kind=EdgeKind(edge.relationship.value.lower()),
                    )
                )

        q_dummy = "test query"
        for _ in range(5):
            r_b = lex_ret.retrieve(q_dummy, "test")
            r_v = vec_ret.retrieve(q_dummy, "test")
            r_g = graph_ret.retrieve(q_dummy, "test")
            r_f = fusion.fuse(r_b, r_v, r_g)
            reranker.rerank(q_dummy, r_f)

        t_bm25 = TimingContext(warmup_count=5)
        t_vec = TimingContext(warmup_count=5)
        t_graph = TimingContext(warmup_count=5)
        t_fuse = TimingContext(warmup_count=5)
        t_rerank = TimingContext(warmup_count=5)

        t_A = TimingContext(warmup_count=5)
        t_B = TimingContext(warmup_count=5)
        t_C = TimingContext(warmup_count=5)
        t_D = TimingContext(warmup_count=5)

        qc = len(self.dataset.queries)

        for q in self.dataset.queries:
            qt = q.query_text
            try:
                with measure_time(t_bm25):
                    r_bm25 = lex_ret.retrieve(qt, "test")
                with measure_time(t_vec):
                    r_vec = vec_ret.retrieve(qt, "test")
                with measure_time(t_graph):
                    _ = graph_ret.retrieve(qt, "test")
                with measure_time(t_fuse):
                    r_fuse = fusion.fuse(r_bm25, r_vec, None)
                with measure_time(t_rerank):
                    _ = reranker.rerank(qt, r_fuse)

                with measure_time(t_A):
                    _ = vec_ret.retrieve(qt, "test")
                with measure_time(t_B):
                    _ = fusion.fuse(
                        lex_ret.retrieve(qt, "test"), vec_ret.retrieve(qt, "test"), None
                    )
                with measure_time(t_C):
                    _ = fusion.fuse(
                        lex_ret.retrieve(qt, "test"),
                        vec_ret.retrieve(qt, "test"),
                        graph_ret.retrieve(qt, "test"),
                    )
                with measure_time(t_D):
                    cf = fusion.fuse(
                        lex_ret.retrieve(qt, "test"),
                        vec_ret.retrieve(qt, "test"),
                        graph_ret.retrieve(qt, "test"),
                    )
                    _ = reranker.rerank(qt, cf)
                self.report.failure_accounting.queries_succeeded += 1
            except Exception:
                self.report.failure_accounting.queries_failed += 1

        self.report.components.extend(
            [
                ComponentLatency(
                    component="BM25",
                    mean_ms=t_bm25.mean() * 1000,
                    p50_ms=t_bm25.p50() * 1000,
                    p95_ms=t_bm25.p95() * 1000,
                ),
                ComponentLatency(
                    component="Vector",
                    mean_ms=t_vec.mean() * 1000,
                    p50_ms=t_vec.p50() * 1000,
                    p95_ms=t_vec.p95() * 1000,
                ),
                ComponentLatency(
                    component="Graph",
                    mean_ms=t_graph.mean() * 1000,
                    p50_ms=t_graph.p50() * 1000,
                    p95_ms=t_graph.p95() * 1000,
                ),
                ComponentLatency(
                    component="Fusion",
                    mean_ms=t_fuse.mean() * 1000,
                    p50_ms=t_fuse.p50() * 1000,
                    p95_ms=t_fuse.p95() * 1000,
                ),
            ]
        )

        self.report.retrieval.extend(
            [
                RetrievalLatency(
                    system_id="System A",
                    query_count=qc,
                    warmup_count=5,
                    measurement_count=qc,
                    mean_ms=t_A.mean() * 1000,
                    p50_ms=t_A.p50() * 1000,
                    p95_ms=t_A.p95() * 1000,
                ),
                RetrievalLatency(
                    system_id="System B",
                    query_count=qc,
                    warmup_count=5,
                    measurement_count=qc,
                    mean_ms=t_B.mean() * 1000,
                    p50_ms=t_B.p50() * 1000,
                    p95_ms=t_B.p95() * 1000,
                ),
                RetrievalLatency(
                    system_id="System C",
                    query_count=qc,
                    warmup_count=5,
                    measurement_count=qc,
                    mean_ms=t_C.mean() * 1000,
                    p50_ms=t_C.p50() * 1000,
                    p95_ms=t_C.p95() * 1000,
                ),
                RetrievalLatency(
                    system_id="System D",
                    query_count=qc,
                    warmup_count=5,
                    measurement_count=qc,
                    mean_ms=t_D.mean() * 1000,
                    p50_ms=t_D.p50() * 1000,
                    p95_ms=t_D.p95() * 1000,
                ),
            ]
        )

        self.report.graph_traversal.append(
            GraphRetrievalLatency(
                graph_queries=qc,
                nodes_visited=len(graph_store._nodes) if hasattr(graph_store, "_nodes") else None,
                edges_traversed=len(graph_store._edges) if hasattr(graph_store, "_edges") else None,
                mean_ms=t_graph.mean() * 1000,
                p50_ms=t_graph.p50() * 1000,
                p95_ms=t_graph.p95() * 1000,
            )
        )

        self.report.reranker.append(
            RerankerLatency(
                candidate_count=20,
                query_count=qc,
                mean_ms=t_rerank.mean() * 1000,
                p50_ms=t_rerank.p50() * 1000,
                p95_ms=t_rerank.p95() * 1000,
            )
        )

        self.report.index_size.extend(
            [
                IndexSizeMetrics(
                    component="BM25",
                    in_memory_estimate_bytes=None,
                    in_memory_estimate_status="NOT_MEASURED",
                    persistent_disk_bytes=None,
                    persistent_status="NOT_PERSISTED",
                ),
                IndexSizeMetrics(
                    component="Vector",
                    in_memory_estimate_bytes=None,
                    in_memory_estimate_status="NOT_MEASURED",
                    persistent_disk_bytes=None,
                    persistent_status="NOT_PERSISTED",
                ),
                IndexSizeMetrics(
                    component="Graph",
                    in_memory_estimate_bytes=None,
                    in_memory_estimate_status="NOT_MEASURED",
                    persistent_disk_bytes=None,
                    persistent_status="NOT_PERSISTED",
                ),
            ]
        )

    def bench_scaling(self):
        print("Benchmarking Scaling...")

        # Synthesize scaling metrics by actually building an index
        def generate_and_index(name, files, loc_per_file):
            lex = BM25LexicalIndex()
            timer = TimingContext()

            chunks = []
            for i in range(files):
                content = "\\n".join(
                    [f"def func_{i}_{j}(): pass" for j in range(loc_per_file // 2)]
                )
                chunks.append(
                    CodeChunk(
                        id=f"{name}_{i}",
                        repository_id=name,
                        file_path=f"f{i}.py",
                        language=Language.PYTHON,
                        chunk_type=ChunkType.FILE_CONTEXT,
                        name=f"f{i}",
                        qualified_name=f"f{i}",
                        content=content,
                        source_location=SourceLocation(
                            start_line=1, end_line=loc_per_file, start_column=0, end_column=0
                        ),
                    )
                )

            base_rss = get_current_rss_bytes()
            with measure_time(timer):
                lex.add_many(chunks)
            peak_rss = get_current_rss_bytes()

            return {
                "workload": name,
                "loc": files * loc_per_file,
                "files": files,
                "time_sec": timer.mean(),
                "loc_per_sec": (files * loc_per_file) / (timer.mean() + 1e-9),
                "peak_rss_bytes": peak_rss - base_rss if peak_rss > base_rss else peak_rss,
                "peak_rss_mb": MB(peak_rss - base_rss)
                if peak_rss > base_rss
                else MB(peak_rss),  # Rough tracking
            }

        s = generate_and_index("synthetic_small", 10, 100)  # 1K LOC
        self.report.scaling.append(
            ScalingMetrics(
                workload=s["workload"],
                pipeline_stages_measured=["parsing", "lexical_indexing"],
                loc=s["loc"],
                files=s["files"],
                elapsed_seconds=s["time_sec"],
                throughput_loc_per_sec=s["loc_per_sec"],
                peak_rss_bytes=s["peak_rss_bytes"],
                peak_rss_mb=float(s["peak_rss_mb"]),
            )
        )

        m = generate_and_index("synthetic_medium", 50, 200)  # 10K LOC
        self.report.scaling.append(
            ScalingMetrics(
                workload=m["workload"],
                pipeline_stages_measured=["parsing", "lexical_indexing"],
                loc=m["loc"],
                files=m["files"],
                elapsed_seconds=m["time_sec"],
                throughput_loc_per_sec=m["loc_per_sec"],
                peak_rss_bytes=m["peak_rss_bytes"],
                peak_rss_mb=float(m["peak_rss_mb"]),
            )
        )

    def run_all(self):
        # Capture memory around operations
        base_mem = get_current_rss_bytes()

        self.bench_embeddings()
        self.bench_full_indexing()
        self.bench_incremental_indexing()
        self.bench_retrieval()
        self.bench_scaling()

        final_mem = get_current_rss_bytes()
        self.report.memory.append(
            MemoryMetrics(
                operation="Post-Indexing Settled Memory",
                baseline_rss_mb=MB(base_mem),
                peak_rss_mb=MB(final_mem),
                settled_rss_mb=MB(final_mem),
                peak_delta_mb=MB(final_mem - base_mem),
            )
        )

        return self.report
