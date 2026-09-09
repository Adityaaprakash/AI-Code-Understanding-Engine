"""Phase 9A - Benchmark Statistics Generator."""

from pydantic import BaseModel, ConfigDict, Field

from benchmarks.schema import BenchmarkDataset


class BenchmarkStatistics(BaseModel):
    model_config = ConfigDict(frozen=True)
    total_repositories: int = 0
    total_languages: int = 0
    total_files: int = 0
    total_chunks: int = 0
    total_symbols: int = 0
    total_graph_edges: int = 0
    total_queries: int = 0
    queries_by_category: dict[str, int] = Field(default_factory=dict)
    queries_by_difficulty: dict[str, int] = Field(default_factory=dict)
    queries_by_language: dict[str, int] = Field(default_factory=dict)
    avg_judgments_per_query: float = 0.0
    total_essential_judgments: int = 0
    total_relevant_judgments: int = 0
    total_marginal_judgments: int = 0
    total_irrelevant_judgments: int = 0
    total_hard_negatives: int = 0
    total_expected_facts: int = 0
    total_multi_hop_paths: int = 0


def generate_benchmark_statistics(dataset: BenchmarkDataset) -> BenchmarkStatistics:
    total_j_count = 0
    counts_by_grade = {0: 0, 1: 0, 2: 0, 3: 0}
    total_hn = total_facts = total_paths = 0

    for query in dataset.queries:
        total_j_count += len(query.relevance_judgments)
        for j in query.relevance_judgments:
            counts_by_grade[j.grade_value] += 1
        total_hn += len(query.hard_negative_chunk_ids)
        total_facts += len(query.expected_facts)
        total_paths += len(query.multi_hop_paths)

    avg_j = total_j_count / max(1, len(dataset.queries))

    return BenchmarkStatistics(
        total_repositories=dataset.metadata.repository_count,
        total_languages=len(dataset.metadata.languages),
        total_files=dataset.metadata.total_file_count,
        total_chunks=dataset.metadata.total_chunk_count,
        total_symbols=dataset.metadata.total_symbol_count,
        total_graph_edges=dataset.metadata.total_graph_edges,
        total_queries=dataset.metadata.query_count,
        queries_by_category=dataset.metadata.query_count_by_category,
        queries_by_difficulty=dataset.metadata.query_count_by_difficulty,
        queries_by_language=dataset.metadata.query_count_by_language,
        avg_judgments_per_query=avg_j,
        total_essential_judgments=counts_by_grade[3],
        total_relevant_judgments=counts_by_grade[2],
        total_marginal_judgments=counts_by_grade[1],
        total_irrelevant_judgments=counts_by_grade[0],
        total_hard_negatives=total_hn,
        total_expected_facts=total_facts,
        total_multi_hop_paths=total_paths,
    )
