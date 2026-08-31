"""Abstract contracts for AST/IR-aware code chunking."""

from abc import ABC, abstractmethod

from code_analyzer.normalization import NormalizationResult
from retrieval.models import CodeChunkCollection


class CodeChunkerContract(ABC):
    """Abstract contract interface for AST/IR-aware code chunking engines."""

    @abstractmethod
    def chunk_normalization_result(
        self,
        result: NormalizationResult,
        source_code: str | None = None,
        max_lines_per_chunk: int = 150,
    ) -> CodeChunkCollection:
        """Generate deterministic semantic chunks from a single file NormalizationResult.

        Args:
            result: Normalized Canonical Code IR result for a single file.
            source_code: Optional original raw source text for snippet extraction.
            max_lines_per_chunk: Maximum line threshold for oversized entity sub-chunking.

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
    ) -> CodeChunkCollection:
        """Generate deterministic semantic chunks across a collection of NormalizationResults.

        Args:
            results: List of NormalizationResults across repository files.
            source_files: Optional mapping of file_path -> raw source code text.
            max_lines_per_chunk: Maximum line threshold for oversized entity sub-chunking.

        Returns:
            Aggregated CodeChunkCollection for the entire repository.
        """
        raise NotImplementedError
