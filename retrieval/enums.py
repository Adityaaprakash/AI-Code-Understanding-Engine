"""Enumerations for retrieval and code chunking."""

from enum import StrEnum


class ChunkType(StrEnum):
    """Supported semantic chunk types in CodeLens AI retrieval pipeline."""

    FILE_CONTEXT = "file_context"
    MODULE_CONTEXT = "module_context"
    CLASS_CONTEXT = "class_context"
    INTERFACE_CONTEXT = "interface_context"
    FUNCTION = "function"
    METHOD = "method"
    SUB_CHUNK = "sub_chunk"
