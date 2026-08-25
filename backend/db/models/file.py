# backend/db/models/file.py
"""
File model — one row per source file per repository.

Mirrors the `files` table in .ai/DATABASE_SCHEMA.md exactly.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class File(Base):
    """A source file within an indexed repository."""

    __tablename__ = "files"

    __table_args__ = (
        CheckConstraint(
            "language IN ('java', 'python', 'typescript')",
            name="ck_files_language",
        ),
        UniqueConstraint("repository_id", "relative_path", name="uq_files_repository_path"),
        Index("idx_files_repository_id", "repository_id"),
        Index("idx_files_language", "language"),
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
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    loc: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    indexed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Repository", back_populates="files"
    )
    symbols: Mapped[list["Symbol"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Symbol", back_populates="file", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["Chunk"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Chunk", back_populates="file", cascade="all, delete-orphan"
    )
