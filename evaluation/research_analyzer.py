import math
from collections import defaultdict
from typing import Any

from evaluation.research_models import (
    AblationDelta,
    AnswerQualityMetrics,
    CategoryMetrics,
    GraphSubsetMetrics,
    LanguageMetrics,
    LatencyMetrics,
    MetricAtK,
    QueryLevelResult,
    ResearchComparisonReport,
    RetrievalMetrics,
    SystemResults,
    TokenMetrics,
)


def build_retrieval_metrics(q_list: list[dict[str, Any]]) -> RetrievalMetrics:
    if not q_list:
        return RetrievalMetrics()
    n = len(q_list)
    prec_1, prec_3, prec_5, prec_10 = 0.0, 0.0, 0.0, 0.0
    rec_1, rec_3, rec_5, rec_10 = 0.0, 0.0, 0.0, 0.0
    hit_1, hit_3, hit_5, hit_10 = 0.0, 0.0, 0.0, 0.0
    ndcg_1, ndcg_3, ndcg_5, ndcg_10 = 0.0, 0.0, 0.0, 0.0
    mrr = 0.0

    for q in q_list:
        mrr += q.get("MRR", 0.0)
        prec_1 += q.get("Precision@1", 0.0)
        prec_3 += q.get("Precision@3", 0.0)
        prec_5 += q.get("Precision@5", 0.0)
        prec_10 += q.get("Precision@10", 0.0)

        rec_1 += q.get("Recall@1", 0.0)
        rec_3 += q.get("Recall@3", 0.0)
        rec_5 += q.get("Recall@5", 0.0)
        rec_10 += q.get("Recall@10", 0.0)

        hit_1 += q.get("HitRate@1", 0.0)
        hit_3 += q.get("HitRate@3", 0.0)
        hit_5 += q.get("HitRate@5", 0.0)
        hit_10 += q.get("HitRate@10", 0.0)

        ndcg_1 += q.get("NDCG@1", 0.0)
        ndcg_3 += q.get("NDCG@3", 0.0)
        ndcg_5 += q.get("NDCG@5", 0.0)
        ndcg_10 += q.get("NDCG@10", 0.0)

    return RetrievalMetrics(
        mrr=mrr / n,
        precision=MetricAtK(k_1=prec_1/n, k_3=prec_3/n, k_5=prec_5/n, k_10=prec_10/n),
        recall=MetricAtK(k_1=rec_1/n, k_3=rec_3/n, k_5=rec_5/n, k_10=rec_10/n),
        hit_rate=MetricAtK(k_1=hit_1/n, k_3=hit_3/n, k_5=hit_5/n, k_10=hit_10/n),
        ndcg=MetricAtK(k_1=ndcg_1/n, k_3=ndcg_3/n, k_5=ndcg_5/n, k_10=ndcg_10/n)
    )

