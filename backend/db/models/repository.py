# backend/db/models/repository.py
"""
Repository model — stores metadata about each indexed repository.

Mirrors the `repositories` table in .ai/DATABASE_SCHEMA.md exactly.
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, CheckConstraint, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class Repository(Base):
    """An indexed source repository (GitHub URL or local path)."""

    __tablename__ = "repositories"

    __table_args__ = (
        CheckConstraint(
            "source_type IN ('github', 'local')",
            name="ck_repositories_source_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'cloning', 'indexing', 'indexed', 'error', 'stale')",
            name="ck_repositories_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default="gen_random_uuid()",
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_branch: Mapped[str] = mapped_column(Text, nullable=False, server_default="main")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_loc: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relationships
    commits: Mapped[list["Commit"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Commit", back_populates="repository", cascade="all, delete-orphan"
    )
    files: Mapped[list["File"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "File", back_populates="repository", cascade="all, delete-orphan"
    )
    symbols: Mapped[list["Symbol"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Symbol", back_populates="repository", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["Chunk"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Chunk", back_populates="repository", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["Job"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Job", back_populates="repository", cascade="all, delete-orphan"
    )
    index_versions: Mapped[list["IndexVersion"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "IndexVersion", back_populates="repository", cascade="all, delete-orphan"
    )
