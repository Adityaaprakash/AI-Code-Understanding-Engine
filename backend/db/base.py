# backend/db/base.py
"""
Declarative base shared by ALL SQLAlchemy models.

Rules:
- Every model must inherit from Base.
- Never create a second independent declarative base.
- This module must not import any model — that causes circular imports.
  Models are registered automatically when their module is imported.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Project-wide SQLAlchemy declarative base."""