def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals: return 0.0
    n = len(sorted_vals)
    if n == 1: return sorted_vals[0]
    k = (n - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c: return sorted_vals[int(k)]
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return d0 + d1

def build_latency_metrics(q_list: list[dict[str, Any]]) -> LatencyMetrics:
    lats = [q.get("latency_ms", 0.0) for q in q_list if "latency_ms" in q]
    if not lats:
        return LatencyMetrics()
    lats.sort()
    return LatencyMetrics(
        mean_ms=sum(lats) / len(lats),
        p50_ms=percentile(lats, 0.50),
        p95_ms=percentile(lats, 0.95)
    )

class ResearchAnalyzer:
    def __init__(self, raw_9c_results: list[dict[str, Any]], benchmark_dataset: Any, authoritative_summary: dict[str, Any] | None = None):
        self.raw_results = raw_9c_results
        self.dataset = benchmark_dataset
        self.authoritative_summary = authoritative_summary
        self.system_names = {
            "A": "Vector",
            "B": "BM25+Vector",
            "C": "BM25+Vector+Graph",
            "D": "BM25+Vector+Graph+Reranker"
        }

    def analyze(self) -> ResearchComparisonReport:
        # Group by system
        by_sys = defaultdict(list)
        for r in self.raw_results:
            by_sys[r["system_id"]].append(r)

        sys_objs = []
        for s_id, s_name in self.system_names.items():
            q_list = by_sys.get(s_id, [])
            sys_objs.append(
                SystemResults(
                    system_id=s_id,
                    system_name=s_name,
                    query_count=len(q_list),
                    retrieval=build_retrieval_metrics(q_list),
                    latency=build_latency_metrics(q_list),
                    tokens=TokenMetrics(measured=False),
                    answer_quality=AnswerQualityMetrics(measured=False)
                )
            )

        # Category breakdown
        cat_breakdown = defaultdict(list)
        for s_id in self.system_names:
            q_list = by_sys.get(s_id, [])
            by_cat = defaultdict(list)
            # Find category for each query
            q_map = {q.query_id: q for q in self.dataset.queries}
            for r in q_list:
                cat = str(q_map[r["query_id"]].category)
                by_cat[cat].append(r)

            for cat, c_list in by_cat.items():
                cat_breakdown[s_id].append(
                    CategoryMetrics(
                        category=cat,
                        query_count=len(c_list),
                        retrieval=build_retrieval_metrics(c_list)
                    )
                )

        # Language breakdown
        lang_breakdown = defaultdict(list)
        for s_id in self.system_names:
            q_list = by_sys.get(s_id, [])
            by_lang = defaultdict(list)
            q_map = {q.query_id: q for q in self.dataset.queries}
            for r in q_list:
                lang = str(q_map[r["query_id"]].language)
                by_lang[lang].append(r)

            for lang, c_list in by_lang.items():
                lang_breakdown[s_id].append(
                    LanguageMetrics(
                        language=lang,
                        query_count=len(c_list),
                        retrieval=build_retrieval_metrics(c_list)
                    )
                )

        # Graph subset evaluation
        graph_breakdown = []
        q_map = {q.query_id: q for q in self.dataset.queries}
        graph_q_ids = {q.query_id for q in self.dataset.queries if bool(q.graph_ground_truth) or bool(q.multi_hop_paths)}

        # We need to find how many graph discoveries were made.
        # This requires tracking via source contributions across all systems.
        # However, for metric table, we just filter queries in graph_q_ids
        for s_id in self.system_names:
            q_list = by_sys.get(s_id, [])
            g_list = [r for r in q_list if r["query_id"] in graph_q_ids]

            queries_with_graph_candidates = None
            graph_assisted = None
            graph_only = None
            provenance = None
            
            if self.authoritative_summary is not None and s_id == "C":
                sc = self.authoritative_summary.get("source_contributions", {})
                graph_assisted = sc.get("BM25_GRAPH", 0) + sc.get("VECTOR_GRAPH", 0) + sc.get("ALL_THREE", 0)
                graph_only = sc.get("GRAPH_ONLY", 0)
                provenance = "phase9c_authoritative_result"
                
            graph_breakdown.append(
                GraphSubsetMetrics(
                    system_id=s_id,
                    query_count=len(g_list),
                    retrieval=build_retrieval_metrics(g_list),
                    graph_queries_overall=len(graph_q_ids),
                    queries_with_graph_candidates=queries_with_graph_candidates,
                    graph_assisted_discoveries=graph_assisted,
                    graph_only_discoveries=graph_only,
                    provenance=provenance
                )
            )

        # Deltas
        deltas = []
        def calc_delta(s1: str, s2: str, step_name: str) -> AblationDelta:
            if s1 not in by_sys or s2 not in by_sys:
                return AblationDelta(step_name=step_name)
            rm1 = build_retrieval_metrics(by_sys[s1])
            rm2 = build_retrieval_metrics(by_sys[s2])

            m1_mrr = rm1.mrr
            m2_mrr = rm2.mrr
            m1_ndcg = rm1.ndcg.k_5
            m2_ndcg = rm2.ndcg.k_5
            m1_prec = rm1.precision.k_5
            m2_prec = rm2.precision.k_5
            m1_rec = rm1.recall.k_5
            m2_rec = rm2.recall.k_5
            m1_hit = rm1.hit_rate.k_5
            m2_hit = rm2.hit_rate.k_5

            def rel(a: float, b: float) -> float: return (b - a)/a if a > 0 else 0.0

            return AblationDelta(
                step_name=step_name,
                mrr_absolute=m2_mrr - m1_mrr, mrr_relative=rel(m1_mrr, m2_mrr) * 100,
                ndcg_5_absolute=m2_ndcg - m1_ndcg, ndcg_5_relative=rel(m1_ndcg, m2_ndcg) * 100,
                precision_5_absolute=m2_prec - m1_prec, precision_5_relative=rel(m1_prec, m2_prec) * 100,
                recall_5_absolute=m2_rec - m1_rec, recall_5_relative=rel(m1_rec, m2_rec) * 100,
                hit_rate_5_absolute=m2_hit - m1_hit, hit_rate_5_relative=rel(m1_hit, m2_hit) * 100
            )

        deltas.append(calc_delta("A", "B", "Vector \u2192 BM25+Vector"))
        deltas.append(calc_delta("B", "C", "BM25+Vector \u2192 +Graph"))
        deltas.append(calc_delta("C", "D", "+Graph \u2192 +Reranker"))
        deltas.append(calc_delta("A", "D", "Vector \u2192 Final"))

        # Query results
        q_results = []
        for r in self.raw_results:
            q_id = r["query_id"]
            if q_id not in q_map: continue
            q_obj = q_map[q_id]
            q_results.append(
                QueryLevelResult(
                    query_id=q_id,
                    system_id=r.get("system_id", "unknown"),
                    repository_id=r.get("repository_id", "unknown"),
                    category=str(q_obj.category),
                    difficulty=str(q_obj.metadata.get("difficulty", "unknown")) if hasattr(q_obj, "metadata") else str(getattr(q_obj, "difficulty", "unknown")),
                    language=str(q_obj.language),
                    graph_grounded=(q_id in graph_q_ids),
                    multi_hop=bool(q_obj.multi_hop_paths),
                    retrieved_chunk_ids=r.get("retrieved_chunk_ids", []),
                    relevant_chunk_ids=r.get("relevant_chunk_ids", []),
                    retrieval=build_retrieval_metrics([r]),
                    latency_ms=r.get("latency_ms", 0.0),
                    evaluation_error=r.get("evaluation_error", None)
                )
            )

        report = ResearchComparisonReport(
            experiment_id="9D-research-metrics",
            benchmark_version="9A.1",
            timestamp="2026-09-10T00:00:00Z",
            limitations=[
                "Java and TypeScript fixture embedding text contains identical content='code' values, creating deterministic embedding ties.",
                "Frozen benchmark contains only 48 queries over 3 small fixture repositories.",
                "Category sample sizes are very small (n=3-5 instances).",
                "Phase 6 evaluation features (Tokens, Answers, Hallucination) are absent as this is a retrieval test."
            ],
            system_configuration={
                "embedding": "LocalSentenceTransformerProvider(all-MiniLM-L6-v2, 384, cpu)",
                "k_evals": [1, 3, 5, 10]
            },
            systems=sys_objs,
            category_breakdown=cat_breakdown,
            language_breakdown=lang_breakdown,
            graph_breakdown=graph_breakdown,
            ablation_deltas=deltas,
            query_results=q_results
        )

        return report
