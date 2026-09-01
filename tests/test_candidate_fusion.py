"""Unit and integration test suite for TASK-5E Candidate Fusion (CandidateFusionEngine)."""

import pytest

from code_analyzer.parsers.models import Language
from retrieval.candidate_fusion import CandidateFusionEngine
from retrieval.enums import ChunkType, RetrievalSource
from retrieval.exceptions import (
    FusionQueryError,
    FusionRepositoryError,
    FusionVersionError,
)
from retrieval.query_models import ProcessedQuery
from retrieval.query_processor import QueryPreprocessor
from retrieval.retrieval_models import RetrievalResult, RetrievalResultSet

REPO_ALPHA = "repo-alpha"
REPO_BETA = "repo-beta"


def _make_result(
    chunk_id: str,
    score: float,
    rank: int,
    repo_id: str = REPO_ALPHA,
    symbol_name: str | None = None,
    commit_sha: str | None = "sha_100",
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        score=score,
        rank=rank,
        repository_id=repo_id,
        commit_sha=commit_sha,
        file_path=f"src/{chunk_id}.py",
        language=Language.PYTHON,
        chunk_type=ChunkType.FUNCTION,
        symbol_name=symbol_name or f"symbol_{chunk_id}",
    )


@pytest.fixture
def sample_query() -> ProcessedQuery:
    preprocessor = QueryPreprocessor()
    query = preprocessor.process("How does payment processing work?")
    return query


# ──────────────────────────────────────────────────────────────────────────────
# 1. Exact RRF Calculation & Deduplication
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_exact_rrf_scoring(sample_query: ProcessedQuery) -> None:
    """TC-1: Verify exact Reciprocal Rank Fusion (RRF) score calculation with k=60.

    Inputs:
        BM25:   A (rank 1), B (rank 2), C (rank 3), E (rank 4)
        Vector: B (rank 1), C (rank 2), D (rank 3), E (rank 4)
        Graph:  C (rank 1), D (rank 2), E (rank 3), F (rank 4)

    RRF scores (k=60):
        C: 1/63 + 1/62 + 1/61 = 0.0158730 + 0.0161290 + 0.0163934 = 0.0483954
        B: 1/62 + 1/61        = 0.0161290 + 0.0163934            = 0.0325224
        D: 1/63 + 1/62        = 0.0158730 + 0.0161290            = 0.0320020
        A: 1/61               = 0.0163934
        E: 1/64 + 1/64 + 1/63 = 0.0156250 + 0.0156250 + 0.0158730 = 0.0471230
        F: 1/64               = 0.0156250
    """
    query = sample_query
    engine = CandidateFusionEngine(rrf_k=60)

    bm25_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[
            _make_result("chunk_A", score=10.0, rank=1),
            _make_result("chunk_B", score=8.0, rank=2),
            _make_result("chunk_C", score=6.0, rank=3),
            _make_result("chunk_E", score=4.0, rank=4),
        ],
    )
    vector_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[
            _make_result("chunk_B", score=0.95, rank=1),
            _make_result("chunk_C", score=0.90, rank=2),
            _make_result("chunk_D", score=0.85, rank=3),
            _make_result("chunk_E", score=0.80, rank=4),
        ],
    )
    graph_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[
            _make_result("chunk_C", score=1.0, rank=1),
            _make_result("chunk_D", score=0.9, rank=2),
            _make_result("chunk_E", score=0.8, rank=3),
            _make_result("chunk_F", score=0.7, rank=4),
        ],
    )

    fused = engine.fuse(
        lexical_results=bm25_res,
        vector_results=vector_res,
        graph_results=graph_res,
        top_k=10,
    )

    assert isinstance(fused, RetrievalResultSet)
    assert len(fused.results) == 6

    # Verify RRF order: C (#1), E (#2), B (#3), D (#4), A (#5), F (#6)
    expected_chunk_order = ["chunk_C", "chunk_E", "chunk_B", "chunk_D", "chunk_A", "chunk_F"]
    actual_chunk_order = [r.chunk_id for r in fused.results]
    assert actual_chunk_order == expected_chunk_order

    # Verify exact math for Chunk C
    chunk_c = fused.results[0]
    expected_score_c = (1.0 / 63.0) + (1.0 / 62.0) + (1.0 / 61.0)
    assert pytest.approx(chunk_c.score, abs=1e-6) == expected_score_c
    assert pytest.approx(chunk_c.fused_score, abs=1e-6) == expected_score_c
    assert chunk_c.rank == 1


