# backend/db/models/index_version.py
"""
IndexVersion model — tracks each successful indexing run.

Mirrors the `index_versions` table in .ai/DATABASE_SCHEMA.md exactly.
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, CheckConstraint, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class IndexVersion(Base):
    """A completed indexing run record, enabling history and rollback queries."""

    __tablename__ = "index_versions"

    __table_args__ = (
        CheckConstraint(
            "kind IN ('full', 'incremental')",
            name="ck_index_versions_kind",
        ),
        Index("idx_index_versions_repository_id", "repository_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default="gen_random_uuid()",
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id"),  # no CASCADE — index history should survive job cleanup
        nullable=False,
    )
    commit_sha: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    files_indexed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    symbols_indexed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    chunks_indexed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Repository", back_populates="index_versions"
    )
    job: Mapped["Job"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Job", back_populates="index_versions"
    )
