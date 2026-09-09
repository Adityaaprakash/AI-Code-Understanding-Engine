"""Tests for Phase 9A Benchmark Dataset and Protocol."""

import pytest

from benchmarks.config import BenchmarkConfig
from benchmarks.loader import BenchmarkLoader
from benchmarks.validator import BenchmarkValidationError, BenchmarkValidator


def test_benchmark_dataset_loads_deterministically() -> None:
    ds1 = BenchmarkLoader.load(force_reload=True)
    ds2 = BenchmarkLoader.load(force_reload=False)

    assert ds1 is ds2
    assert len(ds1.queries) >= 48
    assert len(ds1.repositories) == 3


def test_benchmark_dataset_schema_integrity() -> None:
    ds = BenchmarkLoader.load()
    try:
        BenchmarkValidator.validate(ds)
    except BenchmarkValidationError as e:
        pytest.fail(f"Validation failed: {e}")


def test_no_answer_leakage_in_ids() -> None:
    ds = BenchmarkLoader.load()

    for query in ds.queries:
        assert query.query_id.startswith("q-")

    for repo in ds.repositories:
        assert repo.repository_id.startswith("repo-")
        for chunk in repo.chunks:
            assert chunk.chunk_id.startswith("chk-")
        for symbol in repo.symbols:
            assert symbol.symbol_id.startswith("sym-")


def test_queries_have_multiple_categories_and_difficulties() -> None:
    ds = BenchmarkLoader.load()
    categories: set[str] = set()
    difficulties: set[str] = set()

    for query in ds.queries:
        categories.add(str(query.category.value))
        difficulties.add(str(query.difficulty.value))

    assert len(categories) == 12
    assert len(difficulties) == 3


def test_benchmark_config_generates() -> None:
    config = BenchmarkConfig.get_phase9_standard_config()
    assert len(config.experiments) == 2
    assert config.experiments[0].experiment_id == "9B-vector-baseline"
