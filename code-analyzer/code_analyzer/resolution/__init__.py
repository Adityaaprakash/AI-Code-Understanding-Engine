"""Symbol resolution layer for the AI Code Understanding Engine.

Provides symbol registration, symbol table management, import resolution,
and reference resolution for Java, Python, and TypeScript canonical IR.

Pipeline:
    Canonical Code IR
        → SymbolTable (registration + lookup)
        → ImportResolver (language-specific import mapping)
        → ReferenceResolver (symbol resolution of References)
        → ResolutionResult (enriched reference metadata)

The resolved results are compatible with graph.GraphEdge.from_ir_reference()
and ready for TASK-3D Relationship Extraction.
"""

from code_analyzer.resolution.context import ResolutionContext, ScopeKind
from code_analyzer.resolution.import_resolver import ImportResolver
from code_analyzer.resolution.reference_resolver import ReferenceResolver
from code_analyzer.resolution.relationship_extractor import RelationshipExtractor
from code_analyzer.resolution.result import ResolutionResult, ResolutionStatus
from code_analyzer.resolution.symbol_table import SymbolEntry, SymbolTable

__all__ = [
    "ImportResolver",
    "ReferenceResolver",
    "RelationshipExtractor",
    "ResolutionContext",
    "ResolutionResult",
    "ResolutionStatus",
    "ScopeKind",
    "SymbolEntry",
    "SymbolTable",
]
