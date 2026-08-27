"""Abstract base class establishing the parser interface contract."""

from abc import ABC, abstractmethod

from code_analyzer.parsers.models import Language, ParseResult


class LanguageParser(ABC):
    """Abstract contract for language-specific AST parsers.

    All concrete language parsers (Java, Python, TypeScript) must inherit
    from this base class and implement the required language property and
    parse method.
    """

    @property
    @abstractmethod
    def language(self) -> Language:
        """Return the target programming language for this parser instance."""
        ...

    @abstractmethod
    def parse(self, source_code: str, source_path: str | None = None) -> ParseResult:
        """Parse raw source code into a ParseResult containing the AST.

        Args:
            source_code: The raw source code text to be parsed.
            source_path: Optional file path or identifier for source attribution.

        Returns:
            A ParseResult object containing language identity, AST, diagnostics,
            and parsing success status.
        """
        ...
