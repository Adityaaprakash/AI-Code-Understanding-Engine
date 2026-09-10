import json
import pytest
from evaluation.research_models import TokenMetrics, AnswerQualityMetrics
from evaluation.research_analyzer import build_retrieval_metrics, build_latency_metrics, percentile, ResearchAnalyzer
from evaluation.models import EvaluationQuery, QueryCategory

class DummyDataset:
    def __init__(self, queries):
        self.queries = queries
        self.metadata = type("M",(), {"dataset_version":"9A.1"})
        
class DummyEnum:
    def __init__(self, val):
        self.value = val
    def __str__(self):
        return self.value

class DummyQuery:
    def __init__(self, qid, cat, lang, graph_gt=False, mh=False):
        self.query_id = qid
        self.category = DummyEnum(cat)
        self.language = DummyEnum(lang)
        self.graph_ground_truth = graph_gt
        self.multi_hop_paths = mh
        self.metadata = {}

def test_metric_aggregation():
    q_list = [{"MRR": 0.5, "Precision@5": 0.2}, {"MRR": 1.0, "Precision@5": 0.4}]
    res = build_retrieval_metrics(q_list)
    assert res.mrr == pytest.approx(0.75)
    assert res.precision.k_5 == pytest.approx(0.3)

def test_k_handling():
    # Verify we handle multiple K bounds correctly
    q = [{"Recall@1": 0.1, "Recall@3": 0.2, "Recall@5": 0.3, "Recall@10": 0.4}]
    res = build_retrieval_metrics(q)
    assert res.recall.k_1 == 0.1
    assert res.recall.k_10 == 0.4

def test_empty_retrieval():
    q_list = []
    res = build_retrieval_metrics(q_list)
    assert res.mrr == 0.0
    assert res.precision.k_5 == 0.0

def test_latency_aggregation():
    q_list = [{"latency_ms": 100}, {"latency_ms": 300}, {"latency_ms": 500}]
    lat = build_latency_metrics(q_list)
    assert lat.mean_ms == 300
    assert lat.p50_ms == 300
    assert lat.p95_ms == 480  # derived from formula
    
def test_ablation_delta_calculation():
    raw = [
        {"system_id": "A", "query_id": "1", "MRR": 0.2, "Recall@5": 0.3},
        {"system_id": "B", "query_id": "1", "MRR": 0.5, "Recall@5": 0.6}
    ]
    ds = DummyDataset([DummyQuery("1", "SYMBOL_DEFINITION", "python")])
    ra = ResearchAnalyzer(raw, ds)
    rep = ra.analyze()
    delta_b_a = next(d for d in rep.ablation_deltas if d.step_name == "Vector → BM25+Vector")
    assert delta_b_a.mrr_absolute == pytest.approx(0.3)
    assert delta_b_a.recall_5_absolute == pytest.approx(0.3)
    assert delta_b_a.mrr_relative == pytest.approx(150.0)

def test_token_and_answer_quality_not_measured():
    raw = [{"system_id": "A", "query_id": "1", "MRR": 1.0}]
    ds = DummyDataset([DummyQuery("1", "SYMBOL_DEFINITION", "python")])
    rep = ResearchAnalyzer(raw, ds).analyze()
    sys_a = next(s for s in rep.systems if s.system_id == "A")
    assert sys_a.tokens.measured is False
    assert sys_a.answer_quality.measured is False

def test_serialization():
    raw = [{"system_id": "A", "query_id": "1", "MRR": 1.0}]
    ds = DummyDataset([DummyQuery("1", "SYMBOL_DEFINITION", "python")])
    rep = ResearchAnalyzer(raw, ds).analyze()
    # verify valid pydantic
    rep_json = rep.model_dump_json()
    assert "benchmark_version" in rep_json
    
def test_category_and_language_aggregation():
    raw = [
        {"system_id": "A", "query_id": "1", "MRR": 0.5},
        {"system_id": "A", "query_id": "2", "MRR": 1.0},
    ]
    ds = DummyDataset([
        DummyQuery("1", "DEPENDENCY", "java"),
        DummyQuery("2", "DEPENDENCY", "typescript")
    ])
    rep = ResearchAnalyzer(raw, ds).analyze()
    dep_metrics = next(c for c in rep.category_breakdown["A"] if c.category == "DEPENDENCY")
    assert dep_metrics.query_count == 2
    assert dep_metrics.retrieval.mrr == 0.75
    
    java_metrics = next(l for l in rep.language_breakdown["A"] if l.language == "java")
    assert java_metrics.query_count == 1
    assert java_metrics.retrieval.mrr == 0.5

def test_small_sample_handling():
    q_list = [{"MRR": 1.0}] # count = 1
    res = build_retrieval_metrics(q_list)
    assert res.mrr == 1.0

def test_zero_denominator_handling():
    delta = next(d for d in ResearchAnalyzer([], DummyDataset([])).analyze().ablation_deltas if "Vector → BM25+Vector" in d.step_name)
    assert delta.mrr_relative == 0.0

def test_graph_subset_aggregation():
    raw = [
        {"system_id": "C", "query_id": "1", "MRR": 0.1},
        {"system_id": "C", "query_id": "2", "MRR": 0.5},
    ]
    ds = DummyDataset([
        DummyQuery("1", "CALL_RELATIONSHIP", "python", graph_gt=True),
        DummyQuery("2", "EXPLANATION", "python", graph_gt=False)
    ])
    rep = ResearchAnalyzer(raw, ds).analyze()
    g_metrics = next(g for g in rep.graph_breakdown if g.system_id == "C")
    assert g_metrics.graph_queries_overall == 1
    assert g_metrics.query_count == 1
    assert g_metrics.retrieval.mrr == 0.1
