"""Deterministic entity identity generation for Canonical Code IR."""

import uuid
from typing import Any

# Global namespace UUID for CodeLens AI Canonical Code IR entity identification
CODELENS_IR_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://codelens.ai/ir/v1")


def generate_entity_id(
    kind: str | Any,
    file_path: str,
    qualified_name: str,
    parent_id: str | None = None,
    location_str: str | None = None,
) -> str:
    """Generate a deterministic UUID string for an IR entity based on its logical identity.

    Guarantees that logically identical entities generate identical IDs across
    runtime processes, OS environments, and re-indexes.

    Args:
        kind: EntityKind or string representation of entity kind.
        file_path: Relative file path of the source file.
        qualified_name: Fully qualified or simple name of the entity.
        parent_id: Optional parent entity ID.
        location_str: Optional location range string representation.

    Returns:
        Deterministic UUID v5 string.
    """
    kind_str = kind.value if hasattr(kind, "value") else str(kind)
    normalized_path = file_path.replace("\\", "/").strip("/")

    components = [
        f"kind={kind_str.lower()}",
        f"file={normalized_path}",
        f"qname={qualified_name.strip()}",
    ]
    if parent_id:
        components.append(f"parent={parent_id.strip()}")
    if location_str:
        components.append(f"loc={location_str.strip()}")

    seed_key = "|".join(components)
    return str(uuid.uuid5(CODELENS_IR_NAMESPACE, seed_key))