@pytest.mark.unit
def test_cross_retriever_deduplication(sample_query: ProcessedQuery) -> None:
    """TC-2: Cross-retriever deduplication by chunk_id."""
    query = sample_query
    engine = CandidateFusionEngine(rrf_k=60)

    bm25_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[
            _make_result("chunk_1", score=10.0, rank=1),
            _make_result("chunk_2", score=5.0, rank=2),
        ],
    )
    vector_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[
            _make_result("chunk_2", score=0.9, rank=1),
            _make_result("chunk_3", score=0.8, rank=2),
        ],
    )
    graph_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[
            _make_result("chunk_1", score=1.0, rank=1),
            _make_result("chunk_3", score=0.5, rank=2),
        ],
    )

    fused = engine.fuse(
        lexical_results=bm25_res,
        vector_results=vector_res,
        graph_results=graph_res,
    )

    chunk_ids = [r.chunk_id for r in fused.results]
    assert len(chunk_ids) == 3
    assert set(chunk_ids) == {"chunk_1", "chunk_2", "chunk_3"}


# ──────────────────────────────────────────────────────────────────────────────
# 2. Source Evidence Preservation & Single Source Eligibility
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_source_evidence_preservation(sample_query: ProcessedQuery) -> None:
    """TC-3: Preserve source ranks, source scores, and RetrievalSource list."""
    query = sample_query
    engine = CandidateFusionEngine(rrf_k=60)

    bm25_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result("chunk_shared", score=12.5, rank=1)],
    )
    vector_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result("chunk_shared", score=0.88, rank=3)],
    )

    fused = engine.fuse(lexical_results=bm25_res, vector_results=vector_res)

    assert len(fused.results) == 1
    top = fused.results[0]
    assert top.chunk_id == "chunk_shared"
    assert RetrievalSource.BM25 in top.sources
    assert RetrievalSource.VECTOR in top.sources
    assert RetrievalSource.GRAPH not in top.sources

    assert top.bm25_rank == 1
    assert top.vector_rank == 3
    assert top.graph_rank is None

    assert top.bm25_score == 12.5
    assert top.vector_score == 0.88
    assert top.graph_score is None


@pytest.mark.unit
def test_single_source_candidates_survive(sample_query: ProcessedQuery) -> None:
    """TC-4: Candidates found by only 1 branch remain fully eligible."""
    query = sample_query
    engine = CandidateFusionEngine(rrf_k=60)

    graph_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result("chunk_graph_only", score=1.0, rank=1)],
    )

    fused = engine.fuse(graph_results=graph_res)

    assert len(fused.results) == 1
    assert fused.results[0].chunk_id == "chunk_graph_only"
    assert fused.results[0].sources == [RetrievalSource.GRAPH]


# ──────────────────────────────────────────────────────────────────────────────
# 3. Empty Branches & All-Empty Inputs
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_empty_branches_handling(sample_query: ProcessedQuery) -> None:
    """TC-5: Fusion handles empty result sets gracefully."""
    query = sample_query
    engine = CandidateFusionEngine(rrf_k=60)

    bm25_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result("chunk_1", score=10.0, rank=1)],
    )
    empty_vec = RetrievalResultSet(query=query, repository_id=REPO_ALPHA, results=[])
    empty_graph = RetrievalResultSet(query=query, repository_id=REPO_ALPHA, results=[])

    fused = engine.fuse(
        lexical_results=bm25_res, vector_results=empty_vec, graph_results=empty_graph
    )

    assert len(fused.results) == 1
    assert fused.results[0].chunk_id == "chunk_1"


