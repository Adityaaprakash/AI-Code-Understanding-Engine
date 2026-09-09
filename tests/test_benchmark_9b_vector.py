import json
from pathlib import Path
from unittest.mock import patch

from benchmarks.loader import BenchmarkLoader
from experiments.run_9b_vector_baseline import main


def test_benchmark_is_frozen_9a1():
    dataset = BenchmarkLoader.load()
    assert dataset.metadata.dataset_version == "9A.1"
    assert len(dataset.repositories) == 3
    assert len(dataset.queries) == 48


def test_9b_baseline_output_schema():
    raw_path = Path("results/phase9/9b/raw/results.json")
    summary_path = Path("results/phase9/9b/summary/metrics.json")

    assert raw_path.exists(), "Raw results missing"
    assert summary_path.exists(), "Summary metrics missing"

    with summary_path.open("r", encoding="utf-8") as f:
        summary = json.load(f)

    assert summary["experiment_id"] == "9B-vector-baseline-semantic"
    assert summary["benchmark_version"] == "9A.1"
    assert summary["retrieval_system"] == "VectorOnly"
    assert summary["embedding_model"] == "all-MiniLM-L6-v2"
    assert "overall" in summary
    assert "Recall@1" in summary["overall"]
    assert "Precision@5" in summary["overall"]
    assert "MRR" in summary["overall"]


def test_9b_repository_isolation():
    raw_path = Path("results/phase9/9b/raw/results.json")
    with raw_path.open("r", encoding="utf-8") as f:
        raw_results = json.load(f)

    assert len(raw_results) == 48

    for r in raw_results:
        repo_id = r["repository_id"]
        # Basic naming heuristic for chunks:
        # python chunks contain "py"
        # java chunks contain "java"
        # ts chunks contain "ts"
        for chunk_id in r["retrieved_chunk_ids"]:
            if "py-ecommerce" in repo_id:
                assert (
                    "-py-" in chunk_id
                    or "pay" in chunk_id
                    or "auth" in chunk_id
                    or "order" in chunk_id
                ), f"{chunk_id} crossed into python repo"
            elif "java-banking" in repo_id:
                assert (
                    "-jv-" in chunk_id
                    or "-java-" in chunk_id
                    or "account" in chunk_id
                    or "transaction" in chunk_id
                    or "user" in chunk_id
                )
            elif "ts-gateway" in repo_id:
                assert (
                    "-ts-" in chunk_id
                    or "gateway" in chunk_id
                    or "middleware" in chunk_id
                    or "routes" in chunk_id
                )


@patch("retrieval.lexical_retriever.LexicalRetriever")
@patch("retrieval.graph_retriever.GraphRetriever")
@patch("retrieval.candidate_fusion.CandidateFusionEngine")
@patch("retrieval.reranker.DeterministicReranker")
def test_no_bm25_graph_or_reranker_invocations(mock_rerank, mock_fusion, mock_graph, mock_bm25):
    # Run the main script with these patched out to ensure it doesn't call them!
    main()

    mock_bm25.assert_not_called()
    mock_graph.assert_not_called()
    mock_fusion.assert_not_called()
    mock_rerank.assert_not_called()
