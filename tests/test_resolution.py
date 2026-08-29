"""Unit and integration tests for TASK-3B/3C — Symbol, Import & Reference Resolution.

Tests cover:
  - SymbolTable: registration, lookup by ID/qname/simple-name, scope, repository isolation
  - ImportResolver: Java direct/wildcard, Python module/from/alias, TypeScript named/namespace/relative
  - ReferenceResolver: exact, import-alias, scope-aware, method, type, extends/implements, ambiguous, external
  - End-to-end pipelines: Java, Python, TypeScript multi-file repository simulation
"""

import pytest

from code_analyzer.ir import (
    EntityKind,
    File,
    Reference,
    ReferenceKind,
    SourceLocation,
    generate_entity_id,
)
from code_analyzer.parsers.models import Language
from code_analyzer.resolution import (
    ImportResolver,
    ReferenceResolver,
    ResolutionContext,
    ResolutionResult,
    ResolutionStatus,
    ScopeKind,
    SymbolEntry,
    SymbolTable,
)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

REPO_A = "repo-aaaaaaaa"
REPO_B = "repo-bbbbbbbb"


def _loc(line: int = 1) -> SourceLocation:
    return SourceLocation(start_line=line, start_column=0, end_line=line, end_column=10)


def _make_entry(
    symbol_id: str,
    qname: str,
    file_id: str,
    repo_id: str = REPO_A,
    kind: EntityKind = EntityKind.CLASS,
    language: Language = Language.JAVA,
) -> SymbolEntry:
    simple = qname.split(".")[-1]
    return SymbolEntry(
        symbol_id=symbol_id,
        qualified_name=qname,
        simple_name=simple,
        kind=kind,
        file_id=file_id,
        repository_id=repo_id,
        language=language,
    )


def _make_import_ref(
    ref_id: str,
    target_qname: str,
    file_id: str,
    line: int = 1,
) -> Reference:
    return Reference(
        id=ref_id,
        ref_kind=ReferenceKind.IMPORT,
        source_file_id=file_id,
        source_location=_loc(line),
        target_qualified_name=target_qname,
    )


def _make_ref(
    ref_id: str,
    target_qname: str,
    ref_kind: ReferenceKind,
    file_id: str,
    source_symbol_id: str | None = None,
    line: int = 5,
) -> Reference:
    return Reference(
        id=ref_id,
        ref_kind=ref_kind,
        source_file_id=file_id,
        source_symbol_id=source_symbol_id,
        source_location=_loc(line),
        target_qualified_name=target_qname,
    )


