"""PostgreSQL-specific SQLAlchemy types used by the database schema."""

from typing import Any

from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType[Any]):
    """The pgvector ``VECTOR(dimensions)`` type without a separate ORM dependency."""

    cache_ok = True

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **_kw: Any) -> str:
        return f"VECTOR({self.dimensions})"
