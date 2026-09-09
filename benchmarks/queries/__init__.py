"""Phase 9A - Benchmark Queries package init."""

from benchmarks.queries.java_queries import JAVA_QUERIES
from benchmarks.queries.python_queries import PYTHON_QUERIES
from benchmarks.queries.typescript_queries import TYPESCRIPT_QUERIES

ALL_QUERIES = PYTHON_QUERIES + JAVA_QUERIES + TYPESCRIPT_QUERIES

__all__ = ["ALL_QUERIES", "JAVA_QUERIES", "PYTHON_QUERIES", "TYPESCRIPT_QUERIES"]
