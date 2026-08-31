"""Data models for code retrieval chunks and chunk collections."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from code_analyzer.ir import SourceLocation
from code_analyzer.parsers.models import Language
from retrieval.enums import ChunkType


class CodeChunk(BaseModel):
    """Immutable model representing a deterministic, retrievable AST/IR-aware code chunk."""

    model_config = ConfigDict(frozen=True)

    id: str
    chunk_type: ChunkType
    repository_id: str
    file_id: str
    file_path: str
    language: Language
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

    @field_validator("id")
    @classmethod
    def validate_non_empty_id(cls, v: str) -> str:
        """Ensure chunk ID is a non-empty string."""
        if not v or not v.strip():
            raise ValueError("Chunk ID cannot be empty or whitespace")
        return v.strip()

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


class CodeChunkCollection(BaseModel):
    """Immutable container holding a collection of code chunks with lookup indices."""

    model_config = ConfigDict(frozen=True)

    repository_id: str
    chunks: list[CodeChunk] = Field(default_factory=list)
    file_chunk_map: dict[str, list[str]] = Field(default_factory=dict)
    entity_chunk_map: dict[str, list[str]] = Field(default_factory=dict)

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
