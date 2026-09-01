"""End-to-end Phase 5 Integration Test Suite (5A -> 5B/5C/5D -> 5E -> 5F -> 5G)."""

import pytest

from evaluation.benchmark import RetrievalBenchmarkRunner
from retrieval.candidate_fusion import CandidateFusionEngine
from retrieval.lexical_retriever import LexicalRetriever
from retrieval.query_processor import QueryPreprocessor
from retrieval.reranker import DeterministicReranker
from retrieval.retrieval_models import RetrievalResultSet
from retrieval.vector_index import RepositoryVectorIndex
from retrieval.vector_retriever import VectorRetriever

REPO_ID = "phase5-integration-repo"


@pytest.mark.integration
def test_end_to_end_phase5_pipeline() -> None:
    """Test full Phase 5 hybrid retrieval engine pipeline from query to reranked results."""
    # 1. Query Preprocessing (5A)
    qp = QueryPreprocessor()
    query_text = "Where is database connection configured?"
    processed_q = qp.process(query_text)

    # 2. Build mock dataset & indexes (5B, 5C)
    runner = RetrievalBenchmarkRunner(repository_id=REPO_ID, top_k=5)

    # 3. Lexical Retrieval (5B)
    bm25_res = runner.lexical_retriever.retrieve(query=processed_q, repository_id=REPO_ID, top_k=10)
    assert isinstance(bm25_res, RetrievalResultSet)

    # 4. Vector Retrieval (5C)
    vector_res = runner.vector_retriever.retrieve(query=processed_q, repository_id=REPO_ID, top_k=10)
    assert isinstance(vector_res, RetrievalResultSet)

    # 5. Candidate Fusion (5E)
    fusion_engine = CandidateFusionEngine(rrf_k=60)
    fused_res = fusion_engine.fuse(
        lexical_results=bm25_res,
        vector_results=vector_res,
        top_k=10,
    )
    assert isinstance(fused_res, RetrievalResultSet)
    assert len(fused_res.results) > 0
    assert fused_res.fusion_latency_ms >= 0.0

    # 6. Candidate Reranking (5F)
    reranker = DeterministicReranker(rerank_top_k=50)
    reranked_res = reranker.rerank(query=processed_q, results=fused_res, top_k=5)
    assert isinstance(reranked_res, RetrievalResultSet)
    assert len(reranked_res.results) <= 5
    assert reranked_res.results[0].rerank_score is not None
    assert reranked_res.results[0].rank == 1

    # 7. Preservation of Canonical Identities & Provenance
    top_candidate = reranked_res.results[0]
    assert top_candidate.chunk_id.startswith("chunk-")
    assert top_candidate.repository_id == REPO_ID
    assert top_candidate.sources is not None
    assert top_candidate.fused_score is not None

    # 8. Benchmark Evaluation Execution (5G)
    report = runner.run_benchmark()
    assert report.repository_id == REPO_ID
    assert len(report.systems) == 6
