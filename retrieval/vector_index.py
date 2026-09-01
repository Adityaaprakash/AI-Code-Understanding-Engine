"""Production-quality deterministic vector search index implementation."""

import math
from collections.abc import Iterable
from typing import Any

from code_analyzer.parsers.models import Language
from retrieval.contracts import VectorIndexContract
from retrieval.embedding_models import EmbeddingResult
from retrieval.enums import ChunkType
from retrieval.exceptions import (
    EmbeddingDimensionError,
    VectorQueryError,
)
from retrieval.models import CodeChunk
from retrieval.vector_models import VectorDocument, VectorSearchResult


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculate exact cosine similarity between two float vectors."""
    dot = sum(a * b for a, b in zip(v1, v2, strict=True))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    val = dot / (norm1 * norm2)
    return max(-1.0, min(1.0, val))


class RepositoryVectorIndex:
    """Isolated vector index for a single repository."""

    def __init__(self) -> None:
        self.documents: dict[str, VectorDocument] = {}
        self._dimension: int | None = None

    @property
    def dimension(self) -> int | None:
        return self._dimension

    def add(self, document: VectorDocument) -> None:
        """Add or replace a VectorDocument in the repository index.

        Enforces consistent vector dimensions across all indexed documents.
        """
        if self._dimension is None:
            self._dimension = document.dimension
        elif document.dimension != self._dimension:
            raise EmbeddingDimensionError(
                f"Document dimension mismatch: expected {self._dimension}, got {document.dimension}"
            )

        self.documents[document.chunk_id] = document

    def remove(self, chunk_id: str) -> bool:
        """Remove a VectorDocument by chunk_id."""
        if chunk_id in self.documents:
            del self.documents[chunk_id]
            if not self.documents:
                self._dimension = None
            return True
        return False

    def clear(self) -> None:
        """Clear all indexed documents from the repository index."""
        self.documents.clear()
        self._dimension = None

    def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        language: Language | None = None,
        chunk_type: ChunkType | None = None,
        file_path: str | None = None,
        commit_sha: str | None = None,
    ) -> list[VectorSearchResult]:
        """Execute exact cosine similarity vector search with metadata filtering."""
        if not self.documents:
            return []

        # Validate dimension matching if documents are present
        if self._dimension is not None and len(query_vector) != self._dimension:
            raise EmbeddingDimensionError(
                f"Query vector dimension ({len(query_vector)}) does not match index dimension ({self._dimension})"
            )

        matches: list[VectorSearchResult] = []

        for doc in self.documents.values():
            # Apply metadata filters
            if language is not None and doc.language != language:
                continue
            if chunk_type is not None and doc.chunk_type != chunk_type:
                continue
            if file_path is not None and doc.file_path != file_path:
                continue
            if commit_sha is not None and doc.commit_sha != commit_sha:
                continue

            score = cosine_similarity(query_vector, doc.vector)

            matches.append(
                VectorSearchResult(
                    chunk_id=doc.chunk_id,
                    score=score,
                    repository_id=doc.repository_id,
                    commit_id=doc.commit_id,
                    commit_sha=doc.commit_sha,
                    file_path=doc.file_path,
                    language=doc.language,
                    chunk_type=doc.chunk_type,
                    symbol_name=doc.symbol_name,
                    qualified_name=doc.qualified_name,
                    start_line=doc.start_line,
                    end_line=doc.end_line,
                    metadata=doc.metadata,
                )
            )

        # Deterministic sorting: score DESC, chunk_id ASC
        matches.sort(key=lambda r: (-r.score, r.chunk_id))

        return matches[:top_k]


class VectorIndex(VectorIndexContract):
    """Multi-repository vector index manager with strict repository boundary isolation."""

    def __init__(self) -> None:
        self.indexes: dict[str, RepositoryVectorIndex] = {}

    def _get_or_create_repo_index(self, repository_id: str) -> RepositoryVectorIndex:
        if repository_id not in self.indexes:
            self.indexes[repository_id] = RepositoryVectorIndex()
        return self.indexes[repository_id]

    def add(self, embedding: EmbeddingResult, chunk: CodeChunk | None = None) -> None:
        """Add or replace a single vector embedding in the index."""
        repo_index = self._get_or_create_repo_index(embedding.repository_id)

        lang: Language = Language.PYTHON
        ctype: ChunkType = ChunkType.FILE_CONTEXT
        fpath: str = "unknown_file"
        sym_name: str | None = None
        qual_name: str | None = None
        s_line: int | None = None
        e_line: int | None = None
        meta: dict[str, Any] = {}

        if chunk is not None:
            lang = chunk.language
            ctype = chunk.chunk_type
            fpath = chunk.file_path
            sym_name = chunk.name
            qual_name = chunk.qualified_name
            if chunk.source_location:
                s_line = chunk.source_location.start_line
                e_line = chunk.source_location.end_line
            meta = dict(chunk.metadata)

        doc = VectorDocument(
            chunk_id=embedding.chunk_id,
            vector=embedding.vector,
            dimension=embedding.dimension,
            provider_name=embedding.provider_name,
            model_name=embedding.model_name,
            embedding_version=embedding.embedding_version,
            repository_id=embedding.repository_id,
            commit_id=embedding.commit_id,
            commit_sha=embedding.commit_sha,
            file_path=fpath,
            language=lang,
            chunk_type=ctype,
            symbol_name=sym_name,
            qualified_name=qual_name,
            start_line=s_line,
            end_line=e_line,
            metadata=meta,
        )
        repo_index.add(doc)

    def add_many(
        self,
        embeddings: Iterable[EmbeddingResult],
        chunks: dict[str, CodeChunk] | None = None,
    ) -> None:
        """Batch add a collection or iterable of vector embeddings to the index."""
        chunk_map = chunks or {}
        for emb in embeddings:
            chk = chunk_map.get(emb.chunk_id)
            self.add(emb, chunk=chk)

    def remove(self, chunk_id: str, repository_id: str) -> bool:
        """Remove a single vector embedding by chunk_id from a target repository index."""
        if repository_id in self.indexes:
            return self.indexes[repository_id].remove(chunk_id)
        return False

    def clear(self, repository_id: str | None = None) -> None:
        """Clear a specific repository index, or all repository indexes if repository_id is None."""
        if repository_id is not None:
            if repository_id in self.indexes:
                self.indexes[repository_id].clear()
        else:
            for repo_index in self.indexes.values():
                repo_index.clear()
            self.indexes.clear()

    def search(
        self,
        query_vector: list[float],
        repository_id: str,
        top_k: int = 10,
        language: Language | None = None,
        chunk_type: ChunkType | None = None,
        file_path: str | None = None,
        commit_sha: str | None = None,
    ) -> list[VectorSearchResult]:
        """Execute vector similarity search for a target repository."""
        if not repository_id or not repository_id.strip():
            raise VectorQueryError("repository_id cannot be empty or whitespace")
        if top_k <= 0:
            raise VectorQueryError(f"top_k must be > 0, got {top_k}")
        if not query_vector:
            raise VectorQueryError("query_vector cannot be empty")
        for val in query_vector:
            if math.isnan(val) or math.isinf(val):
                raise VectorQueryError("query_vector contains non-finite values (NaN or Inf)")

        repo_index = self.indexes.get(repository_id)
        if repo_index is None:
            return []

        return repo_index.search(
            query_vector=query_vector,
            top_k=top_k,
            language=language,
            chunk_type=chunk_type,
            file_path=file_path,
            commit_sha=commit_sha,
        )

    def document_count(self, repository_id: str | None = None) -> int:
        """Return total indexed vector count for a repository or across all repositories."""
        if repository_id is not None:
            repo_index = self.indexes.get(repository_id)
            return len(repo_index.documents) if repo_index else 0
        return sum(len(r.documents) for r in self.indexes.values())
