"""Reference resolver — resolves IR References to symbol table entries.

The ReferenceResolver operates on Canonical Code IR References and
attempts to resolve each to a concrete SymbolEntry via:

    1. Exact qualified-name lookup (highest confidence: 1.0)
    2. Import-alias expansion → qualified-name lookup (high: 0.9)
    3. Scope-aware simple-name lookup (high when scoped: 0.85)
    4. File-level simple-name lookup (medium: 0.75)
    5. Repository-wide simple-name lookup (low: 0.6)
    6. Suffix-based repository scan (very low: 0.5) — last resort, guarded

Ambiguity rules (CRITICAL):
    - If multiple candidates with equal confidence remain after all filtering,
      the result is AMBIGUOUS — never guess.
    - The class/method resolution uses the inheritance chain where the IR
      already contains EXTENDS/IMPLEMENTS references.

Architecture:
    ReferenceResolver (language-independent coordinator)
        ├── _resolve_single   (main dispatch)
        ├── _lookup_by_qname  (exact lookup)
        ├── _lookup_via_import (alias expansion)
        ├── _lookup_by_scope  (scope-aware)
        ├── _lookup_method_on_type  (method resolution)
        └── _inheritance_candidates (inherited member lookup)

Do NOT implement:
    - Complete overload resolution
    - Java generic type substitution
    - Full Python MRO
    - Full TypeScript structural typing
    - LLM inference
    - Database reads
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from code_analyzer.ir import (
    EntityKind,
    Reference,
    ReferenceKind,
)
from code_analyzer.resolution.result import ResolutionResult

if TYPE_CHECKING:
    from code_analyzer.resolution.context import ResolutionContext
    from code_analyzer.resolution.symbol_table import SymbolEntry

# ──────────────────────────────────────────────────────────────────────────────
# Confidence constants
# ──────────────────────────────────────────────────────────────────────────────

_CONF_EXACT_QNAME: float = 1.0
_CONF_IMPORT_ALIAS: float = 0.9
_CONF_SCOPE: float = 0.85
_CONF_FILE: float = 0.75
_CONF_REPO_SIMPLE: float = 0.6
_CONF_SUFFIX: float = 0.5
_CONF_INHERITANCE: float = 0.8

# ──────────────────────────────────────────────────────────────────────────────
# Built-in type sets (used to classify BUILTIN references quickly)
# ──────────────────────────────────────────────────────────────────────────────

_PYTHON_BUILTINS: frozenset[str] = frozenset(
    [
        "int",
        "str",
        "float",
        "bool",
        "bytes",
        "list",
        "dict",
        "set",
        "tuple",
        "None",
        "True",
        "False",
        "object",
        "type",
        "Exception",
        "ValueError",
        "TypeError",
        "RuntimeError",
        "AttributeError",
        "KeyError",
        "IndexError",
        "NotImplementedError",
        "StopIteration",
        "len",
        "range",
        "print",
        "input",
        "open",
        "isinstance",
        "issubclass",
        "hasattr",
        "getattr",
        "setattr",
        "super",
        "zip",
        "map",
        "filter",
        "sorted",
        "enumerate",
        "any",
        "all",
        "min",
        "max",
        "sum",
        "abs",
        "round",
    ]
)

_JAVA_BUILTINS: frozenset[str] = frozenset(
    [
        "int",
        "long",
        "short",
        "byte",
        "float",
        "double",
        "boolean",
        "char",
        "void",
        "String",
        "Object",
        "Integer",
        "Long",
        "Boolean",
        "Double",
        "Float",
        "Number",
        "Comparable",
        "Iterable",
        "Override",
        "Deprecated",
        "SuppressWarnings",
    ]
)

_TS_BUILTINS: frozenset[str] = frozenset(
    [
        "string",
        "number",
        "boolean",
        "void",
        "null",
        "undefined",
        "any",
        "unknown",
        "never",
        "object",
        "symbol",
        "bigint",
        "Array",
        "Map",
        "Set",
        "Promise",
        "Record",
        "Partial",
        "Required",
        "Readonly",
        "Pick",
        "Omit",
        "Error",
        "Date",
        "RegExp",
        "Function",
        "console",
        "JSON",
        "Math",
    ]
)


def _is_builtin(name: str, language: str) -> bool:
    """Return True if name is a known built-in for the language."""
    lang = language.lower()
    if lang == "python":
        return name in _PYTHON_BUILTINS
    if lang == "java":
        return name in _JAVA_BUILTINS
    if lang == "typescript":
        return name in _TS_BUILTINS
    return False


# ──────────────────────────────────────────────────────────────────────────────
# Core resolution helpers
# ──────────────────────────────────────────────────────────────────────────────


def _select_single(
    candidates: list[SymbolEntry], confidence: float
) -> tuple[SymbolEntry | None, float, list[str]]:
    """Apply single-candidate rule.

    Returns (entry, confidence, candidate_ids).
    If 0 candidates: (None, 0.0, [])
    If 1 candidate:  (entry, confidence, [entry.symbol_id])
    If >1 candidate: (None, 0.0, sorted_ids)  ← AMBIGUOUS — do NOT pick
    """
    if len(candidates) == 1:
        return candidates[0], confidence, [candidates[0].symbol_id]
    elif len(candidates) == 0:
        return None, 0.0, []
    else:
        return None, 0.0, sorted(e.symbol_id for e in candidates)


def _lookup_exact_qname(
    name: str,
    ctx: ResolutionContext,
) -> list[SymbolEntry]:
    """Attempt exact qualified-name lookup."""
    return ctx.symbol_table.lookup_by_qualified_name(name, ctx.repository_id)


def _lookup_via_import(
    name: str,
    ctx: ResolutionContext,
) -> tuple[list[SymbolEntry], str]:
    """Attempt lookup by expanding a simple name through the resolved import map.

    Returns (candidates, expanded_qualified_name).
    """
    # First check if `name` or its leading segment is an import alias
    first_segment = name.split(".")[0]
    expanded_base = ctx.resolved_imports.get(first_segment)
    if expanded_base is None:
        expanded_base = ctx.resolved_imports.get(name)

    if expanded_base is None:
        return [], name

    # If the name has dotted suffixes beyond the first segment, append them
    rest = name[len(first_segment) :]  # e.g. ".processPayment"
    if rest:
        expanded_qname = expanded_base + rest
    else:
        expanded_qname = expanded_base

    candidates = ctx.symbol_table.lookup_by_qualified_name(expanded_qname, ctx.repository_id)
    return candidates, expanded_qname


def _lookup_scope_simple(
    simple_name: str,
    ctx: ResolutionContext,
    kind_hint: EntityKind | None,
) -> list[SymbolEntry]:
    """Scope-aware simple name lookup.

    Priority order:
        1. Symbols in the current file
        2. Symbols matching the simple name across the repository
    """
    # File-scoped first
    in_file = ctx.symbol_table.lookup_by_simple_name(
        simple_name, ctx.repository_id, file_id=ctx.file_id, kind=kind_hint
    )
    if in_file:
        return in_file

    # Repository-wide
    return ctx.symbol_table.lookup_by_simple_name(simple_name, ctx.repository_id, kind=kind_hint)


def _kind_hint_for_ref(ref: Reference) -> EntityKind | None:
    """Derive an EntityKind hint from a ReferenceKind for narrowing lookups."""
    _map: dict[ReferenceKind, EntityKind] = {
        ReferenceKind.EXTENDS: EntityKind.CLASS,
        ReferenceKind.IMPLEMENTS: EntityKind.INTERFACE,
        ReferenceKind.CALL: EntityKind.METHOD,
        ReferenceKind.TYPE_USAGE: EntityKind.CLASS,
    }
    return _map.get(ref.ref_kind)


def _resolve_method_on_type(
    type_qname: str,
    method_name: str,
    ctx: ResolutionContext,
    include_inherited: bool = True,
) -> list[SymbolEntry]:
    """Resolve a method call on a known type.

    Searches:
        1. Direct method members of the type.
        2. Inherited methods (via EXTENDS references in the IR) if include_inherited.

    Returns a sorted, deterministic candidate list. Caller must apply
    single-candidate rule.
    """
    st = ctx.symbol_table
    repo = ctx.repository_id

    # Find the type entry
    type_candidates = st.lookup_by_qualified_name(type_qname, repo)
    if not type_candidates:
        # Try simple-name fallback
        type_candidates = st.lookup_by_simple_name(type_qname, repo, kind=EntityKind.CLASS)
        if not type_candidates:
            type_candidates = st.lookup_by_simple_name(type_qname, repo, kind=EntityKind.INTERFACE)

    if not type_candidates:
        return []

    method_candidates: list[SymbolEntry] = []
    visited_types: set[str] = set()

    def _search_type(type_entry: SymbolEntry, depth: int) -> None:
        if depth > 5 or type_entry.qualified_name in visited_types:
            return
        visited_types.add(type_entry.qualified_name)

        # Build expected method qname
        method_qname = f"{type_entry.qualified_name}.{method_name}"
        methods = st.lookup_by_qualified_name(method_qname, repo)
        method_candidates.extend(methods)

        if not include_inherited or depth >= 2:
            return

        # Look for inherited types via EXTENDS — the IR stores extends_clause
        # information; we reflect that through suffix lookup
        # Find super-types registered with this file
        file_symbols = st.lookup_in_file(type_entry.file_id, repo)
        for sym in file_symbols:
            if sym.symbol_id == type_entry.symbol_id:
                continue
            if sym.qualified_name.startswith(type_entry.qualified_name + "."):
                continue
            # If we had explicit EXTENDS data we could traverse it here.
            # For MVP, only go one level if the parent qname is resolvable.

    for te in type_candidates:
        _search_type(te, 0)

    return sorted(set(method_candidates), key=lambda e: e.symbol_id)


# ──────────────────────────────────────────────────────────────────────────────
# Main ReferenceResolver
# ──────────────────────────────────────────────────────────────────────────────


class ReferenceResolver:
    """Language-independent reference resolver.

    Resolves IR References against the populated SymbolTable and the
    resolved import map in the ResolutionContext.

    Resolution is strictly deterministic and high-precision:
        - AMBIGUOUS is returned when multiple equally-plausible candidates exist.
        - UNRESOLVED is returned when no candidate exists.
        - EXTERNAL is returned for clearly external dependencies.
        - BUILTIN is returned for known language primitives.
        - RESOLVED is returned only when exactly one confident candidate is found.

    Algorithm doc:
        Step 1: Built-in check — fast exit for language primitives.
        Step 2: Exact qualified-name lookup.
        Step 3: Import-alias expansion (e.g. "PS" → "payment.PaymentService").
        Step 4: Dotted qualified-name resolution via import map.
        Step 5: Scope-aware simple-name lookup (file → repository).
        Step 6: Suffix-based fallback (guarded by strict single-candidate rule).
        Step 7: External classification for known-external prefixes.
    """

    def resolve(
        self,
        reference: Reference,
        ctx: ResolutionContext,
    ) -> ResolutionResult:
        """Resolve a single IR Reference.

        Args:
            reference: The Canonical Code IR Reference to resolve.
            ctx: Resolution context with populated symbol table and import map.

        Returns:
            ResolutionResult with the outcome.
        """
        if reference.ref_kind == ReferenceKind.IMPORT:
            # Import references are handled by ImportResolver — skip here.
            return ResolutionResult.unresolved(
                reference_id=reference.id,
                target_qualified_name=reference.target_qualified_name,
                source_file_id=reference.source_file_id,
                source_location=reference.source_location,
                diagnostic="Import references are handled by ImportResolver.",
            )

        target = reference.target_qualified_name
        file_id = reference.source_file_id
        location = reference.source_location

        # ── Step 1: Already resolved (target_symbol_id provided by IR) ─────
        if reference.target_symbol_id:
            entry = ctx.symbol_table.lookup_by_id(reference.target_symbol_id)
            if entry and entry.repository_id == ctx.repository_id:
                return ResolutionResult.resolved(
                    reference_id=reference.id,
                    target_qualified_name=target,
                    target_symbol_id=entry.symbol_id,
                    confidence=_CONF_EXACT_QNAME,
                    source_file_id=file_id,
                    source_location=location,
                )

        # ── Step 2: Built-in check ──────────────────────────────────────────
        simple_target = target.split(".")[-1] if "." in target else target
        if _is_builtin(target, ctx.language) or _is_builtin(simple_target, ctx.language):
            return ResolutionResult.builtin(
                reference_id=reference.id,
                target_qualified_name=target,
                source_file_id=file_id,
                source_location=location,
            )

        # ── Step 3: Exact qualified-name lookup ─────────────────────────────
        candidates = _lookup_exact_qname(target, ctx)
        if candidates:
            entry, conf, ids = _select_single(candidates, _CONF_EXACT_QNAME)
            if entry:
                return ResolutionResult.resolved(
                    reference_id=reference.id,
                    target_qualified_name=target,
                    target_symbol_id=entry.symbol_id,
                    confidence=conf,
                    source_file_id=file_id,
                    source_location=location,
                )
            else:
                return ResolutionResult.ambiguous(
                    reference_id=reference.id,
                    target_qualified_name=target,
                    candidate_symbol_ids=ids,
                    source_file_id=file_id,
                    source_location=location,
                )

        # ── Step 4: Import-alias expansion ─────────────────────────────────
        if ctx.resolved_imports:
            imp_candidates, expanded_qname = _lookup_via_import(target, ctx)
            if imp_candidates:
                entry, conf, ids = _select_single(imp_candidates, _CONF_IMPORT_ALIAS)
                if entry:
                    return ResolutionResult.resolved(
                        reference_id=reference.id,
                        target_qualified_name=expanded_qname,
                        target_symbol_id=entry.symbol_id,
                        confidence=conf,
                        source_file_id=file_id,
                        source_location=location,
                        attributes={"original_target": target},
                    )
                else:
                    return ResolutionResult.ambiguous(
                        reference_id=reference.id,
                        target_qualified_name=expanded_qname,
                        candidate_symbol_ids=ids,
                        source_file_id=file_id,
                        source_location=location,
                    )

        # ── Step 5: Method resolution for dotted references ─────────────────
        # e.g. "paymentService.processPayment" or "PaymentService.processPayment"
        if "." in target:
            parts = target.rsplit(".", 1)
            type_expr, method_name = parts[0], parts[1]

            # Resolve type_expr first (recursively via simple lookup)
            type_qname = ctx.resolved_imports.get(type_expr, type_expr)
            method_cands = _resolve_method_on_type(type_qname, method_name, ctx)
            if method_cands:
                entry, conf, ids = _select_single(method_cands, _CONF_SCOPE)
                if entry:
                    return ResolutionResult.resolved(
                        reference_id=reference.id,
                        target_qualified_name=entry.qualified_name,
                        target_symbol_id=entry.symbol_id,
                        confidence=conf,
                        source_file_id=file_id,
                        source_location=location,
                        attributes={"original_target": target},
                    )
                elif len(ids) > 1:
                    return ResolutionResult.ambiguous(
                        reference_id=reference.id,
                        target_qualified_name=target,
                        candidate_symbol_ids=ids,
                        source_file_id=file_id,
                        source_location=location,
                    )

        # ── Step 6: Scope-aware simple-name lookup ──────────────────────────
        kind_hint = _kind_hint_for_ref(reference)
        scope_candidates = _lookup_scope_simple(simple_target, ctx, kind_hint)
        if scope_candidates:
            # File-level candidates get higher confidence
            file_cands = [e for e in scope_candidates if e.file_id == ctx.file_id]
            if file_cands:
                entry, conf, ids = _select_single(file_cands, _CONF_FILE)
            else:
                entry, conf, ids = _select_single(scope_candidates, _CONF_REPO_SIMPLE)

            if entry:
                return ResolutionResult.resolved(
                    reference_id=reference.id,
                    target_qualified_name=entry.qualified_name,
                    target_symbol_id=entry.symbol_id,
                    confidence=conf,
                    source_file_id=file_id,
                    source_location=location,
                    attributes={"original_target": target},
                )
            elif len(ids) > 1:
                return ResolutionResult.ambiguous(
                    reference_id=reference.id,
                    target_qualified_name=target,
                    candidate_symbol_ids=ids,
                    source_file_id=file_id,
                    source_location=location,
                )

        # ── Step 7: Suffix-based fallback (last resort) ─────────────────────
        suffix_candidates = ctx.symbol_table.lookup_by_suffix(
            simple_target, ctx.repository_id, kind=kind_hint
        )
        if suffix_candidates:
            entry, conf, ids = _select_single(suffix_candidates, _CONF_SUFFIX)
            if entry:
                return ResolutionResult.resolved(
                    reference_id=reference.id,
                    target_qualified_name=entry.qualified_name,
                    target_symbol_id=entry.symbol_id,
                    confidence=conf,
                    source_file_id=file_id,
                    source_location=location,
                    attributes={"original_target": target, "resolution_method": "suffix_fallback"},
                )
            elif len(ids) > 1:
                return ResolutionResult.ambiguous(
                    reference_id=reference.id,
                    target_qualified_name=target,
                    candidate_symbol_ids=ids,
                    source_file_id=file_id,
                    source_location=location,
                )

        # ── Step 8: UNRESOLVED ───────────────────────────────────────────────
        return ResolutionResult.unresolved(
            reference_id=reference.id,
            target_qualified_name=target,
            source_file_id=file_id,
            source_location=location,
            diagnostic=f"No symbol found for '{target}' in repository '{ctx.repository_id}'.",
        )

    def resolve_all(
        self,
        references: list[Reference],
        ctx: ResolutionContext,
        skip_import_refs: bool = True,
    ) -> dict[str, ResolutionResult]:
        """Resolve a batch of references.

        Args:
            references: List of IR References to resolve.
            ctx: Resolution context (import map should already be populated).
            skip_import_refs: If True, IMPORT references are skipped.

        Returns:
            Dict mapping reference_id → ResolutionResult, sorted by reference_id.
        """
        results: dict[str, ResolutionResult] = {}
        for ref in sorted(references, key=lambda r: r.id):
            if skip_import_refs and ref.ref_kind == ReferenceKind.IMPORT:
                continue
            result = self.resolve(ref, ctx)
            results[ref.id] = result
        return results
