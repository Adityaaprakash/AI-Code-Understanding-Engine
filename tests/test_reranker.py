"""Unit test suite for TASK-5F Candidate Reranker (DeterministicReranker)."""

import pytest

from code_analyzer.parsers.models import Language
from retrieval.enums import ChunkType, RetrievalSource
from retrieval.exceptions import RerankerConfigurationError, RerankerInputError
from retrieval.query_models import ProcessedQuery
from retrieval.query_processor import QueryPreprocessor
from retrieval.reranker import DeterministicReranker
from retrieval.retrieval_models import RetrievalResult, RetrievalResultSet

REPO_ID = "repo-rerank-test"


def _make_candidate(
    chunk_id: str,
    score: float = 0.5,
    rank: int = 1,
    symbol_name: str | None = None,
    qualified_name: str | None = None,
    file_path: str = "src/main.py",
    sources: list[RetrievalSource] | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        score=score,
        rank=rank,
        repository_id=REPO_ID,
        file_path=file_path,
        language=Language.PYTHON,
        chunk_type=ChunkType.FUNCTION,
        symbol_name=symbol_name,
        qualified_name=qualified_name,
        sources=sources or [RetrievalSource.BM25],
        bm25_rank=rank,
        bm25_score=score,
        fused_score=score,
        metadata={"code_content": f"def {symbol_name or chunk_id}(): pass"},
    )


@pytest.fixture
def sample_query() -> ProcessedQuery:
    qp = QueryPreprocessor()
    return qp.process("process_payment")


@pytest.fixture
def sample_fused_set(sample_query: ProcessedQuery) -> RetrievalResultSet:
    c1 = _make_candidate(
        chunk_id="chunk-c1",
        score=0.03,
        rank=1,
        symbol_name="process_payment",
        qualified_name="payment.service.process_payment",
        sources=[RetrievalSource.BM25, RetrievalSource.VECTOR, RetrievalSource.GRAPH],
    )
    c2 = _make_candidate(
        chunk_id="chunk-c2",
        score=0.02,
        rank=2,
        symbol_name="other_function",
        qualified_name="payment.service.other_function",
        sources=[RetrievalSource.BM25],
    )
    c3 = _make_candidate(
        chunk_id="chunk-c3",
        score=0.01,
        rank=3,
        symbol_name="unrelated_fn",
        qualified_name="utils.unrelated_fn",
        sources=[RetrievalSource.VECTOR],
    )
    return RetrievalResultSet(
        query=sample_query,
        repository_id=REPO_ID,
        results=[c1, c2, c3],
        total_matches=3,
        preprocessing_latency_ms=1.0,
        retrieval_latency_ms=5.0,
        fusion_latency_ms=2.0,
        total_latency_ms=8.0,
    )


@pytest.mark.unit
def test_basic_reranking(sample_query: ProcessedQuery, sample_fused_set: RetrievalResultSet) -> None:
    """TC-1: Basic reranking execution flow."""
    reranker = DeterministicReranker(rerank_top_k=50)
    res = reranker.rerank(query=sample_query, results=sample_fused_set, top_k=10)

    assert isinstance(res, RetrievalResultSet)
    assert len(res.results) == 3
    assert res.results[0].chunk_id == "chunk-c1"
    assert res.results[0].rerank_score is not None
    assert res.results[0].rank == 1


@pytest.mark.unit
def test_exact_symbol_match(sample_query: ProcessedQuery, sample_fused_set: RetrievalResultSet) -> None:
    """TC-2: Exact symbol match receives highest exact symbol feature weight."""
    reranker = DeterministicReranker()
    res = reranker.rerank(query=sample_query, results=sample_fused_set, top_k=10)

    top_item = res.results[0]
    assert top_item.symbol_name == "process_payment"
    assert top_item.rerank_score is not None and top_item.rerank_score > 0.5


@pytest.mark.unit
def test_qualified_symbol_match(sample_query: ProcessedQuery) -> None:
    """TC-3: Qualified symbol match scores higher than generic token overlap."""
    q = sample_query
    c1 = _make_candidate(
        chunk_id="chunk-qual",
        symbol_name="handler",
        qualified_name="services.payment.process_payment.handler",
    )
    c2 = _make_candidate(
        chunk_id="chunk-generic",
        symbol_name="unrelated",
        qualified_name="utils.common",
    )
    fused = RetrievalResultSet(
        query=q, repository_id=REPO_ID, results=[c2, c1], total_matches=2
    )

    reranker = DeterministicReranker()
    res = reranker.rerank(query=q, results=fused, top_k=10)

    assert res.results[0].chunk_id == "chunk-qual"


