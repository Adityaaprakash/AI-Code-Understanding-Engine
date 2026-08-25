# backend/schemas/errors.py
"""Standardized error response schemas for CodeLens AI API."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Structured details of an application or HTTP error."""

    code: str = Field(
        ...,
        description="Machine-readable error code",
        json_schema_extra={"example": "NOT_FOUND"},
    )
    message: str = Field(
        ...,
        description="Human-readable error description",
        json_schema_extra={"example": "Resource not found"},
    )
    details: Any | None = Field(
        default=None, description="Optional extra error context or validation errors"
    )


class ErrorResponse(BaseModel):
    """Top-level standardized error envelope."""

    error: ErrorDetail


__all__ = ["ErrorDetail", "ErrorResponse"]
