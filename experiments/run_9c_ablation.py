import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from benchmarks.loader import BenchmarkLoader
from code_analyzer.ir import SourceLocation
from code_analyzer.parsers.models import Language
from evaluation.metrics import (
    calculate_hit_rate_at_k,
    calculate_ndcg_at_k,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_reciprocal_rank,
)
from graph.edges import GraphEdge, generate_edge_id
from graph.enums import EdgeKind, NodeKind, ResolutionStatus
from graph.nodes import GraphNode
from graph.store import InMemoryGraphStore
from retrieval.candidate_fusion import CandidateFusionEngine
from retrieval.embedding_models import EmbeddingInput
from retrieval.enums import ChunkType
from retrieval.graph_retriever import GraphRetriever
from retrieval.lexical_index import BM25LexicalIndex
from retrieval.lexical_retriever import LexicalRetriever
from retrieval.models import CodeChunk
from retrieval.providers import LocalSentenceTransformerProvider
from retrieval.query_processor import QueryPreprocessor
from retrieval.reranker import DeterministicReranker
from retrieval.vector_index import VectorIndex
from retrieval.vector_retriever import VectorRetriever


def main() -> None:
    dataset = BenchmarkLoader.load()
    if dataset.metadata.dataset_version != "9A.1":
        raise ValueError(f"Expected benchmark version 9A.1, got {dataset.metadata.dataset_version}")
    print(f"Loaded benchmark 9A.1: {len(dataset.queries)} queries, {len(dataset.repositories)} repos")

    # Shared architecture
    preprocessor = QueryPreprocessor()
    fusion_engine = CandidateFusionEngine(rrf_k=60)
    reranker = DeterministicReranker(rerank_top_k=50)
    provider = LocalSentenceTransformerProvider(model_name="all-MiniLM-L6-v2", dimension=384)

    vector_index = VectorIndex()
    lexical_index = BM25LexicalIndex()
    graph_store = InMemoryGraphStore()

    global_chunk_map = {}

    print("Building Indexes & Graph Store...")
    for repo in dataset.repositories:
        inputs = []
        for c_fix in repo.chunks:
            code_text = c_fix.content
            ctype_str = c_fix.chunk_type.upper()
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

            chunk_obj = CodeChunk(
                id=c_fix.chunk_id, repository_id=c_fix.repository_id, file_path=c_fix.file_path,
                language=Language(c_fix.language.lower()), chunk_type=ct, name=c_fix.symbol_name,
                qualified_name=c_fix.qualified_name,
                source_location=SourceLocation(start_line=c_fix.start_line or 1, start_column=0, end_line=c_fix.end_line or 10, end_column=0),
                content=code_text, commit_sha="v1.0.0"
            )
            global_chunk_map[c_fix.chunk_id] = chunk_obj
            if c_fix.symbol_id:
                global_chunk_map[c_fix.symbol_id] = chunk_obj
            lexical_index.add(chunk_obj)

            inputs.append(EmbeddingInput(
                chunk_id=c_fix.chunk_id, text=code_text, model_name=provider.model_name,
                embedding_version=provider.embedding_version, metadata={"repository_id": repo.repository_id}
            ))

        if inputs:
            embed_results = provider.embed(inputs)
            for er in embed_results:
                vector_index.add(er, chunk=global_chunk_map[er.chunk_id])

        from graph.models import CodeGraph
        nodes_dict = {}
        edges_dict = {}
        # Graph Adapter: Map symbols to nodes
        for sym in repo.symbols:
            try:
                n_kind = NodeKind(sym.kind.lower())
            except ValueError:
                n_kind = NodeKind.SYMBOL

            gn = GraphNode(
                id=sym.symbol_id,
                kind=n_kind,
                name=sym.name,
                qualified_name=sym.qualified_name,
                language=sym.language,
                file_id=sym.file_path,
                location=SourceLocation(start_line=sym.start_line, end_line=sym.end_line, start_column=0, end_column=0),
                attributes={"path": sym.file_path, "repository_id": repo.repository_id}
            )
            nodes_dict[gn.id] = gn

        # Graph Adapter: Map edges
        for edge_fix in repo.graph_edges:
            e_kind = EdgeKind(edge_fix.relationship.value.lower())
            edge_id = generate_edge_id(edge_fix.source_symbol_id, edge_fix.target_symbol_id, e_kind)
            ge = GraphEdge(
                id=edge_id,
                source_id=edge_fix.source_symbol_id,
                target_id=edge_fix.target_symbol_id,
                kind=e_kind,
                resolution_status=ResolutionStatus.RESOLVED,
                attributes={"repository_id": repo.repository_id}
            )
            edges_dict[ge.id] = ge

        cg = CodeGraph(repository_id=repo.repository_id, nodes=nodes_dict, edges=edges_dict)
        cg._ensure_indexes()
        graph_store._saved_graphs[repo.repository_id] = cg

    vector_retriever = VectorRetriever(index=vector_index, provider=provider, preprocessor=preprocessor)
    lexical_retriever = LexicalRetriever(index=lexical_index, preprocessor=preprocessor)
    graph_retriever = GraphRetriever(graph_store=graph_store, query_preprocessor=preprocessor, chunk_lookup=global_chunk_map)

    k_vals = [1, 3, 5, 10]
    out_raw = []

    sys_metrics: dict[str, Any] = {"A": defaultdict(float), "B": defaultdict(float), "C": defaultdict(float), "D": defaultdict(float)}

    source_stats = {
        "BM25_ONLY": 0, "VECTOR_ONLY": 0, "GRAPH_ONLY": 0,
        "BM25_VECTOR": 0, "BM25_GRAPH": 0, "VECTOR_GRAPH": 0, "ALL_THREE": 0
    }

    cat_sys_stats: dict[str, Any] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    graph_queries_sys_stats: dict[str, Any] = defaultdict(lambda: defaultdict(float))
    lang_sys_stats: dict[str, Any] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

    representative_traces = []

    print("Running queries...")
    for q in dataset.queries:
        relevant_set = {j.chunk_id for j in q.relevance_judgments if j.grade.value > 0}
        rel_grades = {j.chunk_id: j.grade.value for j in q.relevance_judgments if j.grade.value > 0}
        if not relevant_set:
            continue

        t0 = time.perf_counter_ns()

        bm25_res = lexical_retriever.retrieve(query=q.query_text, repository_id=q.repository_id, top_k=20)
        t1 = time.perf_counter_ns()
        vector_res = vector_retriever.retrieve(query=q.query_text, repository_id=q.repository_id, top_k=20)
        t2 = time.perf_counter_ns()
        graph_res = graph_retriever.retrieve(query=q.query_text, repository_id=q.repository_id, top_k=20)
        t3 = time.perf_counter_ns()

        # Provenance explicitly required
        bm25_f = {r.chunk_id for r in bm25_res.results if r.chunk_id in relevant_set}
        vector_f = {r.chunk_id for r in vector_res.results if r.chunk_id in relevant_set}
        graph_f = {r.chunk_id for r in graph_res.results if r.chunk_id in relevant_set}

        for cid in relevant_set:
            in_b, in_v, in_g = (cid in bm25_f), (cid in vector_f), (cid in graph_f)
            if in_b and not in_v and not in_g:
                source_stats["BM25_ONLY"] += 1
            elif in_v and not in_b and not in_g:
                source_stats["VECTOR_ONLY"] += 1
            elif in_g and not in_b and not in_v:
                source_stats["GRAPH_ONLY"] += 1
            elif in_b and in_v and not in_g:
                source_stats["BM25_VECTOR"] += 1
            elif in_b and in_g and not in_v:
                source_stats["BM25_GRAPH"] += 1
            elif in_v and in_g and not in_b:
                source_stats["VECTOR_GRAPH"] += 1
            elif in_b and in_v and in_g:
                source_stats["ALL_THREE"] += 1

        is_graph_grounded = bool(q.graph_ground_truth) or bool(q.multi_hop_paths)

        if q.query_id == "q-py-004":
            representative_traces.append({
                "query_id": q.query_id,
                "text": q.query_text,
                "graph_results": [{"chunk_id": r.chunk_id, "symbol": r.symbol_name, "score": r.score} for r in graph_res.results]
            })

        sys_a_time = (t2 - t1) / 1e6

        sys_b_res = fusion_engine.fuse(lexical_results=bm25_res, vector_results=vector_res, top_k=10)
        sys_b_time = (time.perf_counter_ns() - t2) / 1e6 + sys_a_time + ((t1 - t0) / 1e6)

        start_c = time.perf_counter_ns()
        sys_c_res = fusion_engine.fuse(lexical_results=bm25_res, vector_results=vector_res, graph_results=graph_res, top_k=10)
        sys_c_time = (time.perf_counter_ns() - start_c) / 1e6 + sys_b_time + ((t3 - t2) / 1e6)

        start_r = time.perf_counter_ns()
        sys_full_fusion = fusion_engine.fuse(lexical_results=bm25_res, vector_results=vector_res, graph_results=graph_res, top_k=50)
        sys_d_res = reranker.rerank(query=sys_full_fusion.query, results=sys_full_fusion, top_k=10)
        sys_d_time = (time.perf_counter_ns() - start_r) / 1e6 + sys_c_time

        results_map = {
            "A": (vector_res.results, sys_a_time, "Vector"),
            "B": (sys_b_res.results, sys_b_time, "BM25+Vector"),
            "C": (sys_c_res.results, sys_c_time, "Hybrid"),
            "D": (sys_d_res.results, sys_d_time, "Hybrid+Reranking")
        }

        for sys_id, (res_list, lat, _sys_name) in results_map.items():
            retrieved_ids = [r.chunk_id for r in res_list[:10]]
            mrr = calculate_reciprocal_rank(retrieved_ids, relevant_set)
            recalls = {k: calculate_recall_at_k(retrieved_ids, relevant_set, k) for k in k_vals}
            precs = {k: calculate_precision_at_k(retrieved_ids, relevant_set, k) for k in k_vals}
            hits = {k: calculate_hit_rate_at_k(retrieved_ids, relevant_set, k) for k in k_vals}
            ndcgs = {k: calculate_ndcg_at_k(retrieved_ids, rel_grades, k) for k in k_vals}

            sys_metrics[sys_id]["count"] += 1
            sys_metrics[sys_id]["MRR"] += mrr
            for k in k_vals:
                sys_metrics[sys_id][f"Recall@{k}"] += recalls[k]
                sys_metrics[sys_id][f"Precision@{k}"] += precs[k]
                sys_metrics[sys_id][f"HitRate@{k}"] += hits[k]
                sys_metrics[sys_id][f"NDCG@{k}"] += ndcgs[k]

            cat_sys_stats[sys_id][q.category.value]["count"] += 1
            cat_sys_stats[sys_id][q.category.value]["MRR"] += mrr
            cat_sys_stats[sys_id][q.category.value]["Recall@5"] += recalls[5]
            cat_sys_stats[sys_id][q.category.value]["Precision@5"] += precs[5]

            lang_sys_stats[sys_id][q.language]["count"] += 1
            lang_sys_stats[sys_id][q.language]["MRR"] += mrr
            lang_sys_stats[sys_id][q.language]["Recall@5"] += recalls[5]
            lang_sys_stats[sys_id][q.language]["Precision@5"] += precs[5]

            if is_graph_grounded:
                graph_queries_sys_stats[sys_id]["count"] += 1
                graph_queries_sys_stats[sys_id]["MRR"] += mrr
                graph_queries_sys_stats[sys_id]["Recall@5"] += recalls[5]

            out_raw.append({
                "experiment_id": "9C-ablation",
                "system_id": sys_id,
                "benchmark_version": "9A.1",
                "query_id": q.query_id,
                "repository_id": q.repository_id,
                "latency_ms": lat,
                "retrieved_chunk_ids": retrieved_ids,
                "relevant_chunk_ids": list(relevant_set),
                "MRR": mrr,
                **{f"Recall@{k}": recalls[k] for k in k_vals},
                **{f"Precision@{k}": precs[k] for k in k_vals},
                **{f"HitRate@{k}": hits[k] for k in k_vals},
                **{f"NDCG@{k}": ndcgs[k] for k in k_vals}
            })

    def finalize(metrics: dict[str, Any]) -> dict[str, Any]:
        ans: dict[str, Any] = {}
        for s_id, sm in metrics.items():
            ans[s_id] = {}
            count = max(sm["count"], 1)
            for k, v in sm.items():
                if k != "count":
                    ans[s_id][k] = v / count
            ans[s_id]["count"] = sm["count"]
        return ans

    summary = {
        "overall": finalize(sys_metrics),
        "source_contributions": source_stats,
        "category": {s_id: finalize(d) for s_id, d in cat_sys_stats.items()},
        "language": {s_id: finalize(d) for s_id, d in lang_sys_stats.items()},
        "graph_grounded": finalize(graph_queries_sys_stats),
        "traces": representative_traces
    }

    protocol = {
        "frozen": {
            "embedding": "LocalSentenceTransformerProvider(all-MiniLM-L6-v2, 384, cpu)",
            "rrf_k": 60,
            "retriever_depth": 20,
            "rerank_depth": 50,
            "k_eval": k_vals,
        }
    }

    Path("results/phase9/9c/raw").mkdir(parents=True, exist_ok=True)
    Path("results/phase9/9c/summary").mkdir(parents=True, exist_ok=True)
    Path("results/phase9/9c/configuration").mkdir(parents=True, exist_ok=True)

    with open("results/phase9/9c/raw/results.json", "w", encoding="utf-8") as f:
        json.dump(out_raw, f, indent=2)
    with open("results/phase9/9c/summary/metrics.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    with open("results/phase9/9c/configuration/protocol.json", "w", encoding="utf-8") as f:
        json.dump(protocol, f, indent=2)

if __name__ == "__main__":
    main()