@pytest.mark.unit
def test_all_empty_input_returns_empty_set(sample_query: ProcessedQuery) -> None:
    """TC-6: All empty result sets return an empty RetrievalResultSet cleanly."""
    query = sample_query
    engine = CandidateFusionEngine(rrf_k=60)

    empty_bm25 = RetrievalResultSet(query=query, repository_id=REPO_ALPHA, results=[])
    empty_vec = RetrievalResultSet(query=query, repository_id=REPO_ALPHA, results=[])

    fused = engine.fuse(lexical_results=empty_bm25, vector_results=empty_vec)

    assert len(fused.results) == 0
    assert fused.total_matches == 0
    assert fused.repository_id == REPO_ALPHA


# ──────────────────────────────────────────────────────────────────────────────
# 4. Top-K Limiting, Determinism & Tie-Breaking
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_top_k_limiting(sample_query: ProcessedQuery) -> None:
    """TC-7: top_k truncates candidate list after fusion."""
    query = sample_query
    engine = CandidateFusionEngine(rrf_k=60)

    bm25_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result(f"chunk_{i}", score=10.0 - i, rank=i) for i in range(1, 10)],
    )

    fused = engine.fuse(lexical_results=bm25_res, top_k=3)

    assert len(fused.results) == 3
    assert fused.total_matches == 9
    assert [r.rank for r in fused.results] == [1, 2, 3]


@pytest.mark.unit
def test_tie_breaking_by_chunk_id(sample_query: ProcessedQuery) -> None:
    """TC-8: Equal RRF scores are tie-broken by chunk_id ASC."""
    query = sample_query
    engine = CandidateFusionEngine(rrf_k=60)

    # Both candidates have identical rank 1 in their respective single branch
    bm25_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result("chunk_z", score=10.0, rank=1)],
    )
    vector_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result("chunk_a", score=0.9, rank=1)],
    )

    fused = engine.fuse(lexical_results=bm25_res, vector_results=vector_res)

    assert len(fused.results) == 2
    # RRF score for both is 1/(60+1) = 1/61. Tie breaker by chunk_id ASC puts chunk_a first.
    assert fused.results[0].chunk_id == "chunk_a"
    assert fused.results[1].chunk_id == "chunk_z"


@pytest.mark.unit
def test_deterministic_ordering_repeatability(sample_query: ProcessedQuery) -> None:
    """TC-9: Executing fusion 100 times produces 100% identical candidate lists."""
    query = sample_query
    engine = CandidateFusionEngine(rrf_k=60)

    bm25_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result(f"c_{i}", score=float(10 - i), rank=i) for i in range(1, 5)],
    )
    vector_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result(f"c_{i}", score=0.9 - i * 0.1, rank=i) for i in range(1, 5)],
    )

    first_run = engine.fuse(lexical_results=bm25_res, vector_results=vector_res)
    first_ids = [r.chunk_id for r in first_run.results]
    first_scores = [r.score for r in first_run.results]

    for _ in range(100):
        next_run = engine.fuse(lexical_results=bm25_res, vector_results=vector_res)
        assert [r.chunk_id for r in next_run.results] == first_ids
        assert [r.score for r in next_run.results] == first_scores


@pytest.mark.unit
def test_input_immutability(sample_query: ProcessedQuery) -> None:
    """TC-10: Fusion does not mutate input RetrievalResultSet or RetrievalResult objects."""
    query = sample_query
    engine = CandidateFusionEngine(rrf_k=60)

    item_orig = _make_result("chunk_1", score=10.0, rank=1)
    bm25_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[item_orig],
    )

    fused = engine.fuse(lexical_results=bm25_res)

    assert item_orig.score == 10.0
    assert item_orig.rank == 1
    assert item_orig.sources == []
    assert fused.results[0].score != item_orig.score  # fused score is RRF score


# ──────────────────────────────────────────────────────────────────────────────
# 5. Isolation Boundaries & Input Validation
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_repository_isolation_validation(sample_query: ProcessedQuery) -> None:
    """TC-11: Conflicting repository IDs raise FusionRepositoryError."""
    query = sample_query
    engine = CandidateFusionEngine(rrf_k=60)

    res_alpha = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result("c1", 1.0, 1, REPO_ALPHA)],
    )
    res_beta = RetrievalResultSet(
        query=query,
        repository_id=REPO_BETA,
        results=[_make_result("c2", 1.0, 1, REPO_BETA)],
    )

    with pytest.raises(FusionRepositoryError, match="Conflicting repository IDs"):
        engine.fuse(lexical_results=res_alpha, vector_results=res_beta)


