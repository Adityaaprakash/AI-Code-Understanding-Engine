import json
import os
import sys

# Ensure project root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evaluation.dataset import get_synthetic_benchmark_dataset
from evaluation.research_analyzer import ResearchAnalyzer
from evaluation.research_models import ResearchComparisonReport

def main() -> None:
    print("Loading 9C raw results...")
    raw_path = "results/phase9/9c/raw/results.json"
    if not os.path.exists(raw_path):
        print(f"Error: {raw_path} not found.")
        sys.exit(1)
        
    with open(raw_path, "r", encoding="utf-8") as f:
        raw_results = json.load(f)
        
    print(f"Loaded {len(raw_results)} query logs.")
    
    # We need the benchmark dataset to match query IDs to categories/languages
    # We iterate over all valid benchmark repositories to collect all queries.
    from benchmarks.loader import BenchmarkLoader
    class RepoAggregator:
        def __init__(self) -> None:
            self.queries = BenchmarkLoader.load().queries

    dataset_mock = RepoAggregator()
    print(f"Loaded {len(dataset_mock.queries)} ground-truth queries.")

    summary_path = "results/phase9/9c/summary/metrics.json"
    authoritative_summary = None
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            authoritative_summary = json.load(f)

    analyzer = ResearchAnalyzer(raw_results, dataset_mock, authoritative_summary)
    report = analyzer.analyze()
    
    out_dir = "results/phase9/9d"
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "research_metrics.json")
    
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))
        
    print(f"Wrote JSON report to {json_path}")
    
if __name__ == "__main__":
    main()
