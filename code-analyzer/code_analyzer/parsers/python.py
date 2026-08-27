"""Python language AST parser implementation using tree-sitter."""

from typing import Any

import tree_sitter_python as tspy
from tree_sitter import Language as TSLanguage
from tree_sitter import Parser as TSParser

from code_analyzer.parsers.base import LanguageParser
from code_analyzer.parsers.models import (
    DiagnosticSeverity,
    Language,
    ParseDiagnostic,
    ParseResult,
)
from code_analyzer.parsers.python_ast import extract_python_module


class PythonParser(LanguageParser):
    """Tree-sitter based AST parser for Python source files."""

    def __init__(self) -> None:
        """Initialize tree-sitter Python parser."""
        self._ts_language = TSLanguage(tspy.language())
        self._ts_parser = TSParser(self._ts_language)

    @property
    def language(self) -> Language:
        """Return Python language identifier."""
        return Language.PYTHON

    def parse(self, source_code: str, source_path: str | None = None) -> ParseResult:
        """Parse Python source code text into a ParseResult containing extracted PythonModule.

        Args:
            source_code: The raw Python source text to parse.
            source_path: Optional source file path.

        Returns:
            ParseResult carrying Python language identity, extracted PythonModule AST,
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
        extracted_module = extract_python_module(root_node)

        if diagnostics or root_node.has_error:
            if not diagnostics:
                diagnostics.append(
                    ParseDiagnostic(
                        message="Syntax error in Python source code",
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
                ast=extracted_module,
            )

        return ParseResult.create_success(
            language=self.language,
            ast=extracted_module,
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
