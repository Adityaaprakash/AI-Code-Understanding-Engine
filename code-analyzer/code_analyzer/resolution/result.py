"""Resolution result model for symbol and import resolution.

Defines the canonical result of attempting to resolve a Reference against
the symbol table and resolved imports.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from code_analyzer.ir import SourceLocation


class ResolutionStatus(StrEnum):
    """Resolution outcome for a single reference resolution attempt."""

    RESOLVED = "resolved"
    """Reference was confidently resolved to exactly one symbol."""

    UNRESOLVED = "unresolved"
    """No matching symbol could be found in scope."""

    AMBIGUOUS = "ambiguous"
    """Multiple equally-plausible candidates exist — do NOT guess."""

    EXTERNAL = "external"
    """Target appears to reference a symbol outside the indexed repository."""

    BUILTIN = "builtin"
    """Target is a known language built-in (e.g. int, str, list in Python)."""


class ResolutionResult(BaseModel):
    """Canonical result of a single reference resolution attempt.

    Encapsulates the outcome of resolving an IR Reference against the symbol
    table and import map.  The resolved ``target_symbol_id`` (if present) can
    drive ``GraphEdge.from_ir_reference`` with full confidence.

    Attributes:
        status: Final resolution outcome.
        reference_id: ID of the IR Reference being resolved.
        source_file_id: File from which the reference originates.
        source_location: Source location of the reference use-site.
        target_qualified_name: Fully qualified name of the resolution target.
        target_symbol_id: Symbol ID in the SymbolTable if resolved.
        candidate_symbol_ids: All candidate IDs when ambiguous.
        confidence: Deterministic confidence value in [0.0, 1.0].
        diagnostic: Human-readable explanation of the resolution outcome.
        attributes: Language-specific metadata preserved for downstream use.
    """

    model_config = ConfigDict(frozen=True)

    status: ResolutionStatus
    reference_id: str
    source_file_id: str | None = None
    source_location: SourceLocation | None = None

    target_qualified_name: str
    target_symbol_id: str | None = None
    candidate_symbol_ids: list[str] = Field(default_factory=list)

    confidence: float = 1.0
    diagnostic: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    def is_resolved(self) -> bool:
        """Return True if the reference was confidently resolved."""
        return self.status == ResolutionStatus.RESOLVED

    @classmethod
    def resolved(
        cls,
        reference_id: str,
        target_qualified_name: str,
        target_symbol_id: str,
        confidence: float = 1.0,
        source_file_id: str | None = None,
        source_location: SourceLocation | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> "ResolutionResult":
        """Factory for a successfully resolved result."""
        return cls(
            status=ResolutionStatus.RESOLVED,
            reference_id=reference_id,
            source_file_id=source_file_id,
            source_location=source_location,
            target_qualified_name=target_qualified_name,
            target_symbol_id=target_symbol_id,
            confidence=confidence,
            attributes=attributes or {},
        )

    @classmethod
    def unresolved(
        cls,
        reference_id: str,
        target_qualified_name: str,
        diagnostic: str | None = None,
        source_file_id: str | None = None,
        source_location: SourceLocation | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> "ResolutionResult":
        """Factory for an unresolved reference."""
        return cls(
            status=ResolutionStatus.UNRESOLVED,
            reference_id=reference_id,
            source_file_id=source_file_id,
            source_location=source_location,
            target_qualified_name=target_qualified_name,
            confidence=0.0,
            diagnostic=diagnostic or f"No symbol found for '{target_qualified_name}'",
            attributes=attributes or {},
        )

    @classmethod
    def ambiguous(
        cls,
        reference_id: str,
        target_qualified_name: str,
        candidate_symbol_ids: list[str],
        source_file_id: str | None = None,
        source_location: SourceLocation | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> "ResolutionResult":
        """Factory for an ambiguous resolution (multiple equally-plausible candidates)."""
        return cls(
            status=ResolutionStatus.AMBIGUOUS,
            reference_id=reference_id,
            source_file_id=source_file_id,
            source_location=source_location,
            target_qualified_name=target_qualified_name,
            candidate_symbol_ids=candidate_symbol_ids,
            confidence=0.0,
            diagnostic=(
                f"Multiple symbols match '{target_qualified_name}': "
                + ", ".join(candidate_symbol_ids[:5])
            ),
            attributes=attributes or {},
        )

    @classmethod
    def external(
        cls,
        reference_id: str,
        target_qualified_name: str,
        source_file_id: str | None = None,
        source_location: SourceLocation | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> "ResolutionResult":
        """Factory for a reference to a symbol outside the indexed repository."""
        return cls(
            status=ResolutionStatus.EXTERNAL,
            reference_id=reference_id,
            source_file_id=source_file_id,
            source_location=source_location,
            target_qualified_name=target_qualified_name,
            confidence=0.0,
            diagnostic=(
                f"Target '{target_qualified_name}' appears to be outside the indexed repository."
            ),
            attributes=attributes or {},
        )

    @classmethod
    def builtin(
        cls,
        reference_id: str,
        target_qualified_name: str,
        source_file_id: str | None = None,
        source_location: SourceLocation | None = None,
    ) -> "ResolutionResult":
        """Factory for a reference to a language built-in."""
        return cls(
            status=ResolutionStatus.BUILTIN,
            reference_id=reference_id,
            source_file_id=source_file_id,
            source_location=source_location,
            target_qualified_name=target_qualified_name,
            confidence=1.0,
            diagnostic=f"'{target_qualified_name}' is a language built-in.",
        )
