"""Import resolution for Java, Python, and TypeScript Canonical Code IR.

The ImportResolver converts IMPORT-kind IR References into a resolved import
map that binds local aliases and imported names to their target qualified names
within the indexed repository.

Architecture:
    ImportResolver (language-independent coordinator)
        ├── _JavaImportStrategy
        ├── _PythonImportStrategy
        └── _TypeScriptImportStrategy

Each strategy processes the IMPORT references for one file and updates the
ResolutionContext.resolved_imports mapping.

Known limitations (MVP):
    Java:
        - Direct imports:           SUPPORTED
        - Wildcard imports:         PARTIAL (registered as package-level scope hint)
        - Static imports:           PARTIAL (treated as direct imports)
        - Multi-file classpath:     UNSUPPORTED
    Python:
        - module imports:           SUPPORTED
        - from-import:              SUPPORTED
        - aliases (as ...):         SUPPORTED
        - relative imports:         PARTIAL (resolved relative to file path)
        - dynamic imports:          UNSUPPORTED
        - runtime __import__:       UNSUPPORTED
    TypeScript:
        - named imports:            SUPPORTED
        - default imports:          SUPPORTED
        - namespace imports (as):   SUPPORTED
        - relative path resolution: SUPPORTED (./foo, ../foo)
        - absolute/node_modules:    EXTERNAL (not repository-local)
"""

from __future__ import annotations

import posixpath
from typing import TYPE_CHECKING

from code_analyzer.ir import Reference, ReferenceKind
from code_analyzer.parsers.models import Language

if TYPE_CHECKING:
    from code_analyzer.normalization.result import NormalizationResult
    from code_analyzer.resolution.context import ResolutionContext
    from code_analyzer.resolution.symbol_table import SymbolEntry, SymbolTable

# ──────────────────────────────────────────────────────────────────────────────
# Language-specific built-in / standard-library prefixes
# These are used to classify unresolved imports as EXTERNAL rather than guessing.
# ──────────────────────────────────────────────────────────────────────────────

_JAVA_STDLIB_PREFIXES: frozenset[str] = frozenset(
    [
        "java.",
        "javax.",
        "jakarta.",
        "sun.",
        "com.sun.",
        "org.junit.",
        "org.slf4j.",
        "org.apache.",
        "org.springframework.",
        "com.google.",
        "io.grpc.",
    ]
)

_PYTHON_STDLIB_MODULES: frozenset[str] = frozenset(
    [
        "abc",
        "ast",
        "asyncio",
        "collections",
        "contextlib",
        "copy",
        "dataclasses",
        "datetime",
        "enum",
        "functools",
        "hashlib",
        "importlib",
        "inspect",
        "io",
        "itertools",
        "json",
        "logging",
        "math",
        "operator",
        "os",
        "pathlib",
        "pickle",
        "re",
        "shutil",
        "signal",
        "socket",
        "string",
        "struct",
        "sys",
        "tempfile",
        "threading",
        "time",
        "traceback",
        "typing",
        "types",
        "unittest",
        "urllib",
        "uuid",
        "warnings",
        "weakref",
    ]
)

