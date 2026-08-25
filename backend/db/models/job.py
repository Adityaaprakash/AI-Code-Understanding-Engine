# backend/db/models/job.py
"""
Job model — PostgreSQL-backed job queue for asynchronous indexing.

Mirrors the `jobs` table in .ai/DATABASE_SCHEMA.md exactly.
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, CheckConstraint, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class Job(Base):
    """An asynchronous indexing job polled by the worker process."""

    __tablename__ = "jobs"

    __table_args__ = (
        CheckConstraint(
            "kind IN ('full_index', 'incremental_index')",
            name="ck_jobs_kind",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'done', 'failed')",
            name="ck_jobs_status",
        ),
        # Partial index for efficient worker polling of pending jobs
        Index(
            "idx_jobs_pending",
            "scheduled_at",
            postgresql_where="status = 'pending'",
        ),
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
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    scheduled_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="now()"
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Repository", back_populates="jobs"
    )
    index_versions: Mapped[list["IndexVersion"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "IndexVersion", back_populates="job"
    )
