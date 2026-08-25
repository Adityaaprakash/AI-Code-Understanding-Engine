# backend/schemas/__init__.py
"""Pydantic schemas for API requests, responses, and errors."""

from backend.schemas.errors import ErrorDetail, ErrorResponse
from backend.schemas.health import HealthResponse

__all__ = [
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
]