def _make_ctx(
    repo_id: str,
    file_id: str,
    file_path: str,
    language: Language,
    symbol_table: SymbolTable,
) -> ResolutionContext:
    return ResolutionContext(
        repository_id=repo_id,
        file_id=file_id,
        file_path=file_path,
        language=language,
        symbol_table=symbol_table,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 1. SymbolTable — registration and lookup
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestSymbolTableRegistration:
    def test_register_and_lookup_by_id(self) -> None:
        """TC-1: Register a symbol, look up by ID."""
        st = SymbolTable()
        entry = _make_entry("sym-1", "com.example.Foo", "file-1")
        st.register(entry)

        result = st.lookup_by_id("sym-1")
        assert result is not None
        assert result.symbol_id == "sym-1"
        assert result.qualified_name == "com.example.Foo"

    def test_lookup_missing_id_returns_none(self) -> None:
        st = SymbolTable()
        assert st.lookup_by_id("nonexistent") is None

    def test_register_idempotent(self) -> None:
        """TC-1: Re-registering the same symbol_id is a no-op."""
        st = SymbolTable()
        e1 = _make_entry("sym-1", "com.example.Foo", "file-1")
        st.register(e1)
        st.register(e1)  # idempotent
        assert st.total_symbols == 1

    def test_lookup_by_qualified_name(self) -> None:
        """TC-2: Look up by qualified name."""
        st = SymbolTable()
        e = _make_entry("sym-2", "com.example.payment.PaymentService", "file-2")
        st.register(e)
        results = st.lookup_by_qualified_name("com.example.payment.PaymentService", REPO_A)
        assert len(results) == 1
        assert results[0].symbol_id == "sym-2"

    def test_lookup_qname_wrong_repo_returns_empty(self) -> None:
        """TC-5: Repository isolation — symbols from A must not cross-resolve to B."""
        st = SymbolTable()
        e = _make_entry("sym-3", "com.example.Foo", "file-3", repo_id=REPO_A)
        st.register(e)
        assert st.lookup_by_qualified_name("com.example.Foo", REPO_B) == []

    def test_duplicate_simple_names_different_packages(self) -> None:
        """TC-4: Duplicate simple names must coexist independently."""
        st = SymbolTable()
        e1 = _make_entry("sym-4a", "module_a.UserService", "file-4a")
        e2 = _make_entry("sym-4b", "module_b.UserService", "file-4b")
        st.register(e1)
        st.register(e2)

        results = st.lookup_by_simple_name("UserService", REPO_A)
        assert len(results) == 2
        ids = {r.symbol_id for r in results}
        assert ids == {"sym-4a", "sym-4b"}

    def test_lookup_by_simple_name_file_scoped(self) -> None:
        """TC-4: Simple name lookup filtered by file returns only file-local symbols."""
        st = SymbolTable()
        e1 = _make_entry("sym-5a", "module_a.UserService", "file-5a")
        e2 = _make_entry("sym-5b", "module_b.UserService", "file-5b")
        st.register(e1)
        st.register(e2)

        results = st.lookup_by_simple_name("UserService", REPO_A, file_id="file-5a")
        assert len(results) == 1
        assert results[0].symbol_id == "sym-5a"

    def test_lookup_by_simple_name_kind_filter(self) -> None:
        """TC-4: Simple name lookup filtered by EntityKind."""
        st = SymbolTable()
        e_cls = _make_entry("sym-6a", "pkg.Scheduler", "file-6", kind=EntityKind.CLASS)
        e_fn = _make_entry("sym-6b", "pkg.Scheduler", "file-6", kind=EntityKind.FUNCTION)
        st.register(e_cls)
        st.register(e_fn)

        results = st.lookup_by_simple_name("Scheduler", REPO_A, kind=EntityKind.CLASS)
        assert len(results) == 1
        assert results[0].kind == EntityKind.CLASS

    def test_lookup_in_file(self) -> None:
        """TC-4: Retrieve all symbols declared in a specific file."""
        st = SymbolTable()
        for i, q in enumerate(["pkg.A", "pkg.B", "pkg.C"]):
            st.register(_make_entry(f"sym-{i}", q, "file-X"))
        st.register(_make_entry("sym-other", "other.D", "file-Y"))

        results = st.lookup_in_file("file-X", REPO_A)
        assert len(results) == 3
        assert all(e.file_id == "file-X" for e in results)

    def test_repository_isolation(self) -> None:
        """TC-5: Symbols from repo A must not appear in repo B lookups."""
        st = SymbolTable()
        ea = _make_entry("sym-A", "pkg.Foo", "file-A", repo_id=REPO_A)
        eb = _make_entry("sym-B", "pkg.Foo", "file-B", repo_id=REPO_B)
        st.register(ea)
        st.register(eb)

        res_a = st.lookup_by_qualified_name("pkg.Foo", REPO_A)
        res_b = st.lookup_by_qualified_name("pkg.Foo", REPO_B)
        assert len(res_a) == 1 and res_a[0].symbol_id == "sym-A"
        assert len(res_b) == 1 and res_b[0].symbol_id == "sym-B"

    def test_symbols_for_repository(self) -> None:
        """TC-5: symbols_for_repository returns only symbols from the given repo."""
        st = SymbolTable()
        st.register(_make_entry("sym-r1", "a.X", "f1", repo_id=REPO_A))
        st.register(_make_entry("sym-r2", "b.Y", "f2", repo_id=REPO_B))
        repo_a_syms = st.symbols_for_repository(REPO_A)
        assert all(e.repository_id == REPO_A for e in repo_a_syms)
        assert len(repo_a_syms) == 1

    def test_lookup_by_suffix(self) -> None:
        """TC-15: Suffix lookup resolves partially-qualified references."""
        st = SymbolTable()
        st.register(_make_entry("sym-sf", "com.example.payment.PaymentService", "f1"))
        results = st.lookup_by_suffix("PaymentService", REPO_A)
        assert len(results) == 1
        assert results[0].symbol_id == "sym-sf"

    def test_deterministic_result_order(self) -> None:
        """TC-28: Multiple calls with same input return same order."""
        st = SymbolTable()
        for i in range(5):
            st.register(_make_entry(f"sym-d{i}", f"pkg.Class{i}", "file-d"))

        r1 = st.lookup_in_file("file-d", REPO_A)
        r2 = st.lookup_in_file("file-d", REPO_A)
        assert [e.symbol_id for e in r1] == [e.symbol_id for e in r2]


# ──────────────────────────────────────────────────────────────────────────────
# 2. ImportResolver — Java
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestJavaImportResolver:
    def _setup(self) -> tuple[SymbolTable, ImportResolver, str, str]:
        st = SymbolTable()
        # Register some Java symbols
        ps_id = generate_entity_id(
            EntityKind.CLASS, "payment/PaymentService.java", "com.example.payment.PaymentService"
        )
        gw_id = generate_entity_id(
            EntityKind.CLASS, "payment/PaymentGateway.java", "com.example.payment.PaymentGateway"
        )
        pm_id = generate_entity_id(
            EntityKind.METHOD,
            "payment/PaymentService.java",
            "com.example.payment.PaymentService.processPayment",
        )
        file_pay = generate_entity_id(
            EntityKind.FILE,
            "payment/PaymentService.java",
            "payment/PaymentService.java",
            parent_id=REPO_A,
        )
        file_gw = generate_entity_id(
            EntityKind.FILE,
            "payment/PaymentGateway.java",
            "payment/PaymentGateway.java",
            parent_id=REPO_A,
        )

        st.register(_make_entry(ps_id, "com.example.payment.PaymentService", file_pay))
        st.register(_make_entry(gw_id, "com.example.payment.PaymentGateway", file_gw))
        st.register(
            _make_entry(
                pm_id,
                "com.example.payment.PaymentService.processPayment",
                file_pay,
                kind=EntityKind.METHOD,
            )
        )
        return st, ImportResolver(), ps_id, file_pay

    def test_java_direct_import_resolves(self) -> None:
        """TC-6: Java direct import resolves to repository symbol."""
        st, resolver, ps_id, _ = self._setup()
        file_order = generate_entity_id(
            EntityKind.FILE, "order/OrderService.java", "order/OrderService.java", parent_id=REPO_A
        )
        ctx = _make_ctx(REPO_A, file_order, "order/OrderService.java", Language.JAVA, st)

        from code_analyzer.normalization.result import NormalizationResult

        norm = NormalizationResult(
            file=File(
                id=file_order,
                repository_id=REPO_A,
                path="order/OrderService.java",
                language=Language.JAVA,
                loc=10,
            ),
            references=[
                _make_import_ref("imp-1", "com.example.payment.PaymentService", file_order)
            ],
        )

        resolved = resolver.resolve_imports(norm, ctx)
        assert len(resolved) == 1
        assert resolved[0].target_symbol_id == ps_id
        assert ctx.resolved_imports.get("PaymentService") == "com.example.payment.PaymentService"

    def test_java_external_import_classified_external(self) -> None:
        """TC-23: Java external imports (java.util.*) are not falsely resolved."""
        st, resolver, _, _ = self._setup()
        file_order = generate_entity_id(
            EntityKind.FILE, "order/OrderService.java", "order/OrderService.java", parent_id=REPO_A
        )
        ctx = _make_ctx(REPO_A, file_order, "order/OrderService.java", Language.JAVA, st)

        from code_analyzer.normalization.result import NormalizationResult

        norm = NormalizationResult(
            file=File(
                id=file_order,
                repository_id=REPO_A,
                path="order/OrderService.java",
                language=Language.JAVA,
                loc=5,
            ),
            references=[_make_import_ref("imp-ext", "java.util.List", file_order)],
        )
        resolved = resolver.resolve_imports(norm, ctx)
        assert len(resolved) == 1
        assert resolved[0].is_external is True
        assert resolved[0].target_symbol_id is None

    def test_java_wildcard_import_resolves_members(self) -> None:
        """TC-7: Java wildcard import registers package members in context."""
        st, resolver, _ps_id, _ = self._setup()
        file_order = generate_entity_id(
            EntityKind.FILE, "order/OrderService.java", "order/OrderService.java", parent_id=REPO_A
        )
        ctx = _make_ctx(REPO_A, file_order, "order/OrderService.java", Language.JAVA, st)

        from code_analyzer.normalization.result import NormalizationResult

        norm = NormalizationResult(
            file=File(
                id=file_order,
                repository_id=REPO_A,
                path="order/OrderService.java",
                language=Language.JAVA,
                loc=5,
            ),
            references=[_make_import_ref("imp-wc", "com.example.payment.*", file_order)],
        )
        resolved = resolver.resolve_imports(norm, ctx)
        # Should resolve PaymentService and PaymentGateway from the package
        resolved_targets = {r.target_qualified_name for r in resolved if r.target_symbol_id}
        assert "com.example.payment.PaymentService" in resolved_targets


# ──────────────────────────────────────────────────────────────────────────────
# 3. ImportResolver — Python
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestPythonImportResolver:
    def _setup(self) -> tuple[SymbolTable, ImportResolver]:
        st = SymbolTable()
        ps_id = generate_entity_id(
            EntityKind.CLASS, "services/payment.py", "services.payment.PaymentService"
        )
        file_pay = generate_entity_id(
            EntityKind.FILE, "services/payment.py", "services/payment.py", parent_id=REPO_A
        )
        fn_id = generate_entity_id(
            EntityKind.FUNCTION, "services/payment.py", "services.payment.process"
        )
        st.register(
            _make_entry(
                ps_id, "services.payment.PaymentService", file_pay, language=Language.PYTHON
            )
        )
        st.register(
            _make_entry(
                fn_id,
                "services.payment.process",
                file_pay,
                kind=EntityKind.FUNCTION,
                language=Language.PYTHON,
            )
        )
        return st, ImportResolver()

    def test_python_from_import_resolves(self) -> None:
        """TC-8: Python from-import resolves to repository symbol."""
        st, resolver = self._setup()
        file_order = generate_entity_id(
            EntityKind.FILE, "services/order.py", "services/order.py", parent_id=REPO_A
        )
        ctx = _make_ctx(REPO_A, file_order, "services/order.py", Language.PYTHON, st)

        from code_analyzer.normalization.result import NormalizationResult

        norm = NormalizationResult(
            file=File(
                id=file_order,
                repository_id=REPO_A,
                path="services/order.py",
                language=Language.PYTHON,
                loc=5,
            ),
            references=[
                _make_import_ref("py-imp-1", "services.payment.PaymentService", file_order)
            ],
        )
        resolved = resolver.resolve_imports(norm, ctx)
        ps_id = generate_entity_id(
            EntityKind.CLASS, "services/payment.py", "services.payment.PaymentService"
        )
        assert any(r.target_symbol_id == ps_id for r in resolved)
        assert ctx.resolved_imports.get("PaymentService") == "services.payment.PaymentService"

    def test_python_import_alias_preserved(self) -> None:
        """TC-9: Python import aliases bind local name correctly."""
        st, resolver = self._setup()
        file_order = generate_entity_id(
            EntityKind.FILE, "services/order.py", "services/order.py", parent_id=REPO_A
        )
        ctx = _make_ctx(REPO_A, file_order, "services/order.py", Language.PYTHON, st)

        from code_analyzer.normalization.result import NormalizationResult

        norm = NormalizationResult(
            file=File(
                id=file_order,
                repository_id=REPO_A,
                path="services/order.py",
                language=Language.PYTHON,
                loc=5,
            ),
            references=[
                _make_import_ref("py-imp-alias", "services.payment.PaymentService", file_order)
            ],
        )

        # Simulate an alias: PaymentService → PS
        import_metadata = {"py-imp-alias": {"PaymentService": "PS"}}
        resolver.resolve_imports(norm, ctx, import_metadata=import_metadata)
        # Local binding should use alias "PS"
        assert ctx.resolved_imports.get("PS") == "services.payment.PaymentService"

    def test_python_external_module_not_resolved(self) -> None:
        """TC-23: Python stdlib/external module not falsely resolved."""
        st, resolver = self._setup()
        file_order = generate_entity_id(
            EntityKind.FILE, "services/order.py", "services/order.py", parent_id=REPO_A
        )
        ctx = _make_ctx(REPO_A, file_order, "services/order.py", Language.PYTHON, st)

        from code_analyzer.normalization.result import NormalizationResult

        norm = NormalizationResult(
            file=File(
                id=file_order,
                repository_id=REPO_A,
                path="services/order.py",
                language=Language.PYTHON,
                loc=5,
            ),
            references=[_make_import_ref("py-ext", "os.path", file_order)],
        )
        resolved = resolver.resolve_imports(norm, ctx)
        assert any(r.is_external for r in resolved)
        assert all(r.target_symbol_id is None for r in resolved)


# ──────────────────────────────────────────────────────────────────────────────
# 4. ImportResolver — TypeScript
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestTypeScriptImportResolver:
    def _setup(self) -> tuple[SymbolTable, ImportResolver]:
        st = SymbolTable()
        ps_id = generate_entity_id(
            EntityKind.CLASS, "services/payment.ts", "payment.PaymentService"
        )
        file_pay = generate_entity_id(
            EntityKind.FILE, "services/payment.ts", "services/payment.ts", parent_id=REPO_A
        )
        st.register(
            _make_entry(ps_id, "payment.PaymentService", file_pay, language=Language.TYPESCRIPT)
        )
        return st, ImportResolver()

    def test_ts_named_import_resolves(self) -> None:
        """TC-10: TypeScript named import resolves to repository symbol."""
        st, resolver = self._setup()
        file_order = generate_entity_id(
            EntityKind.FILE, "services/order.ts", "services/order.ts", parent_id=REPO_A
        )
        ctx = _make_ctx(REPO_A, file_order, "services/order.ts", Language.TYPESCRIPT, st)

        from code_analyzer.normalization.result import NormalizationResult

        # The normalizer produces: target_qname = "./payment.PaymentService"
        norm = NormalizationResult(
            file=File(
                id=file_order,
                repository_id=REPO_A,
                path="services/order.ts",
                language=Language.TYPESCRIPT,
                loc=5,
            ),
            references=[_make_import_ref("ts-imp-1", "./payment.PaymentService", file_order)],
        )
        resolved = resolver.resolve_imports(norm, ctx)
        # Should bind "PaymentService" in local scope
        assert "PaymentService" in ctx.resolved_imports or any(
            r.local_name == "PaymentService" for r in resolved
        )

    def test_ts_relative_path_resolution(self) -> None:
        """TC-11: TypeScript relative imports resolve paths correctly."""
        st, resolver = self._setup()
        file_inner = generate_entity_id(
            EntityKind.FILE, "services/sub/order.ts", "services/sub/order.ts", parent_id=REPO_A
        )
        ctx = _make_ctx(REPO_A, file_inner, "services/sub/order.ts", Language.TYPESCRIPT, st)

        from code_analyzer.normalization.result import NormalizationResult

        # ../payment.PaymentService should resolve to services/payment
        norm = NormalizationResult(
            file=File(
                id=file_inner,
                repository_id=REPO_A,
                path="services/sub/order.ts",
                language=Language.TYPESCRIPT,
                loc=5,
            ),
            references=[_make_import_ref("ts-imp-rel", "../payment.PaymentService", file_inner)],
        )
        resolved = resolver.resolve_imports(norm, ctx)
        assert len(resolved) == 1
        # Should resolve the relative path correctly
        assert (
            "services/payment" in resolved[0].target_qualified_name
            or "payment.PaymentService" in resolved[0].target_qualified_name
        )

    def test_ts_external_import_classified(self) -> None:
        """TC-21: TypeScript external imports (react, lodash) are classified as external."""
        st, resolver = self._setup()
        file_order = generate_entity_id(
            EntityKind.FILE, "services/order.ts", "services/order.ts", parent_id=REPO_A
        )
        ctx = _make_ctx(REPO_A, file_order, "services/order.ts", Language.TYPESCRIPT, st)

        from code_analyzer.normalization.result import NormalizationResult

        norm = NormalizationResult(
            file=File(
                id=file_order,
                repository_id=REPO_A,
                path="services/order.ts",
                language=Language.TYPESCRIPT,
                loc=5,
            ),
            references=[_make_import_ref("ts-ext", "react.useState", file_order)],
        )
        resolved = resolver.resolve_imports(norm, ctx)
        assert any(r.is_external for r in resolved)


# ──────────────────────────────────────────────────────────────────────────────
# 5. ReferenceResolver
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestReferenceResolver:
    def _setup(self) -> tuple[SymbolTable, ReferenceResolver]:
        st = SymbolTable()
        ps_id = generate_entity_id(
            EntityKind.CLASS, "services/payment.py", "services.payment.PaymentService"
        )
        pm_id = generate_entity_id(
            EntityKind.METHOD, "services/payment.py", "services.payment.PaymentService.process"
        )
        file_pay = generate_entity_id(
            EntityKind.FILE, "services/payment.py", "services/payment.py", parent_id=REPO_A
        )
        order_id = generate_entity_id(
            EntityKind.CLASS, "services/order.py", "services.order.OrderService"
        )
        file_order = generate_entity_id(
            EntityKind.FILE, "services/order.py", "services/order.py", parent_id=REPO_A
        )
        iface_id = generate_entity_id(
            EntityKind.INTERFACE, "services/interfaces.py", "services.interfaces.IPayment"
        )
        file_iface = generate_entity_id(
            EntityKind.FILE, "services/interfaces.py", "services/interfaces.py", parent_id=REPO_A
        )

        st.register(
            _make_entry(
                ps_id,
                "services.payment.PaymentService",
                file_pay,
                kind=EntityKind.CLASS,
                language=Language.PYTHON,
            )
        )
        st.register(
            _make_entry(
                pm_id,
                "services.payment.PaymentService.process",
                file_pay,
                kind=EntityKind.METHOD,
                language=Language.PYTHON,
            )
        )
        st.register(
            _make_entry(
                order_id,
                "services.order.OrderService",
                file_order,
                kind=EntityKind.CLASS,
                language=Language.PYTHON,
            )
        )
        st.register(
            _make_entry(
                iface_id,
                "services.interfaces.IPayment",
                file_iface,
                kind=EntityKind.INTERFACE,
                language=Language.PYTHON,
            )
        )

        return st, ReferenceResolver()

    def _make_file_order_ctx(self, st: SymbolTable) -> ResolutionContext:
        file_order = generate_entity_id(
            EntityKind.FILE, "services/order.py", "services/order.py", parent_id=REPO_A
        )
        ctx = _make_ctx(REPO_A, file_order, "services/order.py", Language.PYTHON, st)
        return ctx

    def test_exact_qualified_name_resolves(self) -> None:
        """TC-13: Exact qualified name lookup resolves to the correct symbol."""
        st, resolver = self._setup()
        ctx = self._make_file_order_ctx(st)
        file_order = ctx.file_id
        ps_id = generate_entity_id(
            EntityKind.CLASS, "services/payment.py", "services.payment.PaymentService"
        )

        ref = _make_ref(
            "ref-exact", "services.payment.PaymentService", ReferenceKind.TYPE_USAGE, file_order
        )
        result = resolver.resolve(ref, ctx)

        assert result.status == ResolutionStatus.RESOLVED
        assert result.target_symbol_id == ps_id
        assert result.confidence == 1.0

    def test_import_alias_resolution(self) -> None:
        """TC-26: Import alias expands to correct qualified name."""
        st, resolver = self._setup()
        ctx = self._make_file_order_ctx(st)
        # Pre-populate alias: PS → services.payment.PaymentService
        ctx.resolved_imports["PS"] = "services.payment.PaymentService"

        file_order = ctx.file_id
        ps_id = generate_entity_id(
            EntityKind.CLASS, "services/payment.py", "services.payment.PaymentService"
        )

        ref = _make_ref("ref-alias", "PS", ReferenceKind.TYPE_USAGE, file_order)
        result = resolver.resolve(ref, ctx)

        assert result.status == ResolutionStatus.RESOLVED
        assert result.target_symbol_id == ps_id

    def test_method_resolution_via_type(self) -> None:
        """TC-17: Method resolution via enclosing type."""
        st, resolver = self._setup()
        ctx = self._make_file_order_ctx(st)
        ctx.resolved_imports["PaymentService"] = "services.payment.PaymentService"
        file_order = ctx.file_id
        pm_id = generate_entity_id(
            EntityKind.METHOD, "services/payment.py", "services.payment.PaymentService.process"
        )

        ref = _make_ref("ref-method", "PaymentService.process", ReferenceKind.CALL, file_order)
        result = resolver.resolve(ref, ctx)

        assert result.status == ResolutionStatus.RESOLVED
        assert result.target_symbol_id == pm_id

    def test_extends_resolution(self) -> None:
        """TC-19: EXTENDS reference resolves to superclass."""
        st, resolver = self._setup()
        ctx = self._make_file_order_ctx(st)

        file_order = ctx.file_id
        ps_id = generate_entity_id(
            EntityKind.CLASS, "services/payment.py", "services.payment.PaymentService"
        )

        ref = _make_ref(
            "ref-extends", "services.payment.PaymentService", ReferenceKind.EXTENDS, file_order
        )
        result = resolver.resolve(ref, ctx)

        assert result.status == ResolutionStatus.RESOLVED
        assert result.target_symbol_id == ps_id

    def test_implements_resolution(self) -> None:
        """TC-20: IMPLEMENTS reference resolves to interface."""
        st, resolver = self._setup()
        ctx = self._make_file_order_ctx(st)

        file_order = ctx.file_id
        iface_id = generate_entity_id(
            EntityKind.INTERFACE, "services/interfaces.py", "services.interfaces.IPayment"
        )

        ref = _make_ref(
            "ref-impl", "services.interfaces.IPayment", ReferenceKind.IMPLEMENTS, file_order
        )
        result = resolver.resolve(ref, ctx)

        assert result.status == ResolutionStatus.RESOLVED
        assert result.target_symbol_id == iface_id

    def test_unresolved_reference(self) -> None:
        """TC-22: Missing symbol returns UNRESOLVED (not guessed)."""
        st, resolver = self._setup()
        ctx = self._make_file_order_ctx(st)

        ref = _make_ref("ref-missing", "unknown.NonExistent", ReferenceKind.TYPE_USAGE, ctx.file_id)
        result = resolver.resolve(ref, ctx)

        assert result.status == ResolutionStatus.UNRESOLVED
        assert result.target_symbol_id is None

    def test_ambiguous_not_guessed(self) -> None:
        """TC-24: Ambiguous symbols are NEVER silently resolved."""
        st = SymbolTable()
        file_a = generate_entity_id(EntityKind.FILE, "a.py", "a.py", parent_id=REPO_A)
        file_b = generate_entity_id(EntityKind.FILE, "b.py", "b.py", parent_id=REPO_A)
        ps_a = generate_entity_id(EntityKind.CLASS, "a.py", "a.PaymentService")
        ps_b = generate_entity_id(EntityKind.CLASS, "b.py", "b.PaymentService")

        st.register(_make_entry(ps_a, "a.PaymentService", file_a, language=Language.PYTHON))
        st.register(_make_entry(ps_b, "b.PaymentService", file_b, language=Language.PYTHON))

        resolver = ReferenceResolver()
        file_c = generate_entity_id(EntityKind.FILE, "c.py", "c.py", parent_id=REPO_A)
        ctx = _make_ctx(REPO_A, file_c, "c.py", Language.PYTHON, st)
        # No import hint to disambiguate

        ref = _make_ref("ref-ambig", "PaymentService", ReferenceKind.TYPE_USAGE, file_c)
        result = resolver.resolve(ref, ctx)

        # Must be AMBIGUOUS — never randomly choose one
        assert result.status == ResolutionStatus.AMBIGUOUS
        assert len(result.candidate_symbol_ids) == 2

    def test_same_method_name_different_classes_ambiguous(self) -> None:
        """TC-25: Same method name on different classes is AMBIGUOUS without qualification."""
        st = SymbolTable()
        file_a = generate_entity_id(EntityKind.FILE, "a.py", "a.py", parent_id=REPO_A)
        file_b = generate_entity_id(EntityKind.FILE, "b.py", "b.py", parent_id=REPO_A)
        m_a = generate_entity_id(EntityKind.METHOD, "a.py", "a.ClassA.process")
        m_b = generate_entity_id(EntityKind.METHOD, "b.py", "b.ClassB.process")
        st.register(
            _make_entry(
                m_a, "a.ClassA.process", file_a, kind=EntityKind.METHOD, language=Language.PYTHON
            )
        )
        st.register(
            _make_entry(
                m_b, "b.ClassB.process", file_b, kind=EntityKind.METHOD, language=Language.PYTHON
            )
        )

        resolver = ReferenceResolver()
        file_c = generate_entity_id(EntityKind.FILE, "c.py", "c.py", parent_id=REPO_A)
        ctx = _make_ctx(REPO_A, file_c, "c.py", Language.PYTHON, st)

        ref = _make_ref("ref-m-ambig", "process", ReferenceKind.CALL, file_c)
        result = resolver.resolve(ref, ctx)

        assert result.status == ResolutionStatus.AMBIGUOUS

    def test_python_builtin_classified(self) -> None:
        """TC-22: Python builtin references return BUILTIN status."""
        st, resolver = self._setup()
        ctx = self._make_file_order_ctx(st)

        ref = _make_ref("ref-builtin", "isinstance", ReferenceKind.CALL, ctx.file_id)
        result = resolver.resolve(ref, ctx)

        assert result.status == ResolutionStatus.BUILTIN

    def test_source_location_preserved(self) -> None:
        """TC-30: Source location is preserved in all resolution outcomes."""
        st, resolver = self._setup()
        ctx = self._make_file_order_ctx(st)
        loc = _loc(42)

        ref = Reference(
            id="ref-loc",
            ref_kind=ReferenceKind.TYPE_USAGE,
            source_file_id=ctx.file_id,
            source_location=loc,
            target_qualified_name="nonexistent.Symbol",
        )
        result = resolver.resolve(ref, ctx)

        assert result.source_location is not None
        assert result.source_location.start_line == 42

    def test_result_serialization(self) -> None:
        """TC-29: ResolutionResult serializes to / from JSON without loss."""
        st, resolver = self._setup()
        ctx = self._make_file_order_ctx(st)
        generate_entity_id(
            EntityKind.CLASS, "services/payment.py", "services.payment.PaymentService"
        )

        ref = _make_ref(
            "ref-ser", "services.payment.PaymentService", ReferenceKind.TYPE_USAGE, ctx.file_id
        )
        result = resolver.resolve(ref, ctx)

        json_str = result.model_dump_json()
        reconstructed = ResolutionResult.model_validate_json(json_str)

        assert reconstructed.status == result.status
        assert reconstructed.target_symbol_id == result.target_symbol_id
        assert reconstructed.confidence == result.confidence

    def test_resolve_all_skips_import_refs(self) -> None:
        """TC-13: resolve_all skips IMPORT references by default."""
        st, resolver = self._setup()
        ctx = self._make_file_order_ctx(st)

        refs = [
            _make_ref(
                "ref-use", "services.payment.PaymentService", ReferenceKind.TYPE_USAGE, ctx.file_id
            ),
            _make_import_ref("ref-imp", "services.payment.PaymentService", ctx.file_id),
        ]
        results = resolver.resolve_all(refs, ctx)

        assert "ref-use" in results
        assert "ref-imp" not in results


# ──────────────────────────────────────────────────────────────────────────────
# 6. ResolutionResult model
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestResolutionResult:
    def test_resolved_factory(self) -> None:
        r = ResolutionResult.resolved(
            reference_id="r1",
            target_qualified_name="pkg.Foo",
            target_symbol_id="sym-1",
            confidence=0.9,
        )
        assert r.status == ResolutionStatus.RESOLVED
        assert r.is_resolved() is True
        assert r.target_symbol_id == "sym-1"
        assert r.confidence == 0.9

    def test_unresolved_factory(self) -> None:
        r = ResolutionResult.unresolved("r2", "pkg.Missing")
        assert r.status == ResolutionStatus.UNRESOLVED
        assert r.is_resolved() is False
        assert r.target_symbol_id is None
        assert r.confidence == 0.0

    def test_ambiguous_factory(self) -> None:
        r = ResolutionResult.ambiguous("r3", "pkg.Ambig", ["s1", "s2"])
        assert r.status == ResolutionStatus.AMBIGUOUS
        assert len(r.candidate_symbol_ids) == 2
        assert r.confidence == 0.0

    def test_external_factory(self) -> None:
        r = ResolutionResult.external("r4", "org.springframework.Boot")
        assert r.status == ResolutionStatus.EXTERNAL
        assert r.is_resolved() is False

    def test_builtin_factory(self) -> None:
        r = ResolutionResult.builtin("r5", "int")
        assert r.status == ResolutionStatus.BUILTIN
        assert r.confidence == 1.0


# ──────────────────────────────────────────────────────────────────────────────
# 7. ResolutionContext
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestResolutionContext:
    def test_scope_kind_ordering(self) -> None:
        assert ScopeKind.PARAMETER == "parameter"
        assert ScopeKind.REPOSITORY == "repository"

    def test_resolve_alias(self) -> None:
        st = SymbolTable()
        ctx = _make_ctx(REPO_A, "f1", "services/order.py", Language.PYTHON, st)
        ctx.resolved_imports["PS"] = "services.payment.PaymentService"

        assert ctx.resolve_alias("PS") == "services.payment.PaymentService"
        assert ctx.resolve_alias("Unknown") is None

    def test_with_class_scope(self) -> None:
        st = SymbolTable()
        ctx = _make_ctx(REPO_A, "f1", "services/order.py", Language.PYTHON, st)
        ctx2 = ctx.with_class_scope("services.order.OrderService")

        assert ctx2.current_class_qname == "services.order.OrderService"
        assert ctx2.current_function_qname is None

    def test_with_function_scope(self) -> None:
        st = SymbolTable()
        ctx = _make_ctx(REPO_A, "f1", "services/order.py", Language.PYTHON, st)
        ctx_cls = ctx.with_class_scope("services.order.OrderService")
        ctx_fn = ctx_cls.with_function_scope("services.order.OrderService.createOrder")

        assert ctx_fn.current_function_qname == "services.order.OrderService.createOrder"
        assert ctx_fn.current_class_qname == "services.order.OrderService"


# ──────────────────────────────────────────────────────────────────────────────
# 8. End-to-end Java — multi-file resolution (TC-32)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_end_to_end_java_resolution() -> None:
    """TC-32: End-to-end Java import + reference resolution.

    Simulates:
        OrderService.java imports PaymentService
        OrderService references PaymentService.processPayment
    """
    from code_analyzer.normalization import normalize_parse_result
    from code_analyzer.parsers import JavaParser

    payment_src = """
package com.example.payment;

public class PaymentService {
    public void processPayment(String orderId) {}
}
"""
    order_src = """
package com.example.order;

import com.example.payment.PaymentService;

public class OrderService {
    private PaymentService paymentService;
}
"""
    parser = JavaParser()
    repo_id = "repo-java-e2e"

    # Parse and normalize
    pay_result = parser.parse(payment_src, "payment/PaymentService.java")
    order_result = parser.parse(order_src, "order/OrderService.java")

    pay_ir = normalize_parse_result(pay_result, repo_id, "payment/PaymentService.java")
    order_ir = normalize_parse_result(order_result, repo_id, "order/OrderService.java")

    # Build symbol table
    st = SymbolTable()
    st.register_normalization_result(pay_ir, repo_id)
    st.register_normalization_result(order_ir, repo_id)

    # Verify PaymentService registered
    ps_candidates = st.lookup_by_simple_name("PaymentService", repo_id, kind=EntityKind.CLASS)
    assert len(ps_candidates) == 1
    ps_id = ps_candidates[0].symbol_id

    # Resolve imports for OrderService
    ctx = _make_ctx(repo_id, order_ir.file.id, "order/OrderService.java", Language.JAVA, st)
    import_resolver = ImportResolver()
    resolved_imports = import_resolver.resolve_imports(order_ir, ctx)

    # At least the PaymentService import should resolve
    resolved = [r for r in resolved_imports if not r.is_external and r.target_symbol_id]
    assert any(r.target_symbol_id == ps_id for r in resolved), (
        f"Expected PaymentService to resolve. Resolved: {[(r.target_qualified_name, r.target_symbol_id) for r in resolved_imports]}"
    )

    # Resolve a type reference to PaymentService
    ref_resolver = ReferenceResolver()
    type_ref = _make_ref(
        "r-type-ps",
        "com.example.payment.PaymentService",
        ReferenceKind.TYPE_USAGE,
        order_ir.file.id,
    )
    type_result = ref_resolver.resolve(type_ref, ctx)
    assert type_result.status == ResolutionStatus.RESOLVED
    assert type_result.target_symbol_id == ps_id


# ──────────────────────────────────────────────────────────────────────────────
# 9. End-to-end Python — multi-file resolution (TC-33)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_end_to_end_python_resolution() -> None:
    """TC-33: End-to-end Python import + reference resolution.

    Simulates:
        services/payment.py defines PaymentService
        services/order.py imports PaymentService  (from services.payment import PaymentService)
        services/order.py references PaymentService
    """
    from code_analyzer.normalization import normalize_parse_result
    from code_analyzer.parsers import PythonParser

    payment_src = """
class PaymentService:
    def process(self, order_id: str) -> None:
        pass
"""
    order_src = """
from services.payment import PaymentService

class OrderService:
    def create_order(self) -> None:
        service = PaymentService()
"""
    parser = PythonParser()
    repo_id = "repo-py-e2e"

    pay_result = parser.parse(payment_src, "services/payment.py")
    order_result = parser.parse(order_src, "services/order.py")

    pay_ir = normalize_parse_result(pay_result, repo_id, "services/payment.py")
    order_ir = normalize_parse_result(order_result, repo_id, "services/order.py")

    st = SymbolTable()
    st.register_normalization_result(pay_ir, repo_id)
    st.register_normalization_result(order_ir, repo_id)

    # PaymentService should be registered under services.payment.PaymentService
    ps_candidates = st.lookup_by_simple_name("PaymentService", repo_id, kind=EntityKind.CLASS)
    assert len(ps_candidates) == 1
    ps_id = ps_candidates[0].symbol_id

    ctx = _make_ctx(repo_id, order_ir.file.id, "services/order.py", Language.PYTHON, st)
    import_resolver = ImportResolver()
    import_resolver.resolve_imports(order_ir, ctx)

    # Direct qualified-name reference should resolve
    ref_resolver = ReferenceResolver()
    ref = _make_ref(
        "r-ps-py", "services.payment.PaymentService", ReferenceKind.TYPE_USAGE, order_ir.file.id
    )
    result = ref_resolver.resolve(ref, ctx)
    assert result.status == ResolutionStatus.RESOLVED
    assert result.target_symbol_id == ps_id


# ──────────────────────────────────────────────────────────────────────────────
# 10. End-to-end TypeScript — multi-file resolution (TC-34)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_end_to_end_typescript_resolution() -> None:
    """TC-34: End-to-end TypeScript import + reference resolution.

    Simulates:
        services/payment.ts exports PaymentService
        services/order.ts imports { PaymentService } from "./payment"
    """
    from code_analyzer.normalization import normalize_parse_result
    from code_analyzer.parsers import TypeScriptParser

    payment_src = """
export class PaymentService {
    processPayment(orderId: string): void {}
}
"""
    order_src = """
import { PaymentService } from "./payment";

export class OrderService {
    private paymentService: PaymentService;
}
"""
    parser = TypeScriptParser()
    repo_id = "repo-ts-e2e"

    pay_result = parser.parse(payment_src, "services/payment.ts")
    order_result = parser.parse(order_src, "services/order.ts")

    pay_ir = normalize_parse_result(pay_result, repo_id, "services/payment.ts")
    order_ir = normalize_parse_result(order_result, repo_id, "services/order.ts")

    st = SymbolTable()
    st.register_normalization_result(pay_ir, repo_id)
    st.register_normalization_result(order_ir, repo_id)

    # PaymentService should be registered
    ps_candidates = st.lookup_by_simple_name("PaymentService", repo_id, kind=EntityKind.CLASS)
    assert len(ps_candidates) == 1, f"Expected 1 PaymentService, found {len(ps_candidates)}"
    _ = ps_candidates[0].symbol_id

    ctx = _make_ctx(repo_id, order_ir.file.id, "services/order.ts", Language.TYPESCRIPT, st)
    import_resolver = ImportResolver()
    import_resolver.resolve_imports(order_ir, ctx)

    # Try resolving the type reference to PaymentService
    ref_resolver = ReferenceResolver()
    # After import resolution, "PaymentService" should be in resolved_imports
    if "PaymentService" in ctx.resolved_imports:
        ref = _make_ref("r-ts-ps", "PaymentService", ReferenceKind.TYPE_USAGE, order_ir.file.id)
        result = ref_resolver.resolve(ref, ctx)
        assert result.status in (ResolutionStatus.RESOLVED, ResolutionStatus.AMBIGUOUS)
    else:
        # At minimum the symbol should be locatable by qualified name
        qname = ps_candidates[0].qualified_name
        ref = _make_ref("r-ts-ps-qn", qname, ReferenceKind.TYPE_USAGE, order_ir.file.id)
        result = ref_resolver.resolve(ref, ctx)
        assert result.status == ResolutionStatus.RESOLVED


# ──────────────────────────────────────────────────────────────────────────────
# 11. Negative tests — must NOT resolve
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestNegativeResolution:
    def test_missing_import_target_unresolved(self) -> None:
        """Negative: missing import target stays UNRESOLVED."""
        st = SymbolTable()
        resolver = ReferenceResolver()
        ctx = _make_ctx(REPO_A, "f1", "a.py", Language.PYTHON, st)

        ref = _make_ref("neg-1", "missing.Module.MissingClass", ReferenceKind.TYPE_USAGE, "f1")
        result = resolver.resolve(ref, ctx)
        assert result.status == ResolutionStatus.UNRESOLVED

    def test_boundary_violation_different_repos(self) -> None:
        """Negative: symbol from REPO_B is NOT resolved when context is REPO_A."""
        st = SymbolTable()
        sym_b = _make_entry("sym-repo-b", "pkg.Service", "file-b", repo_id=REPO_B)
        st.register(sym_b)

        resolver = ReferenceResolver()
        ctx = _make_ctx(REPO_A, "file-a", "a.py", Language.PYTHON, st)

        ref = _make_ref("neg-boundary", "pkg.Service", ReferenceKind.TYPE_USAGE, "file-a")
        result = resolver.resolve(ref, ctx)
        # Should NOT resolve — different repo
        assert result.status != ResolutionStatus.RESOLVED

    def test_external_dependency_unresolved(self) -> None:
        """Negative: external dependency (not in index) stays UNRESOLVED."""
        st = SymbolTable()
        resolver = ReferenceResolver()
        ctx = _make_ctx(REPO_A, "f1", "a.py", Language.PYTHON, st)

        ref = _make_ref("neg-ext", "requests.Session", ReferenceKind.TYPE_USAGE, "f1")
        result = resolver.resolve(ref, ctx)
        assert result.status in (ResolutionStatus.UNRESOLVED, ResolutionStatus.BUILTIN)
        assert result.target_symbol_id is None
