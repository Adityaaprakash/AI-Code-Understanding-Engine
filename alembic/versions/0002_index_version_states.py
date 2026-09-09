"""Add index version states and active version management.

Revision ID: 0002_index_version_states
Revises: 0001_initial_schema
Create Date: 2026-09-08

This migration updates the schema to support index versioning (Phase 8E)
by adding lifecycle state and unique constraints to `index_versions`, and
an `active_index_version_id` to `repositories`.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "0002_index_version_states"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────────
    # index_versions
    # ──────────────────────────────────────────────────────────────────────────
    # Add status column tracking index compilation state
    op.add_column(
        "index_versions",
        sa.Column("status", sa.Text, nullable=False, server_default="building"),
    )
    # Require unique logical version per source revision
    op.create_unique_constraint(
        "uq_index_versions_repository_commit",
        "index_versions",
        ["repository_id", "commit_sha"],
    )
    # Add check constraint for status values
    op.create_check_constraint(
        "ck_index_versions_status",
        "index_versions",
        "status IN ('building', 'ready', 'failed')",
    )

    # ──────────────────────────────────────────────────────────────────────────
    # repositories
    # ──────────────────────────────────────────────────────────────────────────
    # Assign an active index version reference
    op.add_column(
        "repositories",
        sa.Column("active_index_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_repositories_active_index_version_id",
        "repositories",
        "index_versions",
        ["active_index_version_id"],
        ["id"],
        ondelete="SET NULL",
        use_alter=True,
    )


def downgrade() -> None:
    # Drop from repositories
    op.drop_constraint(
        "fk_repositories_active_index_version_id", "repositories", type_="foreignkey"
    )
    op.drop_column("repositories", "active_index_version_id")

    # Drop from index_versions
    op.drop_constraint("ck_index_versions_status", "index_versions", type_="check")
    op.drop_constraint("uq_index_versions_repository_commit", "index_versions", type_="unique")
    op.drop_column("index_versions", "status")
