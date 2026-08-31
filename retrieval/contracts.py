"""Abstract contracts for AST/IR-aware code chunking."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from code_analyzer.normalization import NormalizationResult
from retrieval.models import CodeChunkCollection

if TYPE_CHECKING:
    from retrieval.embedding_models import EmbeddingInput, EmbeddingResult


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
