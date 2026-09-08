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


class SymbolChangeType(enum.StrEnum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"
    IDENTITY_ONLY = "IDENTITY_ONLY"


class OpaqueFileFallbackReason(enum.StrEnum):
    UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
    PARSER_FAILURE = "PARSER_FAILURE"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


class OpaqueFile(BaseModel):
    """Represents a changed file where symbol-level analysis could not be performed."""

    model_config = ConfigDict(frozen=True)

    path: str
    reason: OpaqueFileFallbackReason
    change_type: ChangeType


class ChangedSymbol(BaseModel):
    """Represents an individual code symbol that changed between commits."""

    model_config = ConfigDict(frozen=True)

    symbol_id: str
    change_type: SymbolChangeType
    name: str
    qualified_name: str
    kind: str
    file_path: str
    previous_symbol_id: str | None = None
    previous_file_path: str | None = None
    previous_qualified_name: str | None = None


class ChangedSymbolResult(BaseModel):
    """Result of changed-symbol detection across a repository."""

    model_config = ConfigDict(frozen=True)

    repository_path: str
    base_commit: str
    target_commit: str
    changed_symbols: list[ChangedSymbol]
    opaque_files: list[OpaqueFile]
