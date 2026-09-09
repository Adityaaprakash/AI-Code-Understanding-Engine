"""Phase 9A - Deterministic Benchmark Loader.

Provides utilities to construct the immutable BenchmarkDataset from fixtures and queries.
"""

from benchmarks.fixtures import (
    build_java_repository,
    build_python_repository,
    build_typescript_repository,
)
from benchmarks.queries import ALL_QUERIES
from benchmarks.schema import BenchmarkDataset, BenchmarkMetadata


class BenchmarkLoader:
    """Deterministic loader for Phase 9A benchmark dataset."""

    _cached_dataset: BenchmarkDataset | None = None

    @classmethod
    def load(cls, force_reload: bool = False) -> BenchmarkDataset:
        if cls._cached_dataset is not None and not force_reload:
            return cls._cached_dataset

        repos = [
            build_python_repository(),
            build_java_repository(),
            build_typescript_repository(),
        ]

        total_files = sum(r.file_count for r in repos)
        total_symbols = sum(r.symbol_count for r in repos)
        total_chunks = sum(r.chunk_count for r in repos)
        total_edges = sum(len(r.graph_edges) for r in repos)

        queries = ALL_QUERIES

        queries_by_cat: dict[str, int] = {}
        for q in queries:
            queries_by_cat[str(q.category.value)] = queries_by_cat.get(str(q.category.value), 0) + 1

        queries_by_diff: dict[str, int] = {}
        for q in queries:
            queries_by_diff[str(q.difficulty.value)] = (
                queries_by_diff.get(str(q.difficulty.value), 0) + 1
            )

        queries_by_lang: dict[str, int] = {}
        for q in queries:
            queries_by_lang[q.language] = queries_by_lang.get(q.language, 0) + 1

        metadata = BenchmarkMetadata(
            languages=["python", "java", "typescript"],
            repository_count=len(repos),
            total_file_count=total_files,
            total_symbol_count=total_symbols,
            total_chunk_count=total_chunks,
            total_graph_edges=total_edges,
            query_count=len(queries),
            query_count_by_category=queries_by_cat,
            query_count_by_difficulty=queries_by_diff,
            query_count_by_language=queries_by_lang,
        )

        dataset = BenchmarkDataset(
            metadata=metadata,
            repositories=repos,
            queries=queries,
        )

        cls._cached_dataset = dataset
        return dataset
