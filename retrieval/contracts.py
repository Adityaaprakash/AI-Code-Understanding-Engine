"""Abstract contracts for AST/IR-aware code chunking, embeddings, and retrieval engines."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from code_analyzer.normalization import NormalizationResult
from retrieval.models import CodeChunkCollection

if TYPE_CHECKING:
    from collections.abc import Iterable

    from code_analyzer.parsers.models import Language
    from retrieval.embedding_models import EmbeddingInput, EmbeddingResult
    from retrieval.enums import ChunkType
    from retrieval.lexical_models import LexicalSearchResult
    from retrieval.models import CodeChunk
    from retrieval.query_models import ProcessedQuery
    from retrieval.retrieval_models import RetrievalResultSet
    from retrieval.vector_models import VectorSearchResult


class CodeChunkerContract(ABC):
    """Abstract contract interface for AST/IR-aware code chunking engines."""

    @abstractmethod
    def chunk_normalization_result(
        self,
        result: NormalizationResult,
        source_code: str | None = None,
        max_lines_per_chunk: int = 150,
        commit_id: str | None = None,
        commit_sha: str | None = None,
    ) -> CodeChunkCollection:
        """Generate deterministic semantic chunks from a single file NormalizationResult.

        Args:
            result: Normalized Canonical Code IR result for a single file.
            source_code: Optional original raw source text for snippet extraction.
            max_lines_per_chunk: Maximum line threshold for oversized entity sub-chunking.
            commit_id: Optional internal commit ID.
            commit_sha: Optional Git commit SHA.

        Returns:
            CodeChunkCollection containing ordered semantic chunks.
        """
        raise NotImplementedError

    @abstractmethod
    def chunk_repository(
        self,
        results: list[NormalizationResult],
        source_files: dict[str, str] | None = None,
        max_lines_per_chunk: int = 150,
        commit_id: str | None = None,
        commit_sha: str | None = None,
    ) -> CodeChunkCollection:
        """Generate deterministic semantic chunks across a collection of NormalizationResults.

        Args:
            results: List of NormalizationResults across repository files.
            source_files: Optional mapping of file_path -> raw source code text.
            max_lines_per_chunk: Maximum line threshold for oversized entity sub-chunking.
            commit_id: Optional internal commit ID.
            commit_sha: Optional Git commit SHA.

        Returns:
            Aggregated CodeChunkCollection for the entire repository.
        """
        raise NotImplementedError


class EmbeddingProviderContract(ABC):
    """Abstract contract interface for embedding providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the embedding provider (e.g. 'test', 'openai', 'local')."""
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the embedding model (e.g. 'test-embed-v1', 'text-embedding-3-small')."""
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension produced by this provider."""
        raise NotImplementedError

    @property
    @abstractmethod
    def embedding_version(self) -> str:
        """Stable version tag for the embedding text configuration and model."""
        raise NotImplementedError

    @abstractmethod
    def embed(self, inputs: list["EmbeddingInput"]) -> list["EmbeddingResult"]:
        """Generate dense vector embeddings for a list of EmbeddingInputs.

        Args:
            inputs: List of validated EmbeddingInputs.

        Returns:
            List of EmbeddingResults matching the input order and identity.
        """
        raise NotImplementedError


class LexicalIndexContract(ABC):
    """Abstract contract interface for BM25 lexical code indexes."""

    @abstractmethod
    def add(self, chunk: "CodeChunk") -> None:
        """Add or replace a single CodeChunk in the index."""
        raise NotImplementedError

    @abstractmethod
    def add_many(self, chunks: "CodeChunkCollection | Iterable[CodeChunk]") -> None:
        """Batch add a collection or iterable of CodeChunks to the index."""
        raise NotImplementedError

    @abstractmethod
    def remove(self, chunk_id: str, repository_id: str) -> bool:
        """Remove a single chunk by chunk_id from a target repository index."""
        raise NotImplementedError

    @abstractmethod
    def clear(self, repository_id: str | None = None) -> None:
        """Clear a specific repository index, or all repository indexes if repository_id is None."""
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query: str,
        repository_id: str,
        top_k: int = 10,
        language: "Language | None" = None,
        chunk_type: "ChunkType | None" = None,
        file_path: str | None = None,
        commit_sha: str | None = None,
    ) -> list["LexicalSearchResult"]:
        """Execute BM25 lexical code search for a target repository.

        Args:
            query: Natural language or code search query string.
            repository_id: Target repository identity for search boundary.
            top_k: Maximum number of ranked results to return (must be > 0).
            language: Optional language filter.
            chunk_type: Optional chunk type filter.
            file_path: Optional file path filter.
            commit_sha: Optional commit SHA index version filter.

        Returns:
            List of ranked LexicalSearchResults sorted by score descending and chunk_id ascending.
        """
        raise NotImplementedError

    @abstractmethod
    def document_count(self, repository_id: str | None = None) -> int:
        """Return total indexed document count for a repository or across all repositories."""
        raise NotImplementedError


class LexicalRetrieverContract(ABC):
    """Abstract contract interface for Phase 5 lexical retrieval services."""

    @abstractmethod
    def retrieve(
        self,
        query: "str | ProcessedQuery",
        repository_id: str,
        top_k: int = 10,
        language: "Language | None" = None,
        chunk_type: "ChunkType | None" = None,
        file_path: str | None = None,
        commit_sha: str | None = None,
    ) -> "RetrievalResultSet":
        """Execute Phase 5 lexical retrieval pipeline returning ranked candidates.

        Args:
            query: Raw query string or preprocessed ProcessedQuery.
            repository_id: Target repository identity for search boundary.
            top_k: Maximum number of ranked candidates to return (must be > 0).
            language: Optional language metadata filter.
            chunk_type: Optional chunk type filter.
            file_path: Optional file path filter.
            commit_sha: Optional index version / commit SHA filter.

        Returns:
            RetrievalResultSet containing ProcessedQuery and ordered RetrievalResults.
        """
        raise NotImplementedError


class VectorIndexContract(ABC):
    """Abstract contract interface for vector search indexes."""

    @abstractmethod
    def add(self, embedding: "EmbeddingResult", chunk: "CodeChunk | None" = None) -> None:
        """Add or replace a single vector embedding in the index."""
        raise NotImplementedError

    @abstractmethod
    def add_many(
        self,
        embeddings: "Iterable[EmbeddingResult]",
        chunks: "dict[str, CodeChunk] | None" = None,
    ) -> None:
        """Batch add a collection or iterable of vector embeddings to the index."""
        raise NotImplementedError

    @abstractmethod
    def remove(self, chunk_id: str, repository_id: str) -> bool:
        """Remove a single vector embedding by chunk_id from a target repository index."""
        raise NotImplementedError

    @abstractmethod
    def clear(self, repository_id: str | None = None) -> None:
        """Clear a specific repository index, or all repository indexes if repository_id is None."""
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query_vector: list[float],
        repository_id: str,
        top_k: int = 10,
        language: "Language | None" = None,
        chunk_type: "ChunkType | None" = None,
        file_path: str | None = None,
        commit_sha: str | None = None,
    ) -> list["VectorSearchResult"]:
        """Execute vector similarity search for a target repository.

        Args:
            query_vector: Dense query vector float list.
            repository_id: Target repository identity for search boundary.
            top_k: Maximum number of ranked results to return (must be > 0).
            language: Optional language filter.
            chunk_type: Optional chunk type filter.
            file_path: Optional file path filter.
            commit_sha: Optional commit SHA index version filter.

        Returns:
            List of ranked VectorSearchResults sorted by score descending and chunk_id ascending.
        """
        raise NotImplementedError

    @abstractmethod
    def document_count(self, repository_id: str | None = None) -> int:
        """Return total indexed vector count for a repository or across all repositories."""
        raise NotImplementedError


class VectorRetrieverContract(ABC):
    """Abstract contract interface for Phase 5 vector retrieval services."""

    @abstractmethod
    def retrieve(
        self,
        query: "str | ProcessedQuery",
        repository_id: str,
        top_k: int = 10,
        language: "Language | None" = None,
        chunk_type: "ChunkType | None" = None,
        file_path: str | None = None,
        commit_sha: str | None = None,
    ) -> "RetrievalResultSet":
        """Execute Phase 5 vector retrieval pipeline returning ranked candidates.

        Args:
            query: Raw query string or preprocessed ProcessedQuery.
            repository_id: Target repository identity for search boundary.
            top_k: Maximum number of ranked candidates to return (must be > 0).
            language: Optional language metadata filter.
            chunk_type: Optional chunk type filter.
            file_path: Optional file path filter.
            commit_sha: Optional index version / commit SHA filter.

        Returns:
            RetrievalResultSet containing ProcessedQuery and ordered RetrievalResults.
        """
        raise NotImplementedError


class GraphRetrieverContract(ABC):
    """Abstract contract interface for Phase 5 graph retrieval services."""

    @abstractmethod
    def retrieve(
        self,
        query: "str | ProcessedQuery",
        repository_id: str,
        top_k: int = 10,
        language: "Language | None" = None,
        chunk_type: "ChunkType | None" = None,
        file_path: str | None = None,
        commit_sha: str | None = None,
    ) -> "RetrievalResultSet":
        """Execute Phase 5 graph retrieval pipeline returning ranked structural candidates.

        Args:
            query: Raw query string or preprocessed ProcessedQuery.
            repository_id: Target repository identity for search boundary.
            top_k: Maximum number of ranked candidates to return (must be > 0).
            language: Optional language metadata filter.
            chunk_type: Optional chunk type filter.
            file_path: Optional file path filter.
            commit_sha: Optional index version / commit SHA filter.

        Returns:
            RetrievalResultSet containing ProcessedQuery and ordered RetrievalResults.
        """
        raise NotImplementedError


class CandidateFusionContract(ABC):
    """Abstract contract interface for Phase 5 candidate fusion engines."""

    @abstractmethod
    def fuse(
        self,
        lexical_results: "RetrievalResultSet | None" = None,
        vector_results: "RetrievalResultSet | None" = None,
        graph_results: "RetrievalResultSet | None" = None,
        top_k: int = 10,
    ) -> "RetrievalResultSet":
        """Fuse candidate result sets from independent retrieval branches into a unified RetrievalResultSet.

        Args:
            lexical_results: RetrievalResultSet from Lexical (BM25) retriever.
            vector_results: RetrievalResultSet from Vector retriever.
            graph_results: RetrievalResultSet from Graph retriever.
            top_k: Maximum number of ranked candidates to return (must be > 0).

        Returns:
            RetrievalResultSet containing ProcessedQuery and fused RetrievalResults.
        """
        raise NotImplementedError
