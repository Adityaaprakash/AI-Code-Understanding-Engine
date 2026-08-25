"""Initial schema — all seven tables.

Revision ID: 0001_initial_schema
Revises: (none)
Create Date: 2026-08-25

This migration implements the full schema defined in .ai/DATABASE_SCHEMA.md.
Tables: repositories, commits, files, symbols, chunks, jobs, index_versions
Extensions: pgvector (vector), pg_trgm (fuzzy text)

IMPORTANT: This migration is hand-reviewed against DATABASE_SCHEMA.md.
Do not modify it to add tables or columns not specified in the schema contract.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────────
    # Extensions
    # ──────────────────────────────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ──────────────────────────────────────────────────────────────────────────
    # repositories
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "repositories",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("source_type", sa.Text, nullable=False),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("local_path", sa.Text, nullable=True),
        sa.Column("default_branch", sa.Text, nullable=False, server_default="main"),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("total_loc", sa.BigInteger, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "source_type IN ('github', 'local')",
            name="ck_repositories_source_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'cloning', 'indexing', 'indexed', 'error', 'stale')",
            name="ck_repositories_status",
        ),
    )

    # ──────────────────────────────────────────────────────────────────────────
    # commits
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "commits",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sha", sa.Text, nullable=False),
        sa.Column("committed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "indexed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("repository_id", "sha", name="uq_commits_repository_sha"),
    )
    op.create_index("idx_commits_repository_id", "commits", ["repository_id"])

    # ──────────────────────────────────────────────────────────────────────────
    # files
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "files",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relative_path", sa.Text, nullable=False),
        sa.Column("language", sa.Text, nullable=False),
        sa.Column("content_hash", sa.Text, nullable=False),
        sa.Column("loc", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "indexed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "language IN ('java', 'python', 'typescript')",
            name="ck_files_language",
        ),
        sa.UniqueConstraint("repository_id", "relative_path", name="uq_files_repository_path"),
    )
    op.create_index("idx_files_repository_id", "files", ["repository_id"])
    op.create_index("idx_files_language", "files", ["language"])

    # ──────────────────────────────────────────────────────────────────────────
    # symbols
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "symbols",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("qualified_name", sa.Text, nullable=False),
        sa.Column("simple_name", sa.Text, nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("language", sa.Text, nullable=False),
        sa.Column("start_line", sa.Integer, nullable=False),
        sa.Column("end_line", sa.Integer, nullable=False),
        sa.Column("doc_comment", sa.Text, nullable=True),
        sa.Column("signature", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "kind IN ('class', 'interface', 'function', 'method', 'variable', 'parameter')",
            name="ck_symbols_kind",
        ),
        sa.CheckConstraint(
            "language IN ('java', 'python', 'typescript')",
            name="ck_symbols_language",
        ),
        sa.UniqueConstraint(
            "repository_id",
            "qualified_name",
            name="uq_symbols_repository_qualified_name",
        ),
    )
    # Add GENERATED ALWAYS AS (tsvector) STORED column — raw DDL required
    op.execute(
        """
        ALTER TABLE symbols
        ADD COLUMN search_vector TSVECTOR
            GENERATED ALWAYS AS (
                to_tsvector('english',
                    coalesce(qualified_name, '') || ' ' ||
                    coalesce(simple_name, '') || ' ' ||
                    coalesce(doc_comment, ''))
            ) STORED
        """
    )
    op.create_index("idx_symbols_repository_id", "symbols", ["repository_id"])
    op.create_index("idx_symbols_file_id", "symbols", ["file_id"])
    op.create_index("idx_symbols_kind", "symbols", ["kind"])
    op.execute(
        "CREATE INDEX idx_symbols_qualified_name ON symbols USING gin(qualified_name gin_trgm_ops)"
    )
    op.execute("CREATE INDEX idx_symbols_search_vector ON symbols USING gin(search_vector)")

    # ──────────────────────────────────────────────────────────────────────────
    # chunks
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "symbol_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("symbols.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("start_line", sa.Integer, nullable=False),
        sa.Column("end_line", sa.Integer, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # GENERATED ALWAYS AS search_vector
    op.execute(
        """
        ALTER TABLE chunks
        ADD COLUMN search_vector TSVECTOR
            GENERATED ALWAYS AS (
                to_tsvector('english', content)
            ) STORED
        """
    )
    # VECTOR(1536) embedding column — requires pgvector extension (installed above)
    op.execute("ALTER TABLE chunks ADD COLUMN embedding VECTOR(1536)")
    op.create_index("idx_chunks_repository_id", "chunks", ["repository_id"])
    op.create_index("idx_chunks_file_id", "chunks", ["file_id"])
    op.create_index("idx_chunks_symbol_id", "chunks", ["symbol_id"])
    op.execute("CREATE INDEX idx_chunks_search_vector ON chunks USING gin(search_vector)")
    # IVFFlat index for approximate nearest-neighbour search
    op.execute(
        "CREATE INDEX idx_chunks_embedding "
        "ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # ──────────────────────────────────────────────────────────────────────────
    # jobs
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default="3"),
        sa.Column(
            "scheduled_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "kind IN ('full_index', 'incremental_index')",
            name="ck_jobs_kind",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'done', 'failed')",
            name="ck_jobs_status",
        ),
    )
    # Partial index for efficient worker polling
    op.execute("CREATE INDEX idx_jobs_pending ON jobs(scheduled_at) WHERE status = 'pending'")

    # ──────────────────────────────────────────────────────────────────────────
    # index_versions
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "index_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id"),  # no CASCADE
            nullable=False,
        ),
        sa.Column("commit_sha", sa.Text, nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("files_indexed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("symbols_indexed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("chunks_indexed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.BigInteger, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "kind IN ('full', 'incremental')",
            name="ck_index_versions_kind",
        ),
    )
    op.create_index("idx_index_versions_repository_id", "index_versions", ["repository_id"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("index_versions")
    op.drop_table("jobs")
    op.drop_table("chunks")
    op.drop_table("symbols")
    op.drop_table("files")
    op.drop_table("commits")
    op.drop_table("repositories")
    # Extensions are left in place on downgrade to avoid breaking other users
    # of the same database instance.
