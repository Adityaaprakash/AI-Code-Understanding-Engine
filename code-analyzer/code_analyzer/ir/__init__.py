"""Canonical Code IR (Intermediate Representation) package.

Provides language-independent, strongly typed, deterministic, and serializable
representations of code entities, locations, types, and references.
"""

from code_analyzer.ir.entities import (
    Class,
    File,
    Function,
    Interface,
    IREntity,
    Method,
    Module,
    Parameter,
    Reference,
    Repository,
    Symbol,
    Variable,
)
from code_analyzer.ir.enums import EntityKind, ReferenceKind, Visibility
from code_analyzer.ir.identity import generate_entity_id
from code_analyzer.ir.location import SourceLocation
from code_analyzer.ir.types import TypeRepresentation

__all__ = [
    "Class",
    "EntityKind",
    "File",
    "Function",
    "IREntity",
    "Interface",
    "Method",
    "Module",
    "Parameter",
    "Reference",
    "ReferenceKind",
    "Repository",
    "SourceLocation",
    "Symbol",
    "TypeRepresentation",
    "Variable",
    "Visibility",
    "generate_entity_id",
]
