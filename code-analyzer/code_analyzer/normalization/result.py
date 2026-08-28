"""Normalization result container model for Canonical Code IR."""

from pydantic import BaseModel, ConfigDict, Field

from code_analyzer.ir import (
    Class,
    File,
    Function,
    Interface,
    Method,
    Module,
    Parameter,
    Reference,
    Symbol,
    Variable,
)
from code_analyzer.parsers.models import ParseDiagnostic


class NormalizationResult(BaseModel):
    """Container holding normalized Canonical Code IR entities extracted from a source file."""

    model_config = ConfigDict(frozen=True)

    file: File
    modules: list[Module] = Field(default_factory=list)
    classes: list[Class] = Field(default_factory=list)
    interfaces: list[Interface] = Field(default_factory=list)
    functions: list[Function] = Field(default_factory=list)
    methods: list[Method] = Field(default_factory=list)
    variables: list[Variable] = Field(default_factory=list)
    parameters: list[Parameter] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    symbols: list[Symbol] = Field(default_factory=list)
    diagnostics: list[ParseDiagnostic] = Field(default_factory=list)
