"""Language representation and parser result models for AST parsing."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Language(StrEnum):
    """Supported MVP programming languages."""

    JAVA = "java"
    PYTHON = "python"
    TYPESCRIPT = "typescript"


class DiagnosticSeverity(StrEnum):
    """Severity levels for parser diagnostics and errors."""

    ERROR = "error"
    WARNING = "warning"
    FATAL = "fatal"


class ParseDiagnostic(BaseModel):
    """Represents a single syntax error, warning, or parser diagnostic message."""

    model_config = ConfigDict(frozen=True)

    message: str
    line: int | None = None
    column: int | None = None
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    kind: str = "syntax_error"


class ParseResult(BaseModel):
    """Container for the output of a language parser execution.

    Carries language identity, file path context, parsed AST representation,
    diagnostics/errors, and operational success status.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    language: Language
    source_path: str | None = None
    ast: Any = None
    diagnostics: list[ParseDiagnostic] = Field(default_factory=list)
    success: bool = True

    @property
    def has_errors(self) -> bool:
        """Return True if any diagnostic is of severity ERROR or FATAL."""
        return any(
            d.severity in (DiagnosticSeverity.ERROR, DiagnosticSeverity.FATAL)
            for d in self.diagnostics
        )

    @classmethod
    def create_success(
        cls,
        language: Language,
        ast: Any = None,
        source_path: str | None = None,
        diagnostics: list[ParseDiagnostic] | None = None,
    ) -> "ParseResult":
        """Factory method to construct a successful ParseResult."""
        return cls(
            language=language,
            source_path=source_path,
            ast=ast,
            diagnostics=diagnostics or [],
            success=True,
        )

    @classmethod
    def create_failure(
        cls,
        language: Language,
        diagnostics: list[ParseDiagnostic],
        source_path: str | None = None,
        ast: Any = None,
    ) -> "ParseResult":
        """Factory method to construct a failed ParseResult."""
        return cls(
            language=language,
            source_path=source_path,
            ast=ast,
            diagnostics=diagnostics,
            success=False,
        )
