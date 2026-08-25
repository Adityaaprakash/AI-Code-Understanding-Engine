# backend/db/models/__init__.py
"""
SQLAlchemy ORM models for AI Code Understanding Engine.

Import all models here so that:
1. Alembic's env.py can import this module and discover all metadata.
2. Circular-import issues are avoided — models import Base from db.base,
   and this file imports models (one direction only).

All table names match .ai/DATABASE_SCHEMA.md exactly.
"""

from backend.db.models.chunk import Chunk
from backend.db.models.commit import Commit
from backend.db.models.file import File
from backend.db.models.index_version import IndexVersion
from backend.db.models.job import Job
from backend.db.models.repository import Repository
from backend.db.models.symbol import Symbol

__all__ = [
    "Chunk",
    "Commit",
    "File",
    "IndexVersion",
    "Job",
    "Repository",
    "Symbol",
]