@pytest.mark.unit
def test_identifier_overlap(sample_query: ProcessedQuery) -> None:
    """TC-4: Token overlap scores candidates based on token matches."""
    q = sample_query
    c1 = _make_candidate(chunk_id="chunk-token-match", symbol_name="process_payment")
    c2 = _make_candidate(chunk_id="chunk-no-match", symbol_name="unrelated")
    fused = RetrievalResultSet(
        query=q, repository_id=REPO_ID, results=[c2, c1], total_matches=2
    )

    reranker = DeterministicReranker()
    res = reranker.rerank(query=q, results=fused, top_k=10)

    assert res.results[0].chunk_id == "chunk-token-match"


@pytest.mark.unit
def test_source_agreement(sample_query: ProcessedQuery) -> None:
    """TC-5: Source agreement boosts candidates found by multiple branches."""
    q = sample_query
    c1 = _make_candidate(
        chunk_id="chunk-multi-source",
        symbol_name="fn_a",
        sources=[RetrievalSource.BM25, RetrievalSource.VECTOR, RetrievalSource.GRAPH],
    )
    c2 = _make_candidate(
        chunk_id="chunk-single-source",
        symbol_name="fn_b",
        sources=[RetrievalSource.BM25],
    )
    fused = RetrievalResultSet(
        query=q, repository_id=REPO_ID, results=[c2, c1], total_matches=2
    )

    reranker = DeterministicReranker()
    res = reranker.rerank(query=q, results=fused, top_k=10)

    assert res.results[0].chunk_id == "chunk-multi-source"


@pytest.mark.unit
def test_rrf_evidence_preservation(sample_query: ProcessedQuery, sample_fused_set: RetrievalResultSet) -> None:
    """TC-6: All original RRF scores and source evidence are preserved intact."""
    reranker = DeterministicReranker()
    res = reranker.rerank(query=sample_query, results=sample_fused_set, top_k=10)

    for item in res.results:
        assert item.fused_score is not None
        assert item.bm25_rank is not None
        assert item.sources is not None


@pytest.mark.unit
def test_top_k_limiting(sample_query: ProcessedQuery, sample_fused_set: RetrievalResultSet) -> None:
    """TC-7: top_k parameter truncates candidate output list."""
    reranker = DeterministicReranker()
    res = reranker.rerank(query=sample_query, results=sample_fused_set, top_k=2)

    assert len(res.results) == 2


@pytest.mark.unit
def test_empty_candidates(sample_query: ProcessedQuery) -> None:
    """TC-8: Empty input results return empty RetrievalResultSet cleanly."""
    fused = RetrievalResultSet(
        query=sample_query, repository_id=REPO_ID, results=[], total_matches=0
    )
    reranker = DeterministicReranker()
    res = reranker.rerank(query=sample_query, results=fused, top_k=10)

    assert len(res.results) == 0
    assert res.total_matches == 0


@pytest.mark.unit
def test_single_candidate(sample_query: ProcessedQuery) -> None:
    """TC-9: Single candidate returns with rank=1 and rerank_score."""
    c1 = _make_candidate(chunk_id="chunk-single", symbol_name="process_payment")
    fused = RetrievalResultSet(
        query=sample_query, repository_id=REPO_ID, results=[c1], total_matches=1
    )
    reranker = DeterministicReranker()
    res = reranker.rerank(query=sample_query, results=fused, top_k=10)

    assert len(res.results) == 1
    assert res.results[0].rank == 1
    assert res.results[0].rerank_score is not None


@pytest.mark.unit
def test_deterministic_ordering(sample_query: ProcessedQuery, sample_fused_set: RetrievalResultSet) -> None:
    """TC-10: Reranker execution produces deterministic candidate scores and ordering."""
    reranker = DeterministicReranker()
    res1 = reranker.rerank(query=sample_query, results=sample_fused_set, top_k=10)
    res2 = reranker.rerank(query=sample_query, results=sample_fused_set, top_k=10)

    ids1 = [r.chunk_id for r in res1.results]
    ids2 = [r.chunk_id for r in res2.results]
    assert ids1 == ids2


@pytest.mark.unit
def test_100_run_determinism(sample_query: ProcessedQuery, sample_fused_set: RetrievalResultSet) -> None:
    """TC-11: Executing reranking 100 times produces 100% identical outputs."""
    reranker = DeterministicReranker()
    first_run = [r.chunk_id for r in reranker.rerank(query=sample_query, results=sample_fused_set, top_k=10).results]

    for _ in range(100):
        current_run = [r.chunk_id for r in reranker.rerank(query=sample_query, results=sample_fused_set, top_k=10).results]
        assert current_run == first_run


