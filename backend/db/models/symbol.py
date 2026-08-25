# backend/db/models/symbol.py
"""
Symbol model — one row per named symbol (class, interface, function, method, variable).

Mirrors the `symbols` table in .ai/DATABASE_SCHEMA.md exactly.

Note on search_vector:
  The column is a PostgreSQL GENERATED ALWAYS AS ... STORED computed column.
  SQLAlchemy cannot generate it via Computed() on TSVECTOR portably.
  The column is declared as a read-only mapped_column so that SELECT queries
  can read it. The actual GENERATED ALWAYS AS expression is in the Alembic migration.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class Symbol(Base):
    """A named code symbol within a file (class, function, method, variable, etc.)."""

    __tablename__ = "symbols"

    __table_args__ = (
        CheckConstraint(
            "kind IN ('class', 'interface', 'function', 'method', 'variable', 'parameter')",
            name="ck_symbols_kind",
        ),
        CheckConstraint(
            "language IN ('java', 'python', 'typescript')",
            name="ck_symbols_language",
        ),
        UniqueConstraint(
            "repository_id", "qualified_name", name="uq_symbols_repository_qualified_name"
        ),
        Index("idx_symbols_repository_id", "repository_id"),
        Index("idx_symbols_file_id", "file_id"),
        Index("idx_symbols_kind", "kind"),
        # GIN indexes on qualified_name (pg_trgm) and search_vector are created
        # in the Alembic migration via raw DDL.
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
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
    )
    qualified_name: Mapped[str] = mapped_column(Text, nullable=False)
    simple_name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    doc_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Computed TSVECTOR — read-only from the ORM perspective.
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', coalesce(qualified_name, '') || ' ' || "
            "coalesce(simple_name, '') || ' ' || coalesce(doc_comment, ''))",
            persisted=True,
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Repository", back_populates="symbols"
    )
    file: Mapped["File"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "File", back_populates="symbols"
    )
    chunks: Mapped[list["Chunk"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Chunk",
        back_populates="symbol",
        foreign_keys="Chunk.symbol_id",
    )
