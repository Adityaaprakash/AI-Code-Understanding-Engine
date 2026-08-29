"""Resolution context — carries all state needed during a resolution pass.

The ResolutionContext is the single object passed through import and reference
resolution.  It is immutable at the top level but the mutable alias map
(populated by the import resolution phase) is intentionally a plain dict
to avoid copy overhead.

ScopeKind defines the lexical scope hierarchy used for scope-aware lookup.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from code_analyzer.parsers.models import Language
from code_analyzer.resolution.symbol_table import SymbolTable


class ScopeKind(StrEnum):
    """Lexical scope hierarchy for resolution precedence."""

    PARAMETER = "parameter"
    """Local parameter — highest precedence."""

    LOCAL = "local"
    """Local variable inside a function/method body."""

    METHOD = "method"
    """Method scope inside a class."""

    CLASS = "class"
    """Class scope — class-level members."""

    MODULE = "module"
    """Module / package scope."""

    FILE = "file"
    """File scope — top-level declarations."""

    REPOSITORY = "repository"
    """Repository-wide scope — lowest precedence."""


@dataclass
class ResolutionContext:
    """Carries all state required for a single resolution pass over an IR file.

    Attributes:
        repository_id: The owning repository — enforces isolation.
        file_id: The current file being resolved.
        file_path: The relative path of the current file (for path-based lookups).
        language: The source language of the current file.
        symbol_table: The populated SymbolTable for the repository.
        resolved_imports: Alias/name → target_qualified_name mapping built by
            the import resolution phase.  Mutable — populated before reference
            resolution begins.
        current_class_qname: Qualified name of the enclosing class (if any).
        current_function_qname: Qualified name of the enclosing function/method (if any).
        current_module_qname: Qualified name of the current module.
    """

    repository_id: str
    file_id: str
    file_path: str
    language: Language
    symbol_table: SymbolTable

    # Populated by ImportResolver before ReferenceResolver runs.
    # Maps: local_name_or_alias → target_qualified_name
    resolved_imports: dict[str, str] = field(default_factory=dict)

    # Scope tracking — set by the resolver when entering a class/function.
    current_class_qname: str | None = None
    current_function_qname: str | None = None
    current_module_qname: str | None = None

    def with_class_scope(self, class_qname: str) -> "ResolutionContext":
        """Return a copy of this context scoped inside a class."""
        import copy

        ctx = copy.copy(self)
        ctx.current_class_qname = class_qname
        ctx.current_function_qname = None
        return ctx

    def with_function_scope(self, function_qname: str) -> "ResolutionContext":
        """Return a copy of this context scoped inside a function/method."""
        import copy

        ctx = copy.copy(self)
        ctx.current_function_qname = function_qname
        return ctx

    def resolve_alias(self, local_name: str) -> str | None:
        """Resolve a local alias or import-bound name to its qualified target.

        Returns the qualified name if the local_name is in the resolved imports
        map, otherwise returns None.
        """
        return self.resolved_imports.get(local_name)

    def scoped_qualified_prefix(self) -> str | None:
        """Return the most-specific enclosing scope qualified name prefix.

        Used to build candidate qualified names from simple names found in
        narrow scopes (e.g. a method call inside a class method).
        """
        if self.current_function_qname:
            return self.current_function_qname
        if self.current_class_qname:
            return self.current_class_qname
        return self.current_module_qname
