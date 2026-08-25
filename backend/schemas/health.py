# backend/schemas/health.py
"""Health endpoint response schema."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Payload returned by the GET /health application status endpoint."""

    status: str = Field(
        default="ok",
        description="Current service health status",
        json_schema_extra={"example": "ok"},
    )


__all__ = ["HealthResponse"]
