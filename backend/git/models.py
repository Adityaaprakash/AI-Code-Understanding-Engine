import enum

from pydantic import BaseModel, ConfigDict


class ChangeType(enum.StrEnum):
    """Types of file changes in a Git repository."""

    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"
    TYPE_CHANGED = "TYPE_CHANGED"


class ChangedFile(BaseModel):
    """Represents a file change between two commits."""

    model_config = ConfigDict(frozen=True)

    path: str
    change_type: ChangeType
    previous_path: str | None = None
    old_blob_id: str | None = None
    new_blob_id: str | None = None


class GitDiffResult(BaseModel):
    """The complete result of a Git diff operation between two commits."""

    model_config = ConfigDict(frozen=True)

    repository_path: str
    base_commit: str
    target_commit: str
    changed_files: list[ChangedFile]