_TS_EXTERNAL_PREFIXES: frozenset[str] = frozenset(
    [
        "@",
        "react",
        "react-dom",
        "next",
        "lodash",
        "axios",
        "express",
        "fastify",
        "rxjs",
        "zone.js",
        "typescript",
        "jest",
        "vitest",
    ]
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _normalize_path(file_path: str) -> str:
    """Normalize a file path to use forward slashes."""
    return file_path.replace("\\", "/")


def _resolve_relative_ts_path(base_file_path: str, relative_path: str) -> str:
    """Resolve a TypeScript relative import path against a base file path.

    E.g.  base=services/order.ts,  relative=./payment  →  services/payment.

    Returns the normalized resolved path without extension.
    """
    base = _normalize_path(base_file_path)
    base_dir = posixpath.dirname(base)
    resolved = posixpath.normpath(posixpath.join(base_dir, relative_path))
    # Strip common TS extensions
    for ext in (".ts", ".tsx", ".js", ".jsx", ".d.ts"):
        if resolved.endswith(ext):
            resolved = resolved[: -len(ext)]
    return resolved.lstrip("./")


def _is_java_external(import_path: str) -> bool:
    """Return True if a Java import path refers to a known external library."""
    return any(import_path.startswith(prefix) for prefix in _JAVA_STDLIB_PREFIXES)


def _is_python_external(module_name: str) -> bool:
    """Return True if a Python module is a known stdlib or external package."""
    root = module_name.split(".")[0].lstrip(".")
    return root in _PYTHON_STDLIB_MODULES


def _is_ts_external(module_path: str) -> bool:
    """Return True if a TypeScript import path is clearly not repository-local."""
    if module_path.startswith("."):
        return False
    for prefix in _TS_EXTERNAL_PREFIXES:
        if module_path.startswith(prefix):
            return True
    # Bare module specifiers without '.' prefix are treated as external
    return not module_path.startswith(".")


# ──────────────────────────────────────────────────────────────────────────────
# Resolved import record
# ──────────────────────────────────────────────────────────────────────────────


class ResolvedImport:
    """Record produced by an import strategy for a single import reference.

    Attributes:
        reference_id: The IR Reference ID of the IMPORT reference.
        local_name: The name bound in the importing file's local scope.
        target_qualified_name: Best-known qualified name of the import target.
        target_symbol_id: Resolved symbol ID if the target was found in the table.
        is_wildcard: True for wildcard/namespace imports (``import *``).
        is_external: True if the target is outside the indexed repository.
    """

    __slots__ = (
        "is_external",
        "is_wildcard",
        "local_name",
        "reference_id",
        "target_qualified_name",
        "target_symbol_id",
    )

    def __init__(
        self,
        reference_id: str,
        local_name: str,
        target_qualified_name: str,
        target_symbol_id: str | None = None,
        is_wildcard: bool = False,
        is_external: bool = False,
    ) -> None:
        self.reference_id = reference_id
        self.local_name = local_name
        self.target_qualified_name = target_qualified_name
        self.target_symbol_id = target_symbol_id
        self.is_wildcard = is_wildcard
        self.is_external = is_external


# ──────────────────────────────────────────────────────────────────────────────
# Wildcard import index: package/module prefix → members
# ──────────────────────────────────────────────────────────────────────────────


def _build_package_prefix_index(
    symbol_table: SymbolTable,
    repository_id: str,
    package_prefix: str,
) -> list[SymbolEntry]:
    """Return all symbols in the table whose qualified name starts with package_prefix."""
    prefix = package_prefix.rstrip(".*") + "."
    results: list[SymbolEntry] = []
    for entry in symbol_table.symbols_for_repository(repository_id):
        if (
            entry.qualified_name.startswith(prefix)
            and "." not in entry.qualified_name[len(prefix) :]
        ):
            results.append(entry)
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Java import strategy
# ──────────────────────────────────────────────────────────────────────────────


class _JavaImportStrategy:
    """Resolve Java IMPORT references for a single file."""

    def resolve(
        self,
        import_refs: list[Reference],
        symbol_table: SymbolTable,
        repository_id: str,
    ) -> list[ResolvedImport]:
        results: list[ResolvedImport] = []

        for ref in sorted(import_refs, key=lambda r: r.id):
            target_qname = ref.target_qualified_name

            is_wildcard = target_qname.endswith(".*")
            is_external = _is_java_external(target_qname)

            if is_external:
                # Bind simple name from the rightmost segment before .*
                segment = target_qname.rstrip(".*").split(".")[-1] if not is_wildcard else "*"
                results.append(
                    ResolvedImport(
                        reference_id=ref.id,
                        local_name=segment,
                        target_qualified_name=target_qname,
                        is_wildcard=is_wildcard,
                        is_external=True,
                    )
                )
                continue

            if is_wildcard:
                # Wildcard: register all direct members of the package
                package = target_qname[:-2]  # strip .*
                members = _build_package_prefix_index(symbol_table, repository_id, package)
                for member in members:
                    results.append(
                        ResolvedImport(
                            reference_id=ref.id,
                            local_name=member.simple_name,
                            target_qualified_name=member.qualified_name,
                            target_symbol_id=member.symbol_id,
                            is_wildcard=True,
                        )
                    )
                if not members:
                    # Record unsatisfied wildcard for diagnostics
                    results.append(
                        ResolvedImport(
                            reference_id=ref.id,
                            local_name="*",
                            target_qualified_name=target_qname,
                            is_wildcard=True,
                        )
                    )
                continue

            # Direct import — try exact qualified-name lookup
            candidates = symbol_table.lookup_by_qualified_name(target_qname, repository_id)
            local_name = target_qname.split(".")[-1]

            if len(candidates) == 1:
                results.append(
                    ResolvedImport(
                        reference_id=ref.id,
                        local_name=local_name,
                        target_qualified_name=target_qname,
                        target_symbol_id=candidates[0].symbol_id,
                    )
                )
            elif len(candidates) > 1:
                # Ambiguous (same qname in multiple files); bind but don't choose
                results.append(
                    ResolvedImport(
                        reference_id=ref.id,
                        local_name=local_name,
                        target_qualified_name=target_qname,
                    )
                )
            else:
                # Not found in local repo
                results.append(
                    ResolvedImport(
                        reference_id=ref.id,
                        local_name=local_name,
                        target_qualified_name=target_qname,
                    )
                )

        return results


# ──────────────────────────────────────────────────────────────────────────────
# Python import strategy
# ──────────────────────────────────────────────────────────────────────────────


class _PythonImportStrategy:
    """Resolve Python IMPORT references for a single file.

    Python normalizer produces two kinds of IMPORT references:
        from services.payment import PaymentService
            → target_qualified_name = "services.payment.PaymentService"

        import services.payment
            → target_qualified_name = "services.payment"

    The alias_map metadata on the Reference is used to bind the local alias.
    """

    def resolve(
        self,
        import_refs: list[Reference],
        symbol_table: SymbolTable,
        repository_id: str,
        file_path: str,
        import_metadata: dict[str, dict[str, str]] | None = None,
    ) -> list[ResolvedImport]:
        """
        Args:
            import_refs: IMPORT References from the IR.
            symbol_table: Populated SymbolTable.
            repository_id: Owning repository.
            file_path: Path of the importing file (for relative imports).
            import_metadata: Optional mapping of ref.id → alias_map for preserving
                alias information from the Python AST.
        """
        results: list[ResolvedImport] = []
        meta = import_metadata or {}

        for ref in sorted(import_refs, key=lambda r: r.id):
            target_qname = ref.target_qualified_name
            alias_map: dict[str, str] = meta.get(ref.id, {})

            # Determine external status
            root_module = target_qname.lstrip(".").split(".")[0]
            is_external = _is_python_external(root_module)

            # Determine local name: alias first, then simple name
            simple_name = target_qname.split(".")[-1]
            local_name = alias_map.get(simple_name, simple_name)

            if target_qname == "*":
                # from module import * — wildcard
                results.append(
                    ResolvedImport(
                        reference_id=ref.id,
                        local_name="*",
                        target_qualified_name=target_qname,
                        is_wildcard=True,
                        is_external=is_external,
                    )
                )
                continue

            if is_external:
                results.append(
                    ResolvedImport(
                        reference_id=ref.id,
                        local_name=local_name,
                        target_qualified_name=target_qname,
                        is_external=True,
                    )
                )
                continue

            # Try exact qualified-name lookup
            candidates = symbol_table.lookup_by_qualified_name(target_qname, repository_id)

            if len(candidates) == 1:
                results.append(
                    ResolvedImport(
                        reference_id=ref.id,
                        local_name=local_name,
                        target_qualified_name=target_qname,
                        target_symbol_id=candidates[0].symbol_id,
                    )
                )
            elif len(candidates) > 1:
                results.append(
                    ResolvedImport(
                        reference_id=ref.id,
                        local_name=local_name,
                        target_qualified_name=target_qname,
                    )
                )
            else:
                # Not found — try module-level (the module itself may not be in the
                # symbol table but its members are)
                results.append(
                    ResolvedImport(
                        reference_id=ref.id,
                        local_name=local_name,
                        target_qualified_name=target_qname,
                    )
                )

        return results


# ──────────────────────────────────────────────────────────────────────────────
# TypeScript import strategy
# ──────────────────────────────────────────────────────────────────────────────


class _TypeScriptImportStrategy:
    """Resolve TypeScript IMPORT references for a single file.

    TypeScript normalizer produces IMPORT references with target_qualified_name
    of the form:
        named:      "<module_path>.<name>"      e.g. "./payment.PaymentService"
        default:    "<module_path>"             when no named specifiers
        namespace:  recorded as alias in metadata
    """

    def resolve(
        self,
        import_refs: list[Reference],
        symbol_table: SymbolTable,
        repository_id: str,
        file_path: str,
        import_metadata: dict[str, dict[str, str]] | None = None,
    ) -> list[ResolvedImport]:
        """
        Args:
            import_refs: IMPORT References from the IR.
            symbol_table: Populated SymbolTable.
            repository_id: Owning repository.
            file_path: Path of the importing file (for relative path resolution).
            import_metadata: Optional mapping of ref.id → {"alias_map": ...,
                "default_import": ..., "namespace_import": ...}.
        """
        results: list[ResolvedImport] = []
        meta = import_metadata or {}

        for ref in sorted(import_refs, key=lambda r: r.id):
            target_qname = ref.target_qualified_name
            ref_meta: dict[str, str] = meta.get(ref.id, {})

            # Extract module_path from target_qname
            # Normalizer pattern: "module_path.SymbolName" or just "module_path"
            parts = target_qname.rsplit(".", 1)
            if len(parts) == 2:
                module_path_raw, symbol_name = parts[0], parts[1]
            else:
                module_path_raw = target_qname
                symbol_name = ""

            is_relative = module_path_raw.startswith(".")
            is_external = _is_ts_external(module_path_raw)

            if is_external:
                local_name = symbol_name or module_path_raw.split("/")[-1]
                results.append(
                    ResolvedImport(
                        reference_id=ref.id,
                        local_name=local_name,
                        target_qualified_name=target_qname,
                        is_external=True,
                    )
                )
                continue

            if is_relative:
                resolved_module = _resolve_relative_ts_path(file_path, module_path_raw)
            else:
                resolved_module = module_path_raw.replace("/", ".")

            if symbol_name:
                resolved_target = f"{resolved_module}.{symbol_name}"
            else:
                resolved_target = resolved_module

            local_name = ref_meta.get("alias", symbol_name) or resolved_module.split(".")[-1]

            # Exact lookup first
            candidates = symbol_table.lookup_by_qualified_name(resolved_target, repository_id)

            if not candidates and symbol_name:
                # Try suffix lookup for module.SymbolName combinations
                candidates = symbol_table.lookup_by_suffix(symbol_name, repository_id)
                # Filter to those whose qualified name contains the resolved module
                candidates = [
                    c
                    for c in candidates
                    if resolved_module in c.qualified_name or c.qualified_name.endswith(symbol_name)
                ]

            if len(candidates) == 1:
                results.append(
                    ResolvedImport(
                        reference_id=ref.id,
                        local_name=local_name,
                        target_qualified_name=resolved_target,
                        target_symbol_id=candidates[0].symbol_id,
                    )
                )
            elif len(candidates) > 1:
                results.append(
                    ResolvedImport(
                        reference_id=ref.id,
                        local_name=local_name,
                        target_qualified_name=resolved_target,
                    )
                )
            else:
                results.append(
                    ResolvedImport(
                        reference_id=ref.id,
                        local_name=local_name,
                        target_qualified_name=resolved_target,
                    )
                )

        return results


# ──────────────────────────────────────────────────────────────────────────────
# Public ImportResolver
# ──────────────────────────────────────────────────────────────────────────────


class ImportResolver:
    """Language-aware import resolver.

    Processes all IMPORT-kind References in a NormalizationResult and
    populates ``ResolutionContext.resolved_imports`` with the resulting
    alias → qualified-name mappings.

    Usage::

        resolver = ImportResolver()
        resolver.resolve_imports(norm_result, ctx)
        # ctx.resolved_imports now contains the import map for the file

    The import resolver must be called BEFORE the ReferenceResolver so that
    the alias map is available for subsequent reference resolution.
    """

    def __init__(self) -> None:
        self._java = _JavaImportStrategy()
        self._python = _PythonImportStrategy()
        self._typescript = _TypeScriptImportStrategy()

    def resolve_imports(
        self,
        normalization_result: NormalizationResult,
        ctx: ResolutionContext,
        import_metadata: dict[str, dict[str, str]] | None = None,
    ) -> list[ResolvedImport]:
        """Resolve all IMPORT references in the normalization result.

        Mutates ``ctx.resolved_imports`` with the resolved alias map.

        Args:
            normalization_result: Normalized IR output for a single file.
            ctx: Resolution context to mutate with resolved import mappings.
            import_metadata: Optional per-reference alias metadata (e.g. alias_map
                from the parser AST). Keys are Reference IDs.

        Returns:
            List of ResolvedImport records (may include unresolved/external).
        """
        import_refs = [
            r for r in normalization_result.references if r.ref_kind == ReferenceKind.IMPORT
        ]

        if ctx.language == Language.JAVA:
            resolved_list = self._java.resolve(import_refs, ctx.symbol_table, ctx.repository_id)
        elif ctx.language == Language.PYTHON:
            resolved_list = self._python.resolve(
                import_refs,
                ctx.symbol_table,
                ctx.repository_id,
                ctx.file_path,
                import_metadata,
            )
        elif ctx.language == Language.TYPESCRIPT:
            resolved_list = self._typescript.resolve(
                import_refs,
                ctx.symbol_table,
                ctx.repository_id,
                ctx.file_path,
                import_metadata,
            )
        else:
            resolved_list = []

        # Populate the context import map — last writer wins for duplicate locals
        for ri in sorted(resolved_list, key=lambda r: r.reference_id):
            if not ri.is_wildcard and ri.local_name != "*":
                ctx.resolved_imports[ri.local_name] = ri.target_qualified_name

        return resolved_list

    def resolve_imports_from_references(
        self,
        references: list[Reference],
        ctx: ResolutionContext,
        symbol_table: SymbolTable,
        repository_id: str,
        import_metadata: dict[str, dict[str, str]] | None = None,
    ) -> list[ResolvedImport]:
        """Resolve IMPORT references provided directly (without NormalizationResult).

        Useful when operating on raw Reference lists from a pre-populated graph.
        """
        import_refs = [r for r in references if r.ref_kind == ReferenceKind.IMPORT]
        meta = import_metadata or {}

        if ctx.language == Language.JAVA:
            resolved_list = self._java.resolve(import_refs, symbol_table, repository_id)
        elif ctx.language == Language.PYTHON:
            resolved_list = self._python.resolve(
                import_refs, symbol_table, repository_id, ctx.file_path, meta
            )
        elif ctx.language == Language.TYPESCRIPT:
            resolved_list = self._typescript.resolve(
                import_refs, symbol_table, repository_id, ctx.file_path, meta
            )
        else:
            resolved_list = []

        for ri in sorted(resolved_list, key=lambda r: r.reference_id):
            if not ri.is_wildcard and ri.local_name != "*":
                ctx.resolved_imports[ri.local_name] = ri.target_qualified_name

        return resolved_list
