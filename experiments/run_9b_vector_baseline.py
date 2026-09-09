import json
import time
from collections import defaultdict
from pathlib import Path

from benchmarks.loader import BenchmarkLoader
from code_analyzer.ir import SourceLocation
from code_analyzer.parsers.models import Language
from evaluation.metrics import (
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_reciprocal_rank,
)
from retrieval.embedding_models import EmbeddingInput
from retrieval.enums import ChunkType
from retrieval.models import CodeChunk
from retrieval.providers import LocalSentenceTransformerProvider
from retrieval.query_processor import QueryPreprocessor
from retrieval.vector_index import VectorIndex
from retrieval.vector_retriever import VectorRetriever


def main() -> None:
    dataset = BenchmarkLoader.load()
    if dataset.metadata.dataset_version != "9A.1":
        raise ValueError(f"Expected benchmark version 9A.1, got {dataset.metadata.dataset_version}")
    print(
        f"Loaded benchmark 9A.1: {len(dataset.queries)} queries, {len(dataset.repositories)} repos"
    )

    # Build Vector Index
    print("Building Vector Index...")
    provider = LocalSentenceTransformerProvider(model_name="all-MiniLM-L6-v2", dimension=384)
    preprocessor = QueryPreprocessor()
    vector_index = VectorIndex()

    # Load chunks into VectorIndex
    for repo in dataset.repositories:
        inputs = []
        chunks_map = {}
        for c in repo.chunks:
            # We map Benchmark Chunk -> CodeChunk
            code_text = c.content
            ctype_str = c.chunk_type.upper()
            if "FILE" in ctype_str:
                ct = ChunkType.FILE_CONTEXT
            elif "CLASS" in ctype_str:
                ct = ChunkType.CLASS_CONTEXT
            elif "FUNC" in ctype_str:
                ct = ChunkType.FUNCTION
            elif "METH" in ctype_str:
                ct = ChunkType.METHOD
            else:
                ct = ChunkType.SUB_CHUNK

            chunks_map[c.chunk_id] = CodeChunk(
                id=c.chunk_id,
                repository_id=c.repository_id,
                file_path=c.file_path,
                language=Language(c.language.lower()),
                chunk_type=ct,
                name=c.symbol_name,
                qualified_name=c.qualified_name,
                source_location=SourceLocation(
                    start_line=c.start_line or 1,
                    start_column=0,
                    end_line=c.end_line or 10,
                    end_column=0,
                ),
                content=code_text,
                commit_sha="v1.0.0",
            )
            inputs.append(
                EmbeddingInput(
                    chunk_id=c.chunk_id,
                    text=code_text,
                    model_name=provider.model_name,
                    embedding_version=provider.embedding_version,
                    metadata={"repository_id": repo.repository_id},
                )
            )

        # Embed all chunks for this repo
        if inputs:
            embed_results = provider.embed(inputs)
            for er in embed_results:
                vector_index.add(er, chunk=chunks_map[er.chunk_id])

    retriever = VectorRetriever(index=vector_index, provider=provider, preprocessor=preprocessor)

    # Metrics settings
    k_vals_recall = [1, 3, 5, 10]
    k_vals_prec = [5, 10]

    raw_results = []

    # Trackers for aggregates
    total_mrr = 0.0
    total_recall: dict[int, float] = {k: 0.0 for k in k_vals_recall}
    total_prec: dict[int, float] = {k: 0.0 for k in k_vals_prec}
    
    def get_default_stats() -> dict[str, float]:
        d: dict[str, float] = {"count": 0.0, "MRR": 0.0}
        for k in k_vals_recall:
            d[f"Recall@{k}"] = 0.0
        for k in k_vals_prec:
            d[f"Precision@{k}"] = 0.0
        return d

    cat_stats: dict[str, dict[str, float]] = defaultdict(get_default_stats)
    diff_stats: dict[str, dict[str, float]] = defaultdict(get_default_stats)
    lang_stats: dict[str, dict[str, float]] = defaultdict(get_default_stats)
    repo_stats: dict[str, dict[str, float]] = defaultdict(get_default_stats)

    print("Running baseline vector retrieval...")
    for q in dataset.queries:
        # Ground truth
        relevant_set = {j.chunk_id for j in q.relevance_judgments if j.grade.value > 0}
        if not relevant_set:
            continue

        start_t = time.perf_counter()

        # Isolated query vector execution
        res_set = retriever.retrieve(query=q.query_text, repository_id=q.repository_id, top_k=10)
        latency = (time.perf_counter() - start_t) * 1000

        retrieved_ids = [r.chunk_id for r in res_set.results]

        # Calculate isolated metrics
        mrr = calculate_reciprocal_rank(retrieved_ids, relevant_set)
        recalls = {k: calculate_recall_at_k(retrieved_ids, relevant_set, k) for k in k_vals_recall}
        precs = {k: calculate_precision_at_k(retrieved_ids, relevant_set, k) for k in k_vals_prec}

        total_mrr += mrr
        for k in k_vals_recall:
            total_recall[k] += recalls[k]
        for k in k_vals_prec:
            total_prec[k] += precs[k]

        cat = q.category.value
        diff = q.difficulty.value
        lang = q.language
        rep = q.repository_id

        cat_stats[cat]["count"] += 1
        diff_stats[diff]["count"] += 1
        lang_stats[lang]["count"] += 1
        repo_stats[rep]["count"] += 1

        for grp in [cat_stats[cat], diff_stats[diff], lang_stats[lang], repo_stats[rep]]:
            grp["MRR"] += mrr
            for k in k_vals_recall:
                grp[f"Recall@{k}"] += recalls[k]
            for k in k_vals_prec:
                grp[f"Precision@{k}"] += precs[k]

        raw_results.append(
            {
                "query_id": q.query_id,
                "repository_id": q.repository_id,
                "retrieval_system": "vector-only",
                "rank": 1 if retrieved_ids else None,
                "latency_ms": latency,
                "retrieved_chunk_ids": retrieved_ids,
                "scores": [r.score for r in res_set.results],
                "relevant_chunk_ids": list(relevant_set),
                "MRR": mrr,
                "Recall@1": recalls[1],
                "Recall@3": recalls[3],
                "Recall@5": recalls[5],
                "Recall@10": recalls[10],
                "Precision@5": precs[5],
                "Precision@10": precs[10],
            }
        )

    num_q = len(raw_results)
    if num_q == 0:
        print("No valid queries to evaluate.")
        return

    overall_metrics = {
        "MRR": total_mrr / num_q,
        "Recall@1": total_recall[1] / num_q,
        "Recall@3": total_recall[3] / num_q,
        "Recall@5": total_recall[5] / num_q,
        "Recall@10": total_recall[10] / num_q,
        "Precision@5": total_prec[5] / num_q,
        "Precision@10": total_prec[10] / num_q,
    }

    def finalize_group(stats: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
        res: dict[str, dict[str, float]] = {}
        for k, v in stats.items():
            count = v["count"]
            res[k] = {ak: (av / count) for ak, av in v.items() if ak != "count"}
        return res

    summary = {
        "experiment_id": "9B-vector-baseline-semantic",
        "experiment_name": "Task 9B Vector Baseline",
        "benchmark_version": "9A.1",
        "protocol_version": "Phase 9 Standard",
        "retrieval_system": "VectorOnly",
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_dimension": 384,
        "similarity_metric": "Cosine",
        "top_k_values": [1, 3, 5, 10],
        "repository_scope": "Isolated per repository",
        "software_version": "0.1.0",
        "overall": overall_metrics,
        "category_breakdown": finalize_group(cat_stats),
        "difficulty_breakdown": finalize_group(diff_stats),
        "language_breakdown": finalize_group(lang_stats),
        "repository_breakdown": finalize_group(repo_stats),
    }

    print("\n--- BASELINE METRICS ---")
    print(json.dumps(overall_metrics, indent=2))

    Path("results/phase9/9b/raw").mkdir(parents=True, exist_ok=True)
    Path("results/phase9/9b/summary").mkdir(parents=True, exist_ok=True)

    with open("results/phase9/9b/raw/results.json", "w", encoding="utf-8") as f:
        json.dump(raw_results, f, indent=2)

    with open("results/phase9/9b/summary/metrics.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\nExperiment completed. Results saved to results/phase9/9b/")


if __name__ == "__main__":
    main()
