"""Data models for code retrieval chunks and chunk collections."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from code_analyzer.ir import SourceLocation
from code_analyzer.parsers.models import Language
from retrieval.enums import ChunkType


class CodeChunk(BaseModel):
    """Immutable model representing a deterministic, retrievable AST/IR-aware code chunk."""

    model_config = ConfigDict(frozen=True)

    id: str
    chunk_type: ChunkType
    repository_id: str
    commit_id: str | None = None
    commit_sha: str | None = None
    file_id: str = ""
    file_path: str
    language: Language

    @model_validator(mode="before")
    @classmethod
    def _populate_defaults(cls, data: Any) -> Any:
        """Populate file_id from file_path if omitted or empty and normalize backslashes."""
        if isinstance(data, dict) and data.get("file_path"):
            norm_path = data["file_path"].replace("\\", "/")
            data["file_path"] = norm_path
            if not data.get("file_id"):
                data["file_id"] = norm_path
            elif isinstance(data.get("file_id"), str):
                data["file_id"] = data["file_id"].replace("\\", "/")
        return data

    entity_id: str | None = None
    parent_entity_id: str | None = None
    parent_chunk_id: str | None = None
    name: str | None = None
    qualified_name: str | None = None
    source_location: SourceLocation
    content: str = ""
    doc_comment: str | None = None
    signature: str | None = None
    sub_chunk_index: int = 0
    total_sub_chunks: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def symbol_name(self) -> str | None:
        """Alias for name, providing canonical symbol identifier search convenience."""
        return self.name

    @property
    def symbol_id(self) -> str | None:
        """Alias for entity_id, providing canonical symbol entity reference convenience."""
        return self.entity_id

    def to_index_dict(self) -> dict[str, Any]:
        """Export comprehensive metadata dictionary for downstream indexing layers (embeddings / BM25)."""
        return {
            "chunk_id": self.id,
            "chunk_type": self.chunk_type.value,
            "repository_id": self.repository_id,
            "commit_id": self.commit_id,
            "commit_sha": self.commit_sha,
            "file_id": self.file_id,
            "file_path": self.file_path,
            "language": self.language.value
            if hasattr(self.language, "value")
            else str(self.language),
            "entity_id": self.entity_id,
            "symbol_id": self.symbol_id,
            "parent_entity_id": self.parent_entity_id,
            "parent_chunk_id": self.parent_chunk_id,
            "symbol_name": self.name,
            "qualified_name": self.qualified_name,
            "signature": self.signature,
            "doc_comment": self.doc_comment,
            "start_line": self.source_location.start_line,
            "end_line": self.source_location.end_line,
            "start_column": self.source_location.start_column,
            "end_column": self.source_location.end_column,
            "sub_chunk_index": self.sub_chunk_index,
            "total_sub_chunks": self.total_sub_chunks,
            "content": self.content,
            "metadata": self.metadata,
        }

    @field_validator("id", "repository_id", "file_id")
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: ValidationInfo) -> str:
        """Ensure core identity strings are non-empty and stripped."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty or whitespace")
        return v.strip()

    @field_validator("file_path")
    @classmethod
    def validate_and_normalize_file_path(cls, v: str) -> str:
        """Ensure file_path is non-empty and normalized to repository-relative path with forward slashes."""
        if not v or not v.strip():
            raise ValueError("file_path cannot be empty or whitespace")
        normalized = v.replace("\\", "/").strip()
        return normalized

    @field_validator("source_location")
    @classmethod
    def validate_source_location(cls, v: SourceLocation) -> SourceLocation:
        """Ensure source location lines are valid (end_line >= start_line)."""
        if v.end_line < v.start_line:
            raise ValueError(
                f"Invalid source location: end_line ({v.end_line}) cannot be less than start_line ({v.start_line})"
            )
        return v

    @field_validator("sub_chunk_index")
    @classmethod
    def validate_sub_chunk_index(cls, v: int) -> int:
        """Ensure sub_chunk_index is non-negative."""
        if v < 0:
            raise ValueError(f"sub_chunk_index must be >= 0, got {v}")
        return v

    @field_validator("total_sub_chunks")
    @classmethod
    def validate_total_sub_chunks(cls, v: int) -> int:
        """Ensure total_sub_chunks is >= 1."""
        if v < 1:
            raise ValueError(f"total_sub_chunks must be >= 1, got {v}")
        return v

    @model_validator(mode="after")
    def validate_chunk_relationships(self) -> "CodeChunk":
        """Validate logical relationships between chunk attributes."""
        if self.sub_chunk_index >= self.total_sub_chunks:
            raise ValueError(
                f"sub_chunk_index ({self.sub_chunk_index}) must be strictly less than "
                f"total_sub_chunks ({self.total_sub_chunks})"
            )
        if (
            self.chunk_type == ChunkType.SUB_CHUNK
            and not self.parent_chunk_id
            and not self.entity_id
        ):
            raise ValueError(
                "SUB_CHUNK must have a valid parent_chunk_id or entity_id (cannot be orphaned)"
            )
        return self


class CodeChunkCollection(BaseModel):
    """Immutable container holding a collection of code chunks with lookup indices."""

    model_config = ConfigDict(frozen=True)

    repository_id: str
    commit_id: str | None = None
    commit_sha: str | None = None
    chunks: list[CodeChunk] = Field(default_factory=list)
    file_chunk_map: dict[str, list[str]] = Field(default_factory=dict)
    entity_chunk_map: dict[str, list[str]] = Field(default_factory=dict)

    @property
    def chunk_count(self) -> int:
        """Return total number of chunks in the collection."""
        return len(self.chunks)

    def __len__(self) -> int:
        """Return total number of chunks in the collection."""
        return len(self.chunks)

    def get_chunks_for_file(self, file_id: str) -> list[CodeChunk]:
        """Retrieve all chunks belonging to a specific file ID."""
        chunk_ids = set(self.file_chunk_map.get(file_id, []))
        return [c for c in self.chunks if c.id in chunk_ids]

    def get_chunks_for_entity(self, entity_id: str) -> list[CodeChunk]:
        """Retrieve all chunks representing or derived from a specific IR entity ID."""
        chunk_ids = set(self.entity_chunk_map.get(entity_id, []))
        return [c for c in self.chunks if c.id in chunk_ids]

    def get_chunk_by_id(self, chunk_id: str) -> CodeChunk | None:
        """Retrieve a single chunk by its unique chunk ID."""
        for chunk in self.chunks:
            if chunk.id == chunk_id:
                return chunk
        return None
