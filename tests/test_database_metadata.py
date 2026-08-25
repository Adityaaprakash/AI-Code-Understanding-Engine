"""TASK-1C metadata checks that do not require a running database."""

import backend.db.models  # noqa: F401 - registers every model on Base.metadata
from backend.db.base import Base

EXPECTED_TABLES = {
    "repositories",
    "commits",
    "files",
    "symbols",
    "chunks",
    "jobs",
    "index_versions",
}


def test_metadata_contains_exactly_the_initial_schema_tables() -> None:
    """The declarative base must not silently introduce extra tables."""
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_metadata_contains_the_documented_foreign_key_delete_actions() -> None:
    """Relationship integrity is represented in the authoritative ORM metadata."""
    foreign_keys = {
        (table.name, foreign_key.parent.name): foreign_key.ondelete
        for table in Base.metadata.tables.values()
        for foreign_key in table.foreign_keys
    }

    assert foreign_keys == {
        ("commits", "repository_id"): "CASCADE",
        ("files", "repository_id"): "CASCADE",
        ("symbols", "repository_id"): "CASCADE",
        ("symbols", "file_id"): "CASCADE",
        ("chunks", "repository_id"): "CASCADE",
        ("chunks", "file_id"): "CASCADE",
        ("chunks", "symbol_id"): "SET NULL",
        ("jobs", "repository_id"): "CASCADE",
        ("index_versions", "repository_id"): "CASCADE",
        ("index_versions", "job_id"): None,
    }
