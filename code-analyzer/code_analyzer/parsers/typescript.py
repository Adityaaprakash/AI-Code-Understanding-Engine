"""TypeScript language parser abstraction stub."""

from code_analyzer.parsers.base import LanguageParser
from code_analyzer.parsers.models import Language, ParseResult


class TypeScriptParser(LanguageParser):
    """Parser abstraction stub for TypeScript source files.

    Concrete tree-sitter AST extraction logic will be implemented in TASK-2D.
    """

    @property
    def language(self) -> Language:
        """Return TypeScript language identifier."""
        return Language.TYPESCRIPT

    def parse(self, source_code: str, source_path: str | None = None) -> ParseResult:
        """Stub parse execution verifying parser interface contract."""
        return ParseResult.create_success(
            language=self.language,
            ast=None,
            source_path=source_path,
        )
