"""SymbolTable — language-independent in-memory symbol registry.

The symbol table maps deterministic symbol IDs and qualified names to
SymbolEntry records derived from Canonical Code IR. It is the core lookup
index for the reference and import resolution pipelines.

Design principles:
- All indexes are built at registration time for O(1) or O(k) lookups.
- Qualified names are NOT globally unique; repository isolation is enforced.
- Duplicate simple names across different scopes coexist.
- The table is deterministic: insertion order is preserved, iteration results
  are sorted before being returned to callers.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from code_analyzer.ir import (
    Class,
    EntityKind,
    File,
    Function,
    Interface,
    IREntity,
    Method,
    Module,
    Parameter,
    Repository,
    Symbol,
    Variable,
)
from code_analyzer.normalization.result import NormalizationResult
from code_analyzer.parsers.models import Language


class SymbolEntry(BaseModel):
    """Canonical record in the SymbolTable derived from a Canonical Code IR entity.

    Attributes:
        symbol_id: Deterministic UUID matching the IR entity ID.
        qualified_name: Fully qualified name of the symbol.
        simple_name: Unqualified local name.
        kind: Entity kind (class, method, function, variable, etc.).
        file_id: ID of the file that declares this symbol.
        repository_id: ID of the owning repository.
        language: Source language.
        parent_id: ID of the enclosing scope entity (class, module, file).
        attributes: Additional language-specific metadata.
    """

    model_config = ConfigDict(frozen=True)

    symbol_id: str
    qualified_name: str
    simple_name: str
    kind: EntityKind
    file_id: str
    repository_id: str
    language: Language | str | None = None
    parent_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


def _entity_kind(entity: IREntity) -> EntityKind:
    """Map an IR entity to its EntityKind."""
    return entity.kind


def _entry_from_entity(entity: IREntity, repository_id: str) -> SymbolEntry | None:
    """Construct a SymbolEntry from a Canonical Code IR entity.

    Returns None for entity kinds that should not be registered as symbols
    (e.g. Repository, File, which are structural nodes not addressable symbols).
    """
    # Skip non-symbol structural entities
    if isinstance(entity, (Repository, File, Module)):
        return None

    file_id: str = getattr(entity, "file_id", "")
    if not file_id:
        return None

    language: Language | str | None = getattr(entity, "language", None)
    parent_id: str | None = None
    attrs: dict[str, Any] = {}

    if isinstance(entity, Class):
        parent_id = entity.parent_id
        attrs = {
            "modifiers": entity.modifiers,
            "type_parameters": entity.type_parameters,
            "is_abstract": entity.is_abstract,
            "visibility": entity.visibility.value if entity.visibility else None,
        }
    elif isinstance(entity, Interface):
        parent_id = entity.parent_id
        attrs = {
            "modifiers": entity.modifiers,
            "type_parameters": entity.type_parameters,
            "visibility": entity.visibility.value if entity.visibility else None,
        }
    elif isinstance(entity, (Function, Method)):
        parent_id = getattr(entity, "class_id", None) or getattr(entity, "module_id", None)
        attrs = {
            "is_async": entity.is_async,
            "is_static": getattr(entity, "is_static", False),
            "is_abstract": getattr(entity, "is_abstract", False),
            "is_constructor": getattr(entity, "is_constructor", False),
            "modifiers": entity.modifiers,
            "visibility": entity.visibility.value if entity.visibility else None,
        }
    elif isinstance(entity, Variable):
        parent_id = entity.parent_id
        attrs = {
            "is_constant": entity.is_constant,
            "visibility": entity.visibility.value if entity.visibility else None,
        }
    elif isinstance(entity, Parameter):
        parent_id = entity.parent_callable_id
        attrs = {"position": entity.position, "is_optional": entity.is_optional}
    elif isinstance(entity, Symbol):
        attrs = {"symbol_kind": entity.symbol_kind.value}

    qualified_name = entity.qualified_name or entity.name or ""
    simple_name = entity.name or qualified_name.split(".")[-1]

    if not qualified_name:
        return None

    return SymbolEntry(
        symbol_id=entity.id,
        qualified_name=qualified_name,
        simple_name=simple_name,
        kind=_entity_kind(entity),
        file_id=file_id,
        repository_id=repository_id,
        language=language,
        parent_id=parent_id,
        attributes=attrs,
    )


class SymbolTable:
    """In-memory symbol registry providing deterministic lookup by ID, qualified name, and scope.

    The symbol table enforces repository isolation: symbols from different
    repositories are stored separately and cannot cross-resolve.

    Indexes built at registration time:
        _by_id:             symbol_id → SymbolEntry
        _by_qname:          (repo_id, qname) → list[SymbolEntry]
        _by_simple:         (repo_id, simple_name) → list[SymbolEntry]
        _by_file:           (repo_id, file_id) → list[SymbolEntry]
        _by_file_kind:      (repo_id, file_id, kind) → list[SymbolEntry]
    """

    def __init__(self) -> None:
        self._by_id: dict[str, SymbolEntry] = {}
        self._by_qname: dict[tuple[str, str], list[SymbolEntry]] = {}
        self._by_simple: dict[tuple[str, str], list[SymbolEntry]] = {}
        self._by_file: dict[tuple[str, str], list[SymbolEntry]] = {}
        self._by_file_kind: dict[tuple[str, str, str], list[SymbolEntry]] = {}

    # ──────────────────────────────────────────────────────────────────────────
    # Registration
    # ──────────────────────────────────────────────────────────────────────────

    def register(self, entry: SymbolEntry) -> None:
        """Register a single SymbolEntry in all indexes.

        If the same symbol_id has already been registered, the existing entry
        is kept (idempotent — re-registering the same entity has no effect).
        If the same symbol_id maps to a *different* entry, the first wins.
        """
        if entry.symbol_id in self._by_id:
            return  # idempotent — already registered

        self._by_id[entry.symbol_id] = entry

        key_qname = (entry.repository_id, entry.qualified_name)
        self._by_qname.setdefault(key_qname, []).append(entry)

        key_simple = (entry.repository_id, entry.simple_name)
        self._by_simple.setdefault(key_simple, []).append(entry)

        key_file = (entry.repository_id, entry.file_id)
        self._by_file.setdefault(key_file, []).append(entry)

        key_file_kind = (entry.repository_id, entry.file_id, entry.kind.value)
        self._by_file_kind.setdefault(key_file_kind, []).append(entry)

    def register_entity(self, entity: IREntity, repository_id: str) -> SymbolEntry | None:
        """Construct and register a SymbolEntry from a Canonical Code IR entity.

        Returns the registered entry, or None for non-symbol entity kinds.
        """
        entry = _entry_from_entity(entity, repository_id)
        if entry:
            self.register(entry)
        return entry

    def register_normalization_result(
        self, result: NormalizationResult, repository_id: str
    ) -> list[SymbolEntry]:
        """Register all declarable symbols from a NormalizationResult.

        Returns a sorted list of newly registered SymbolEntry records.
        """
        registered: list[SymbolEntry] = []
        all_entities: list[IREntity] = [
            *result.classes,
            *result.interfaces,
            *result.functions,
            *result.methods,
            *result.variables,
            *result.parameters,
        ]
        for entity in all_entities:
            entry = self.register_entity(entity, repository_id)
            if entry:
                registered.append(entry)
        return sorted(registered, key=lambda e: e.qualified_name)

    # ──────────────────────────────────────────────────────────────────────────
    # Lookups
    # ──────────────────────────────────────────────────────────────────────────

    def lookup_by_id(self, symbol_id: str) -> SymbolEntry | None:
        """Look up a symbol by its deterministic UUID."""
        return self._by_id.get(symbol_id)

    def lookup_by_qualified_name(
        self, qualified_name: str, repository_id: str
    ) -> list[SymbolEntry]:
        """Look up symbols by fully-qualified name within a repository.

        Returns a sorted, deterministic list (may be empty).
        Qualified names are NOT globally unique — e.g.:
            module_a.UserService and module_b.UserService coexist.
        """
        key = (repository_id, qualified_name)
        results = list(self._by_qname.get(key, []))
        return sorted(results, key=lambda e: e.symbol_id)

    def lookup_by_simple_name(
        self,
        simple_name: str,
        repository_id: str,
        file_id: str | None = None,
        kind: EntityKind | None = None,
    ) -> list[SymbolEntry]:
        """Look up symbols by unqualified simple name within a repository.

        Optionally filter by file_id and/or entity kind for scope narrowing.
        Returns a sorted, deterministic list.
        """
        key = (repository_id, simple_name)
        candidates = list(self._by_simple.get(key, []))

        if file_id:
            candidates = [e for e in candidates if e.file_id == file_id]
        if kind:
            candidates = [e for e in candidates if e.kind == kind]

        return sorted(candidates, key=lambda e: e.symbol_id)

    def lookup_in_file(
        self,
        file_id: str,
        repository_id: str,
        kind: EntityKind | None = None,
    ) -> list[SymbolEntry]:
        """Retrieve all symbols declared in a specific file.

        Optionally filter by entity kind. Returns a sorted, deterministic list.
        """
        if kind:
            key3 = (repository_id, file_id, kind.value)
            results = list(self._by_file_kind.get(key3, []))
        else:
            key2 = (repository_id, file_id)
            results = list(self._by_file.get(key2, []))

        return sorted(results, key=lambda e: e.qualified_name)

    def lookup_by_suffix(
        self,
        suffix: str,
        repository_id: str,
        kind: EntityKind | None = None,
    ) -> list[SymbolEntry]:
        """Look up symbols whose qualified name ends with the given suffix.

        Useful for resolving partially-qualified references like
        ``payment.PaymentService`` where the full package prefix is unknown.
        Returns a sorted, deterministic list.

        NOTE: This is O(N) over all registered symbols in the repository.
        Use only as a fallback — prefer exact qualified-name lookups first.
        """
        results: list[SymbolEntry] = []
        suffix_lower = suffix.lower()
        for (repo_id, _qname), entries in self._by_qname.items():
            if repo_id != repository_id:
                continue
            for e in entries:
                if e.qualified_name.lower().endswith(suffix_lower) and (
                    kind is None or e.kind == kind
                ):
                    results.append(e)
        return sorted(results, key=lambda e: (e.qualified_name, e.symbol_id))

    # ──────────────────────────────────────────────────────────────────────────
    # Introspection helpers
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def total_symbols(self) -> int:
        """Total number of registered symbols across all repositories."""
        return len(self._by_id)

    def symbols_for_repository(self, repository_id: str) -> list[SymbolEntry]:
        """Return all symbols registered for a specific repository, sorted."""
        results: list[SymbolEntry] = []
        for (repo_id, _qname), entries in self._by_qname.items():
            if repo_id == repository_id:
                results.extend(entries)
        return sorted(results, key=lambda e: e.qualified_name)

    def has_symbol(self, symbol_id: str) -> bool:
        """Return True if a symbol with the given ID has been registered."""
        return symbol_id in self._by_id