@pytest.mark.unit
def test_tie_breaking(sample_query: ProcessedQuery) -> None:
    """TC-12: Candidates with identical rerank scores are tie-broken by chunk_id ASC."""
    q = sample_query
    c_b = _make_candidate(chunk_id="chunk-B", symbol_name="unrelated_a")
    c_a = _make_candidate(chunk_id="chunk-A", symbol_name="unrelated_b")
    fused = RetrievalResultSet(
        query=q, repository_id=REPO_ID, results=[c_b, c_a], total_matches=2
    )

    reranker = DeterministicReranker(weights={"exact_symbol": 0.0, "qualified_symbol": 0.0, "token_overlap": 0.0, "source_agreement": 0.0, "rrf_prior": 1.0})
    res = reranker.rerank(query=q, results=fused, top_k=10)

    assert res.results[0].chunk_id == "chunk-A"
    assert res.results[1].chunk_id == "chunk-B"


@pytest.mark.unit
def test_input_immutability(sample_query: ProcessedQuery, sample_fused_set: RetrievalResultSet) -> None:
    """TC-13: Input RetrievalResultSet and RetrievalResult objects remain unmutated."""
    original_score = sample_fused_set.results[0].score
    reranker = DeterministicReranker()
    _ = reranker.rerank(query=sample_query, results=sample_fused_set, top_k=10)

    assert sample_fused_set.results[0].score == original_score


@pytest.mark.unit
def test_query_mismatch_raises_error(sample_query: ProcessedQuery, sample_fused_set: RetrievalResultSet) -> None:
    """TC-14: Query mismatch between provided query and result set query raises RerankerInputError."""
    qp = QueryPreprocessor()
    different_query = qp.process("completely_different_query")
    reranker = DeterministicReranker()

    with pytest.raises(RerankerInputError, match="Query mismatch"):
        reranker.rerank(query=different_query, results=sample_fused_set, top_k=10)


@pytest.mark.unit
def test_latency_tracking(sample_query: ProcessedQuery, sample_fused_set: RetrievalResultSet) -> None:
    """TC-15: Reranking measures reranking_latency_ms and updates total_latency_ms."""
    reranker = DeterministicReranker()
    res = reranker.rerank(query=sample_query, results=sample_fused_set, top_k=10)

    assert res.reranking_latency_ms >= 0.0
    assert res.total_latency_ms >= res.fusion_latency_ms + res.reranking_latency_ms


@pytest.mark.unit
def test_serialization_roundtrip(sample_query: ProcessedQuery, sample_fused_set: RetrievalResultSet) -> None:
    """TC-16: RetrievalResultSet containing reranked results serializes to JSON and back."""
    reranker = DeterministicReranker()
    res = reranker.rerank(query=sample_query, results=sample_fused_set, top_k=10)

    json_str = res.model_dump_json()
    roundtrip = RetrievalResultSet.model_validate_json(json_str)

    assert roundtrip.repository_id == res.repository_id
    assert len(roundtrip.results) == len(res.results)
    assert roundtrip.results[0].rerank_score == res.results[0].rerank_score


@pytest.mark.performance
def test_performance_scale(sample_query: ProcessedQuery) -> None:
    """TC-17: Reranking a 500-candidate pool completes in under 100ms."""
    candidates = [
        _make_candidate(
            chunk_id=f"chunk-{i:04d}",
            score=1.0 / (60 + i),
            rank=i,
            symbol_name=f"func_{i}",
        )
        for i in range(1, 501)
    ]
    fused = RetrievalResultSet(
        query=sample_query,
        repository_id=REPO_ID,
        results=candidates,
        total_matches=500,
    )

    reranker = DeterministicReranker(rerank_top_k=500)
    res = reranker.rerank(query=sample_query, results=fused, top_k=10)

    assert len(res.results) == 10
    assert res.reranking_latency_ms < 100.0


@pytest.mark.unit
def test_invalid_parameters(sample_query: ProcessedQuery, sample_fused_set: RetrievalResultSet) -> None:
    """TC-18: Invalid top_k <= 0 or rerank_top_k <= 0 raise appropriate errors."""
    with pytest.raises(RerankerConfigurationError):
        DeterministicReranker(rerank_top_k=0)

    reranker = DeterministicReranker()
    with pytest.raises(RerankerInputError):
        reranker.rerank(query=sample_query, results=sample_fused_set, top_k=0)
