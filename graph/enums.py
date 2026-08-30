"""Enumerations for Code Knowledge Graph nodes, edges, and resolution status."""

from enum import StrEnum


class NodeKind(StrEnum):
    """Enumeration of supported graph node kinds in CodeLens AI."""

    REPOSITORY = "repository"
    FILE = "file"
    MODULE = "module"
    PACKAGE = "package"
    CLASS = "class"
    INTERFACE = "interface"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    PARAMETER = "parameter"
    SYMBOL = "symbol"


class EdgeKind(StrEnum):
    """Enumeration of directed relationship/edge kinds in the Code Knowledge Graph."""

    # Structural & Containment
    CONTAINS = "contains"
    DECLARES = "declares"
    EXPORTS = "exports"

    # Invocation & Reference
    CALLS = "calls"
    IMPORTS = "imports"
    REFERENCES = "references"

    # Type & Subtyping
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    TYPED_AS = "typed_as"
    USES = "uses"

    # Polymorphism & Override
    OVERRIDES = "overrides"

    # Variable & State Access
    READS = "reads"
    WRITES = "writes"
    FIELD_ACCESS = "field_access"


class ResolutionStatus(StrEnum):
    """Resolution status of graph references and edges."""

    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    BUILTIN = "builtin"
    EXTERNAL = "external"
