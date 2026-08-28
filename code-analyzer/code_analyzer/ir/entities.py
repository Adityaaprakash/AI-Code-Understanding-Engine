"""Canonical Code IR entity data models."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from code_analyzer.ir.enums import EntityKind, ReferenceKind, Visibility
from code_analyzer.ir.location import SourceLocation
from code_analyzer.ir.types import TypeRepresentation
from code_analyzer.parsers.models import Language


class IREntity(BaseModel):
    """Base abstract entity for Canonical Code IR nodes."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: EntityKind
    name: str | None = None
    qualified_name: str | None = None
    location: SourceLocation | None = None
    doc_comment: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def validate_non_empty_id(cls, v: str) -> str:
        """Ensure entity ID is a non-empty, non-whitespace string."""
        if not v or not v.strip():
            raise ValueError("Entity ID cannot be empty or whitespace")
        return v.strip()


class Repository(IREntity):
    """Canonical representation of a parsed repository."""

    kind: EntityKind = EntityKind.REPOSITORY
    name: str
    root_path: str
    files: list[str] = Field(default_factory=list)
    language_breakdown: dict[Language, int] = Field(default_factory=dict)


class File(IREntity):
    """Canonical representation of a source file in a repository."""

    kind: EntityKind = EntityKind.FILE
    repository_id: str
    path: str
    language: Language
    content_hash: str | None = None
    loc: int = 0
    module_ids: list[str] = Field(default_factory=list)
    symbol_ids: list[str] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)


class Module(IREntity):
    """Canonical representation of a module or package namespace."""

    kind: EntityKind = EntityKind.MODULE
    file_id: str
    name: str
    qualified_name: str
    exported_symbol_ids: list[str] = Field(default_factory=list)


class Reference(IREntity):
    """Canonical representation of a use-site reference from one symbol to another."""

    kind: EntityKind = EntityKind.REFERENCE
    ref_kind: ReferenceKind
    source_symbol_id: str | None = None
    source_file_id: str | None = None
    source_location: SourceLocation | None = None
    target_qualified_name: str
    target_symbol_id: str | None = None
    confidence: float = 1.0


class Parameter(IREntity):
    """Canonical representation of a formal parameter of a function or method."""

    kind: EntityKind = EntityKind.PARAMETER
    parent_callable_id: str | None = None
    name: str
    declared_type: TypeRepresentation | str | None = None
    default_value: str | None = None
    position: int
    modifiers: list[str] = Field(default_factory=list)
    is_optional: bool = False

    @field_validator("position")
    @classmethod
    def validate_position(cls, v: int) -> int:
        """Ensure parameter position is non-negative."""
        if v < 0:
            raise ValueError(f"Parameter position must be >= 0, got {v}")
        return v


class Class(IREntity):
    """Canonical representation of a class declaration."""

    kind: EntityKind = EntityKind.CLASS
    file_id: str
    module_id: str | None = None
    name: str
    qualified_name: str
    modifiers: list[str] = Field(default_factory=list)
    type_parameters: list[str] = Field(default_factory=list)
    parent_id: str | None = None
    superclass_ref: Reference | None = None
    interface_refs: list[Reference] = Field(default_factory=list)
    method_ids: list[str] = Field(default_factory=list)
    field_ids: list[str] = Field(default_factory=list)
    nested_class_ids: list[str] = Field(default_factory=list)
    is_abstract: bool = False
    visibility: Visibility = Visibility.PUBLIC


class Interface(IREntity):
    """Canonical representation of an interface declaration."""

    kind: EntityKind = EntityKind.INTERFACE
    file_id: str
    module_id: str | None = None
    name: str
    qualified_name: str
    modifiers: list[str] = Field(default_factory=list)
    type_parameters: list[str] = Field(default_factory=list)
    parent_id: str | None = None
    extends_refs: list[Reference] = Field(default_factory=list)
    method_ids: list[str] = Field(default_factory=list)
    field_ids: list[str] = Field(default_factory=list)
    visibility: Visibility = Visibility.PUBLIC


class Function(IREntity):
    """Canonical representation of a standalone function declaration."""

    kind: EntityKind = EntityKind.FUNCTION
    file_id: str
    module_id: str | None = None
    name: str
    qualified_name: str
    parameters: list[Parameter] = Field(default_factory=list)
    return_type: TypeRepresentation | str | None = None
    type_parameters: list[str] = Field(default_factory=list)
    modifiers: list[str] = Field(default_factory=list)
    is_async: bool = False
    visibility: Visibility = Visibility.PUBLIC
    parent_id: str | None = None
    call_refs: list[Reference] = Field(default_factory=list)


class Method(IREntity):
    """Canonical representation of a method belonging to a class or interface."""

    kind: EntityKind = EntityKind.METHOD
    file_id: str
    class_id: str | None = None
    name: str
    qualified_name: str
    parameters: list[Parameter] = Field(default_factory=list)
    return_type: TypeRepresentation | str | None = None
    type_parameters: list[str] = Field(default_factory=list)
    modifiers: list[str] = Field(default_factory=list)
    is_async: bool = False
    is_static: bool = False
    is_abstract: bool = False
    is_constructor: bool = False
    overrides_ref: Reference | None = None
    visibility: Visibility = Visibility.PUBLIC
    call_refs: list[Reference] = Field(default_factory=list)


class Variable(IREntity):
    """Canonical representation of a field, property, or variable declaration."""

    kind: EntityKind = EntityKind.VARIABLE
    file_id: str
    parent_id: str | None = None
    name: str
    qualified_name: str
    declared_type: TypeRepresentation | str | None = None
    modifiers: list[str] = Field(default_factory=list)
    initializer: str | None = None
    is_constant: bool = False
    visibility: Visibility = Visibility.PUBLIC


class Symbol(IREntity):
    """Canonical representation of a addressable code symbol in the repository."""

    kind: EntityKind = EntityKind.SYMBOL
    symbol_kind: EntityKind
    name: str
    qualified_name: str
    language: Language
    file_id: str
    embedding_id: str | None = None
