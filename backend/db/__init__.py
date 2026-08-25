# backend/db/__init__.py
"""
Database package for AI Code Understanding Engine.

Public surface:
    Base      — declarative base shared by all models

Imports are intentionally minimal here; models are imported explicitly
where needed to avoid circular imports.
"""

from backend.db.base import Base

__all__ = ["Base"]
