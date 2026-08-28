"""Abstract base class for AST to Canonical Code IR normalizers."""

from abc import ABC, abstractmethod

from code_analyzer.normalization.result import NormalizationResult
from code_analyzer.parsers.models import Language


class ASTNormalizer[T](ABC):
    """Abstract base class for converting language-specific AST models to Canonical Code IR."""

    @abstractmethod
    def normalize(
        self,
        ast: T,
        repository_id: str,
        file_path: str,
        language: Language,
        content_hash: str | None = None,
        loc: int = 0,
    ) -> NormalizationResult:
        """Normalize a language-specific AST model into a canonical NormalizationResult.

        Args:
            ast: Language-specific AST extraction model (e.g. JavaStructure, PythonModule, TypeScriptStructure).
            repository_id: Repository ID string.
            file_path: Relative source file path.
            language: Source code Language enum.
            content_hash: Optional SHA-256 content hash.
            loc: Lines of code count.

        Returns:
            Canonical NormalizationResult containing IR entities and references.
        """
