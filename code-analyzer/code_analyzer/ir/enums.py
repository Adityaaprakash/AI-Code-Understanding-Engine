"""Enumerations for Canonical Code IR entities, references, and visibility."""

from enum import StrEnum


class EntityKind(StrEnum):
    """Supported canonical entity kinds in the IR hierarchy."""

    REPOSITORY = "repository"
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    INTERFACE = "interface"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    PARAMETER = "parameter"
    REFERENCE = "reference"
    SYMBOL = "symbol"


class ReferenceKind(StrEnum):
    """Supported relationship/reference kinds between IR entities."""

    IMPORT = "import"
    CALL = "call"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    TYPE_USAGE = "type_usage"
    VARIABLE_USAGE = "variable_usage"
    INSTANTIATION = "instantiation"
    OVERRIDE = "override"
    FIELD_ACCESS = "field_access"


class Visibility(StrEnum):
    """Language-neutral visibility modifiers for symbols."""

    PUBLIC = "public"
    PROTECTED = "protected"
    PRIVATE = "private"
    PACKAGE = "package"
    INTERNAL = "internal"