@pytest.mark.unit
def test_version_commit_sha_isolation_validation(sample_query: ProcessedQuery) -> None:
    """TC-12: Conflicting commit SHAs raise FusionVersionError."""
    query = sample_query
    engine = CandidateFusionEngine(rrf_k=60)

    res_v1 = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result("c1", 1.0, 1, commit_sha="sha_100")],
    )
    res_v2 = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result("c2", 1.0, 1, commit_sha="sha_200")],
    )

    with pytest.raises(FusionVersionError, match="Conflicting commit SHAs"):
        engine.fuse(lexical_results=res_v1, vector_results=res_v2)


@pytest.mark.unit
def test_query_consistency_validation() -> None:
    """TC-13: Conflicting query texts across result sets raise FusionQueryError."""
    preprocessor = QueryPreprocessor()
    q1 = preprocessor.process("How does authentication work?")
    q2 = preprocessor.process("How are payments processed?")
    engine = CandidateFusionEngine(rrf_k=60)

    res1 = RetrievalResultSet(
        query=q1, repository_id=REPO_ALPHA, results=[_make_result("c1", 1.0, 1)]
    )
    res2 = RetrievalResultSet(
        query=q2, repository_id=REPO_ALPHA, results=[_make_result("c2", 1.0, 1)]
    )

    with pytest.raises(FusionQueryError, match="Conflicting queries"):
        engine.fuse(lexical_results=res1, vector_results=res2)


@pytest.mark.unit
def test_input_parameter_validation() -> None:
    """TC-14: Invalid parameters (rrf_k <= 0, top_k <= 0, no input sets) raise FusionQueryError."""
    with pytest.raises(FusionQueryError, match="rrf_k must be > 0"):
        CandidateFusionEngine(rrf_k=0)

    engine = CandidateFusionEngine(rrf_k=60)

    with pytest.raises(FusionQueryError, match="top_k must be > 0"):
        engine.fuse(top_k=0)

    with pytest.raises(FusionQueryError, match="At least one RetrievalResultSet must be provided"):
        engine.fuse()


# ──────────────────────────────────────────────────────────────────────────────
# 6. Serialization & Performance Scale
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_json_serialization_roundtrip(sample_query: ProcessedQuery) -> None:
    """TC-15: RetrievalResultSet Pydantic JSON serialization roundtrip."""
    query = sample_query
    engine = CandidateFusionEngine(rrf_k=60)

    bm25_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result("c1", 10.0, 1)],
    )

    fused = engine.fuse(lexical_results=bm25_res)
    json_str = fused.model_dump_json()

    deserialized = RetrievalResultSet.model_validate_json(json_str)
    assert deserialized.repository_id == fused.repository_id
    assert len(deserialized.results) == len(fused.results)
    assert deserialized.results[0].chunk_id == "c1"
    assert deserialized.results[0].sources == [RetrievalSource.BM25]


@pytest.mark.performance
def test_performance_scale(sample_query: ProcessedQuery) -> None:
    """TC-16: Fusing 1,000+ candidates per branch performs in under 100ms."""
    query = sample_query
    engine = CandidateFusionEngine(rrf_k=60)

    bm25_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result(f"chunk_{i}", 1000.0 - i, i) for i in range(1, 1001)],
    )
    vector_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result(f"chunk_{i}", 1.0 - (i / 2000.0), i) for i in range(500, 1501)],
    )
    graph_res = RetrievalResultSet(
        query=query,
        repository_id=REPO_ALPHA,
        results=[_make_result(f"chunk_{i}", 1.0, i) for i in range(800, 1801)],
    )

    fused = engine.fuse(
        lexical_results=bm25_res,
        vector_results=vector_res,
        graph_results=graph_res,
        top_k=50,
    )

    assert len(fused.results) == 50
    assert fused.total_matches == 1800
    assert fused.fusion_latency_ms < 200.0  # Sub-second efficient
