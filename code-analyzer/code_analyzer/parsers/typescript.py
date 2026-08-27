"""TypeScript language AST parser implementation using tree-sitter."""

from typing import Any

import tree_sitter_typescript as tsts
from tree_sitter import Language as TSLanguage
from tree_sitter import Parser as TSParser

from code_analyzer.parsers.base import LanguageParser
from code_analyzer.parsers.models import (
    DiagnosticSeverity,
    Language,
    ParseDiagnostic,
    ParseResult,
)
from code_analyzer.parsers.typescript_ast import extract_typescript_structure


class TypeScriptParser(LanguageParser):
    """Tree-sitter based AST parser for TypeScript source files."""

    def __init__(self) -> None:
        """Initialize tree-sitter TypeScript parser."""
        self._ts_language = TSLanguage(tsts.language_typescript())
        self._ts_parser = TSParser(self._ts_language)

    @property
    def language(self) -> Language:
        """Return TypeScript language identifier."""
        return Language.TYPESCRIPT

    def parse(self, source_code: str, source_path: str | None = None) -> ParseResult:
        """Parse TypeScript source code text into a ParseResult containing extracted TypeScriptStructure.

        Args:
            source_code: The raw TypeScript source text to parse.
            source_path: Optional source file path.

        Returns:
            ParseResult carrying TypeScript language identity, extracted TypeScriptStructure AST,
            diagnostics list, and success status.
        """
        try:
            encoded_code = source_code.encode("utf-8")
            tree = self._ts_parser.parse(encoded_code)
        except Exception as exc:
            diagnostic = ParseDiagnostic(
                message=f"Parser execution failed: {exc}",
                line=1,
                column=0,
                severity=DiagnosticSeverity.FATAL,
                kind="parser_failure",
            )
            return ParseResult.create_failure(
                language=self.language,
                diagnostics=[diagnostic],
                source_path=source_path,
            )

        root_node = tree.root_node
        diagnostics = self._find_diagnostics(root_node)
        extracted_structure = extract_typescript_structure(root_node)

        if diagnostics or root_node.has_error:
            if not diagnostics:
                diagnostics.append(
                    ParseDiagnostic(
                        message="Syntax error in TypeScript source code",
                        line=1,
                        column=0,
                        severity=DiagnosticSeverity.ERROR,
                        kind="syntax_error",
                    )
                )
            return ParseResult.create_failure(
                language=self.language,
                diagnostics=diagnostics,
                source_path=source_path,
                ast=extracted_structure,
            )

        return ParseResult.create_success(
            language=self.language,
            ast=extracted_structure,
            source_path=source_path,
        )

    def _find_diagnostics(self, root_node: Any) -> list[ParseDiagnostic]:
        """Find syntax errors and missing tokens in tree-sitter AST."""
        diagnostics: list[ParseDiagnostic] = []

        def _traverse(node: Any) -> None:
            if node.type == "ERROR" or node.is_missing:
                line = node.start_point[0] + 1
                col = node.start_point[1]
                snippet = node.text.decode("utf-8", errors="replace").strip()
                if snippet:
                    msg = f"Syntax error near '{snippet[:30]}'"
                else:
                    msg = f"Syntax error (missing or invalid token) at line {line}, column {col}"

                diagnostics.append(
                    ParseDiagnostic(
                        message=msg,
                        line=line,
                        column=col,
                        severity=DiagnosticSeverity.ERROR,
                        kind="syntax_error",
                    )
                )
            for child in node.children:
                _traverse(child)

        _traverse(root_node)
        return diagnostics
