"""Lightweight language-independent type representation model for Canonical Code IR."""

from pydantic import BaseModel, ConfigDict, Field


class TypeRepresentation(BaseModel):
    """Canonical representation of a type signature or annotation."""

    model_config = ConfigDict(frozen=True)

    display_name: str
    normalized_name: str | None = None
    type_arguments: list["TypeRepresentation"] = Field(default_factory=list)
    is_optional: bool = False
