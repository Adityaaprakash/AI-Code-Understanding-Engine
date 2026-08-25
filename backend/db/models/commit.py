# backend/db/models/commit.py
"""
Commit model — tracks commit SHAs indexed per repository.

Mirrors the `commits` table in .ai/DATABASE_SCHEMA.md exactly.
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class Commit(Base):
    """A git commit SHA that has been indexed for a repository."""

    __tablename__ = "commits"

    __table_args__ = (
        UniqueConstraint("repository_id", "sha", name="uq_commits_repository_sha"),
        Index("idx_commits_repository_id", "repository_id"),
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
    sha: Mapped[str] = mapped_column(Text, nullable=False)
    committed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    indexed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Repository", back_populates="commits"
    )
