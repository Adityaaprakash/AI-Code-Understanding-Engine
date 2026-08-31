"""Deterministic chunk identity generation for CodeLens AI."""

import uuid
from typing import Any

from code_analyzer.ir import SourceLocation

# Global namespace UUID for CodeLens AI Code Chunks
CODELENS_CHUNK_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://codelens.ai/chunk/v1")


def generate_chunk_id(
    repository_id: str,
    file_path: str,
    chunk_type: str | Any,
    entity_id: str | None = None,
    location: SourceLocation | str | None = None,
    sub_chunk_index: int = 0,
) -> str:
    """Generate a deterministic UUID string for a CodeChunk based on its semantic identity.

    Guarantees that identical chunks generate identical IDs across runtime processes,
    OS environments, and re-indexes.

    Args:
        repository_id: Repository ID.
        file_path: Relative path of the source file.
        chunk_type: ChunkType enum or string representation.
        entity_id: Optional underlying Canonical IR entity ID.
        location: Optional SourceLocation object or formatted location string.
        sub_chunk_index: Sub-chunk index for oversized entities (default 0).

    Returns:
        Deterministic UUID v5 string.
    """
    type_str = chunk_type.value if hasattr(chunk_type, "value") else str(chunk_type)
    normalized_path = file_path.replace("\\", "/").strip("/")

    components = [
        f"repo={repository_id.strip()}",
        f"file={normalized_path}",
        f"type={type_str.lower()}",
    ]
    if entity_id:
        components.append(f"entity={entity_id.strip()}")

    if isinstance(location, SourceLocation):
        loc_str = f"{location.start_line}:{location.start_column}-{location.end_line}:{location.end_column}"
        components.append(f"loc={loc_str}")
    elif isinstance(location, str) and location.strip():
        components.append(f"loc={location.strip()}")

    if sub_chunk_index > 0:
        components.append(f"sub={sub_chunk_index}")

    seed_key = "|".join(components)
    return str(uuid.uuid5(CODELENS_CHUNK_NAMESPACE, seed_key))
