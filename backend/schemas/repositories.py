# backend/schemas/repositories.py
"""Schemas for Repositories and Indexing Jobs API."""

import uuid
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RepositoryCreate(BaseModel):
    """Schema for adding a new repository to be indexed."""

    name: str = Field(..., description="Display name of the repository.")
    source_type: str = Field(..., description="Must be 'github' or 'local'.")
    url: str | None = Field(None, description="GitHub repository URL if source_type is github.")
    local_path: str | None = Field(None, description="Local path if source_type is local.")
    default_branch: str = Field("main", description="Target branch to index.")

    @model_validator(mode="after")
    def validate_local_path(self) -> "RepositoryCreate":
        if self.source_type == "local":
            if not self.local_path:
                raise ValueError("local_path is required when source_type is local.")
            try:
                # Canonicalize the path to prevent traversal bypasses
                resolved = Path(self.local_path).resolve(strict=True)
            except Exception:
                raise ValueError("local_path does not exist or is invalid.") from None

            if not resolved.is_dir():
                raise ValueError("local_path must be a directory.")

            # The architecture allows developer-supplied arbitrary paths across the host
            # filesystem. It is explicitly a trusted developer input model.
            self.local_path = str(resolved)
        return self


class RepositoryResponse(BaseModel):
    """Schema for returning repository metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source_type: str
    url: str | None
    local_path: str | None
    default_branch: str
    status: str
    error_message: str | None
    total_loc: int | None
    created_at: datetime
    updated_at: datetime


class JobResponse(BaseModel):
    """Schema for representing an asynchronous indexing job status."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    kind: str
    status: str
    error_message: str | None
    attempts: int
    scheduled_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
