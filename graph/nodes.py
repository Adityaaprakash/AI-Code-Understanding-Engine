"""Data models representing nodes in the Code Knowledge Graph."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from code_analyzer.ir import (
    Class,
    File,
    Function,
    Interface,
    IREntity,
    Method,
    Module,
    Parameter,
    Repository,
    SourceLocation,
    Symbol,
    Variable,
)
from code_analyzer.parsers.models import Language
from graph.enums import NodeKind


class GraphNode(BaseModel):
    """Immutable data node representation in the Code Knowledge Graph derived from IR entities."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: NodeKind
    name: str | None = None
    qualified_name: str | None = None
    language: Language | str | None = None
    file_id: str | None = None
    location: SourceLocation | None = None
    doc_comment: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def validate_non_empty_id(cls, v: str) -> str:
        """Ensure node ID is non-empty and non-whitespace."""
        if not v or not v.strip():
            raise ValueError("Graph node ID cannot be empty or whitespace")
        return v.strip()

    @classmethod
    def from_ir_entity(cls, entity: IREntity) -> "GraphNode":
        """Factory method to construct a GraphNode from a Canonical Code IR entity.

        Args:
            entity: Canonical Code IR entity node from Phase 2.

        Returns:
            Derived GraphNode instance.
        """
        # Map IR EntityKind string to NodeKind enum
        try:
            node_kind = NodeKind(entity.kind.value)
        except ValueError:
            node_kind = NodeKind.SYMBOL

        file_id: str | None = getattr(entity, "file_id", None)
        language: Language | str | None = getattr(entity, "language", None)
        location: SourceLocation | None = getattr(entity, "location", None)

        # Extract type-specific attributes for graph metadata payload
        extra_attrs: dict[str, Any] = {}

        if isinstance(entity, Repository):
            extra_attrs["root_path"] = entity.root_path
            extra_attrs["files"] = entity.files
            extra_attrs["language_breakdown"] = entity.language_breakdown
        elif isinstance(entity, File):
            extra_attrs["path"] = entity.path
            extra_attrs["content_hash"] = entity.content_hash
            extra_attrs["loc"] = entity.loc
            extra_attrs["module_ids"] = entity.module_ids
            extra_attrs["symbol_ids"] = entity.symbol_ids
            extra_attrs["reference_ids"] = entity.reference_ids
        elif isinstance(entity, Module):
            extra_attrs["exported_symbol_ids"] = entity.exported_symbol_ids
        elif isinstance(entity, (Class, Interface)):
            extra_attrs["modifiers"] = entity.modifiers
            extra_attrs["type_parameters"] = entity.type_parameters
            extra_attrs["method_ids"] = entity.method_ids
            extra_attrs["field_ids"] = entity.field_ids
            extra_attrs["visibility"] = entity.visibility.value if entity.visibility else None
        elif isinstance(entity, (Function, Method)):
            extra_attrs["parameters"] = [p.model_dump() for p in entity.parameters]
            if isinstance(entity.return_type, BaseModel):
                extra_attrs["return_type"] = entity.return_type.model_dump()
            elif entity.return_type is not None:
                extra_attrs["return_type"] = entity.return_type
            else:
                extra_attrs["return_type"] = None
            extra_attrs["is_async"] = entity.is_async
            extra_attrs["modifiers"] = entity.modifiers
            extra_attrs["visibility"] = entity.visibility.value if entity.visibility else None
            if isinstance(entity, Method):
                extra_attrs["class_id"] = entity.class_id
                extra_attrs["is_static"] = entity.is_static
                extra_attrs["is_abstract"] = entity.is_abstract
                extra_attrs["is_constructor"] = entity.is_constructor
        elif isinstance(entity, Variable):
            extra_attrs["parent_id"] = entity.parent_id
            if isinstance(entity.declared_type, BaseModel):
                extra_attrs["declared_type"] = entity.declared_type.model_dump()
            elif entity.declared_type is not None:
                extra_attrs["declared_type"] = entity.declared_type
            else:
                extra_attrs["declared_type"] = None
            extra_attrs["is_constant"] = entity.is_constant
            extra_attrs["visibility"] = entity.visibility.value if entity.visibility else None
        elif isinstance(entity, Parameter):
            extra_attrs["parent_callable_id"] = entity.parent_callable_id
            extra_attrs["position"] = entity.position
            extra_attrs["is_optional"] = entity.is_optional
            extra_attrs["default_value"] = entity.default_value
        elif isinstance(entity, Symbol):
            extra_attrs["symbol_kind"] = entity.symbol_kind.value
            extra_attrs["embedding_id"] = entity.embedding_id

        # Merge any generic metadata dictionary attached to the IR entity
        if entity.metadata:
            extra_attrs.update(entity.metadata)

        return cls(
            id=entity.id,
            kind=node_kind,
            name=entity.name,
            qualified_name=entity.qualified_name,
            language=language,
            file_id=file_id,
            location=location,
            doc_comment=entity.doc_comment,
            attributes=extra_attrs,
        )
