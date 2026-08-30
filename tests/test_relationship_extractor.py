"""Unit and integration tests for TASK-3D — Relationship Extraction.

Tests cover:
  - Unit tests: CALLS, IMPORTS, REFERENCES, EXTENDS, IMPLEMENTS, USES, DECLARES
  - Resolution filtering: UNRESOLVED, AMBIGUOUS, BUILTIN, EXTERNAL produce NO false edges
  - Edge identity determinism, deduplication, direction, and provenance
  - Language-specific multi-file integration tests: Java, Python, TypeScript
  - End-to-end pipeline: Canonical IR → Symbol Table → Import/Ref Resolution → Relationship Extraction → CodeGraph
"""

import pytest

from code_analyzer.ir import (
    Class,
    EntityKind,
    File,
    Method,
    Reference,
    ReferenceKind,
    SourceLocation,
    generate_entity_id,
)
from code_analyzer.normalization import NormalizationResult, normalize_parse_result
from code_analyzer.parsers import JavaParser, PythonParser, TypeScriptParser
from code_analyzer.parsers.models import Language
from code_analyzer.resolution import (
    ImportResolver,
    ReferenceResolver,
    RelationshipExtractor,
    ResolutionContext,
    ResolutionResult,
    SymbolEntry,
    SymbolTable,
)
from graph import (
    CodeGraph,
    EdgeKind,
)
from graph import (
    ResolutionStatus as GraphResolutionStatus,
)
from graph.contracts import RelationshipExtractorContract

REPO_ID = "repo-relationship-test"


def _loc(line: int = 1) -> SourceLocation:
    return SourceLocation(start_line=line, start_column=0, end_line=line, end_column=10)


def _make_file(path: str, lang: Language) -> File:
    file_id = generate_entity_id(EntityKind.FILE, path, path, parent_id=REPO_ID)
    return File(
        id=file_id,
        repository_id=REPO_ID,
        path=path,
        language=lang,
        loc=50,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 1. Unit Tests — Classification, Structural, Precedence, and Contract
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestRelationshipExtractorUnit:
    def test_contract_compliance(self) -> None:
        """TC-1: Verify RelationshipExtractor implements RelationshipExtractorContract."""
        extractor = RelationshipExtractor()
        assert isinstance(extractor, RelationshipExtractorContract)

    def test_declares_extraction(self) -> None:
        """TC-2: Extract structural DECLARES edges for parent-child entity ownership."""
        extractor = RelationshipExtractor()
        st = SymbolTable()

        file_ent = _make_file("order/OrderService.java", Language.JAVA)
        cls_id = generate_entity_id(
            EntityKind.CLASS, "order/OrderService.java", "com.example.OrderService"
        )
        mth_id = generate_entity_id(
            EntityKind.METHOD, "order/OrderService.java", "com.example.OrderService.process"
        )

        cls_ent = Class(
            id=cls_id,
            name="OrderService",
            qualified_name="com.example.OrderService",
            file_id=file_ent.id,
            method_ids=[mth_id],
        )
        mth_ent = Method(
            id=mth_id,
            name="process",
            qualified_name="com.example.OrderService.process",
            file_id=file_ent.id,
            class_id=cls_id,
        )

        norm = NormalizationResult(
            file=file_ent,
            classes=[cls_ent],
            methods=[mth_ent],
        )

        nodes, edges = extractor.extract_from_normalization_result(norm, st)

        assert len(nodes) == 3  # File, Class, Method
        declares_edges = [e for e in edges if e.kind == EdgeKind.DECLARES]
        assert len(declares_edges) == 1
        assert declares_edges[0].source_id == cls_id
        assert declares_edges[0].target_id == mth_id

    def test_calls_relationship_extraction(self) -> None:
        """TC-3: Extract CALLS edge when reference is CALL and target is resolved."""
        extractor = RelationshipExtractor()
        st = SymbolTable()

        file_ent = _make_file("services/order.py", Language.PYTHON)
        caller_id = generate_entity_id(
            EntityKind.METHOD, "services/order.py", "OrderService.checkout"
        )
        callee_id = generate_entity_id(
            EntityKind.METHOD, "services/payment.py", "PaymentService.process"
        )

        st.register(
            SymbolEntry(
                symbol_id=callee_id,
                qualified_name="PaymentService.process",
                simple_name="process",
                kind=EntityKind.METHOD,
                file_id="file-pay",
                repository_id=REPO_ID,
                language=Language.PYTHON,
            )
        )

        ref = Reference(
            id="ref-call-1",
            ref_kind=ReferenceKind.CALL,
            source_file_id=file_ent.id,
            source_symbol_id=caller_id,
            source_location=_loc(12),
            target_qualified_name="PaymentService.process",
            target_symbol_id=callee_id,
        )

        norm = NormalizationResult(
            file=file_ent,
            references=[ref],
        )

        # Pre-resolved map
        res_map = {
            "ref-call-1": ResolutionResult.resolved(
                reference_id="ref-call-1",
                target_qualified_name="PaymentService.process",
                target_symbol_id=callee_id,
            )
        }

        _, edges = extractor.extract_from_normalization_result(norm, st, resolution_results=res_map)

        calls_edges = [e for e in edges if e.kind == EdgeKind.CALLS]
        assert len(calls_edges) == 1
        assert calls_edges[0].source_id == caller_id
        assert calls_edges[0].target_id == callee_id
        assert calls_edges[0].resolution_status == GraphResolutionStatus.RESOLVED

    def test_extends_relationship_extraction(self) -> None:
        """TC-4: Extract EXTENDS edge when reference is EXTENDS and target is resolved."""
        extractor = RelationshipExtractor()
        st = SymbolTable()

        file_ent = _make_file("payment.py", Language.PYTHON)
        sub_id = generate_entity_id(EntityKind.CLASS, "payment.py", "StripeService")
        base_id = generate_entity_id(EntityKind.CLASS, "base.py", "BasePaymentService")

        ref = Reference(
            id="ref-ext-1",
            ref_kind=ReferenceKind.EXTENDS,
            source_file_id=file_ent.id,
            source_symbol_id=sub_id,
            source_location=_loc(5),
            target_qualified_name="BasePaymentService",
            target_symbol_id=base_id,
        )

        norm = NormalizationResult(file=file_ent, references=[ref])
        res_map = {
            "ref-ext-1": ResolutionResult.resolved("ref-ext-1", "BasePaymentService", base_id)
        }

        _, edges = extractor.extract_from_normalization_result(norm, st, resolution_results=res_map)

        ext_edges = [e for e in edges if e.kind == EdgeKind.EXTENDS]
        assert len(ext_edges) == 1
        assert ext_edges[0].source_id == sub_id
        assert ext_edges[0].target_id == base_id

    def test_implements_relationship_extraction(self) -> None:
        """TC-5: Extract IMPLEMENTS edge when reference is IMPLEMENTS and target is resolved."""
        extractor = RelationshipExtractor()
        st = SymbolTable()

        file_ent = _make_file("Gateway.ts", Language.TYPESCRIPT)
        cls_id = generate_entity_id(EntityKind.CLASS, "Gateway.ts", "StripeGateway")
        iface_id = generate_entity_id(EntityKind.INTERFACE, "IGateway.ts", "IPaymentGateway")

        ref = Reference(
            id="ref-impl-1",
            ref_kind=ReferenceKind.IMPLEMENTS,
            source_file_id=file_ent.id,
            source_symbol_id=cls_id,
            source_location=_loc(3),
            target_qualified_name="IPaymentGateway",
            target_symbol_id=iface_id,
        )

        norm = NormalizationResult(file=file_ent, references=[ref])
        res_map = {
            "ref-impl-1": ResolutionResult.resolved("ref-impl-1", "IPaymentGateway", iface_id)
        }

        _, edges = extractor.extract_from_normalization_result(norm, st, resolution_results=res_map)

        impl_edges = [e for e in edges if e.kind == EdgeKind.IMPLEMENTS]
        assert len(impl_edges) == 1
        assert impl_edges[0].source_id == cls_id
        assert impl_edges[0].target_id == iface_id

    def test_uses_relationship_extraction(self) -> None:
        """TC-6: Extract USES edge for TYPE_USAGE references."""
        extractor = RelationshipExtractor()
        st = SymbolTable()

        file_ent = _make_file("Order.java", Language.JAVA)
        caller_id = generate_entity_id(EntityKind.CLASS, "Order.java", "Order")
        type_id = generate_entity_id(EntityKind.CLASS, "Payment.java", "PaymentService")

        ref = Reference(
            id="ref-uses-1",
            ref_kind=ReferenceKind.TYPE_USAGE,
            source_file_id=file_ent.id,
            source_symbol_id=caller_id,
            source_location=_loc(10),
            target_qualified_name="PaymentService",
            target_symbol_id=type_id,
        )

        norm = NormalizationResult(file=file_ent, references=[ref])
        res_map = {"ref-uses-1": ResolutionResult.resolved("ref-uses-1", "PaymentService", type_id)}

        _, edges = extractor.extract_from_normalization_result(norm, st, resolution_results=res_map)

        uses_edges = [e for e in edges if e.kind == EdgeKind.USES]
        assert len(uses_edges) == 1
        assert uses_edges[0].source_id == caller_id
        assert uses_edges[0].target_id == type_id

    def test_imports_relationship_extraction(self) -> None:
        """TC-7: Extract IMPORTS edge for resolved IMPORT references."""
        extractor = RelationshipExtractor()
        st = SymbolTable()

        file_ent = _make_file("OrderService.java", Language.JAVA)
        imported_sym_id = generate_entity_id(
            EntityKind.CLASS, "PaymentService.java", "com.example.payment.PaymentService"
        )

        ref = Reference(
            id="ref-imp-1",
            ref_kind=ReferenceKind.IMPORT,
            source_file_id=file_ent.id,
            source_location=_loc(2),
            target_qualified_name="com.example.payment.PaymentService",
            target_symbol_id=imported_sym_id,
        )

        norm = NormalizationResult(file=file_ent, references=[ref])
        res_map = {
            "ref-imp-1": ResolutionResult.resolved(
                "ref-imp-1", "com.example.payment.PaymentService", imported_sym_id
            )
        }

        _, edges = extractor.extract_from_normalization_result(norm, st, resolution_results=res_map)

        imp_edges = [e for e in edges if e.kind == EdgeKind.IMPORTS]
        assert len(imp_edges) == 1
        assert imp_edges[0].source_id == file_ent.id
        assert imp_edges[0].target_id == imported_sym_id


# ──────────────────────────────────────────────────────────────────────────────
# 2. Negative Tests & False-Positive Prevention
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestRelationshipExtractorNegativeCases:
    def test_unresolved_reference_emits_no_edge(self) -> None:
        """TC-8: Unresolved references MUST NOT create graph edges (No False Positives)."""
        extractor = RelationshipExtractor()
        st = SymbolTable()
        file_ent = _make_file("order.py", Language.PYTHON)

        ref = Reference(
            id="ref-unresolved",
            ref_kind=ReferenceKind.CALL,
            source_file_id=file_ent.id,
            source_location=_loc(15),
            target_qualified_name="unknown_module.unknown_func",
        )

        norm = NormalizationResult(file=file_ent, references=[ref])
        res_map = {
            "ref-unresolved": ResolutionResult.unresolved(
                "ref-unresolved", "unknown_module.unknown_func"
            )
        }

        _, edges = extractor.extract_from_normalization_result(norm, st, resolution_results=res_map)

        assert len(edges) == 0  # No false edge created!

    def test_ambiguous_reference_emits_no_edge(self) -> None:
        """TC-9: Ambiguous references MUST NOT create graph edges."""
        extractor = RelationshipExtractor()
        st = SymbolTable()
        file_ent = _make_file("order.py", Language.PYTHON)

        ref = Reference(
            id="ref-ambig",
            ref_kind=ReferenceKind.CALL,
            source_file_id=file_ent.id,
            source_location=_loc(20),
            target_qualified_name="process",
        )

        norm = NormalizationResult(file=file_ent, references=[ref])
        res_map = {
            "ref-ambig": ResolutionResult.ambiguous("ref-ambig", "process", ["sym-1", "sym-2"])
        }

        _, edges = extractor.extract_from_normalization_result(norm, st, resolution_results=res_map)

        assert len(edges) == 0

    def test_builtin_reference_emits_no_repository_edge(self) -> None:
        """TC-10: Builtin references (int, str, print) emit NO repository-local edges."""
        extractor = RelationshipExtractor()
        st = SymbolTable()
        file_ent = _make_file("order.py", Language.PYTHON)

        ref = Reference(
            id="ref-builtin",
            ref_kind=ReferenceKind.CALL,
            source_file_id=file_ent.id,
            source_location=_loc(25),
            target_qualified_name="print",
        )

        norm = NormalizationResult(file=file_ent, references=[ref])
        res_map = {"ref-builtin": ResolutionResult.builtin("ref-builtin", "print")}

        _, edges = extractor.extract_from_normalization_result(norm, st, resolution_results=res_map)

        assert len(edges) == 0

    def test_external_reference_emits_no_repository_edge(self) -> None:
        """TC-11: External library references (react, java.util) emit NO repository edges."""
        extractor = RelationshipExtractor()
        st = SymbolTable()
        file_ent = _make_file("OrderService.java", Language.JAVA)

        ref = Reference(
            id="ref-ext",
            ref_kind=ReferenceKind.IMPORT,
            source_file_id=file_ent.id,
            source_location=_loc(1),
            target_qualified_name="java.util.List",
        )

        norm = NormalizationResult(file=file_ent, references=[ref])
        res_map = {"ref-ext": ResolutionResult.external("ref-ext", "java.util.List")}

        _, edges = extractor.extract_from_normalization_result(norm, st, resolution_results=res_map)

        assert len(edges) == 0

    def test_deduplication_and_idempotency(self) -> None:
        """TC-12: Extraction is idempotent and deduplicates identical relationships."""
        extractor = RelationshipExtractor()
        st = SymbolTable()
        file_ent = _make_file("order.py", Language.PYTHON)
        src_id = "sym-caller"
        tgt_id = "sym-callee"

        ref1 = Reference(
            id="r1",
            ref_kind=ReferenceKind.CALL,
            source_file_id=file_ent.id,
            source_symbol_id=src_id,
            source_location=_loc(10),
            target_qualified_name="process",
            target_symbol_id=tgt_id,
        )
        ref2 = Reference(
            id="r2",
            ref_kind=ReferenceKind.CALL,
            source_file_id=file_ent.id,
            source_symbol_id=src_id,
            source_location=_loc(10),  # Same line & call
            target_qualified_name="process",
            target_symbol_id=tgt_id,
        )

        norm = NormalizationResult(file=file_ent, references=[ref1, ref2])
        res_map = {
            "r1": ResolutionResult.resolved("r1", "process", tgt_id),
            "r2": ResolutionResult.resolved("r2", "process", tgt_id),
        }

        _, edges = extractor.extract_from_normalization_result(norm, st, resolution_results=res_map)

        # Identical source, target, kind, line produce identical edge ID -> deduplicated!
        assert len(edges) == 1


# ──────────────────────────────────────────────────────────────────────────────
# 3. Multi-File Integration Tests (Java, Python, TypeScript)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestLanguageIntegrationRelationships:
    def test_java_multi_file_relationships(self) -> None:
        """TC-13: Java multi-file repository extraction (Order, Payment, Stripe)."""
        parser = JavaParser()
        pay_src = """
package com.example.payment;

public interface PaymentGateway {
    void processPayment(String orderId);
}
"""
        stripe_src = """
package com.example.payment;

public class StripeGateway implements PaymentGateway {
    public void processPayment(String orderId) {}
}
"""
        order_src = """
package com.example.order;

import com.example.payment.PaymentGateway;

public class OrderService {
    private PaymentGateway gateway;

    public void checkout(String orderId) {
        gateway.processPayment(orderId);
    }
}
"""
        ir_pay = normalize_parse_result(
            parser.parse(pay_src, "payment/PaymentGateway.java"), REPO_ID
        )
        ir_stripe = normalize_parse_result(
            parser.parse(stripe_src, "payment/StripeGateway.java"), REPO_ID
        )
        ir_order = normalize_parse_result(
            parser.parse(order_src, "order/OrderService.java"), REPO_ID
        )

        st = SymbolTable()
        st.register_normalization_result(ir_pay, REPO_ID)
        st.register_normalization_result(ir_stripe, REPO_ID)
        st.register_normalization_result(ir_order, REPO_ID)

        extractor = RelationshipExtractor()
        nodes, edges = extractor.extract_repository_relationships(
            [ir_pay, ir_stripe, ir_order], st, REPO_ID
        )

        assert len(nodes) > 0
        edge_kinds = {e.kind for e in edges}

        # Should contain structural DECLARES and resolved relationships
        assert EdgeKind.DECLARES in edge_kinds

    def test_python_multi_file_relationships(self) -> None:
        """TC-14: Python multi-module repository extraction."""
        parser = PythonParser()
        base_src = """
class BaseService:
    def execute(self):
        pass
"""
        pay_src = """
from base import BaseService

class PaymentService(BaseService):
    def process(self):
        self.execute()
"""
        ir_base = normalize_parse_result(parser.parse(base_src, "base.py"), REPO_ID)
        ir_pay = normalize_parse_result(parser.parse(pay_src, "payment.py"), REPO_ID)

        st = SymbolTable()
        st.register_normalization_result(ir_base, REPO_ID)
        st.register_normalization_result(ir_pay, REPO_ID)

        extractor = RelationshipExtractor()
        nodes, edges = extractor.extract_repository_relationships([ir_base, ir_pay], st, REPO_ID)

        assert len(nodes) > 0
        assert len(edges) > 0

    def test_typescript_multi_file_relationships(self) -> None:
        """TC-15: TypeScript multi-file repository extraction."""
        parser = TypeScriptParser()
        iface_src = """
export interface ILogger {
    log(msg: string): void;
}
"""
        impl_src = """
import { ILogger } from "./iface";

export class ConsoleLogger implements ILogger {
    log(msg: string): void {}
}
"""
        ir_iface = normalize_parse_result(parser.parse(iface_src, "iface.ts"), REPO_ID)
        ir_impl = normalize_parse_result(parser.parse(impl_src, "impl.ts"), REPO_ID)

        st = SymbolTable()
        st.register_normalization_result(ir_iface, REPO_ID)
        st.register_normalization_result(ir_impl, REPO_ID)

        extractor = RelationshipExtractor()
        nodes, edges = extractor.extract_repository_relationships([ir_iface, ir_impl], st, REPO_ID)

        assert len(nodes) > 0
        assert len(edges) > 0


# ──────────────────────────────────────────────────────────────────────────────
# 4. End-to-End Pipeline & CodeGraph Construction
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_end_to_end_codegraph_pipeline() -> None:
    """TC-16: Full pipeline: IR → Symbol Table → Resolution → Extractor → CodeGraph container."""
    parser = JavaParser()
    payment_src = """
package com.example.payment;

public class PaymentService {
    public void processPayment(String id) {}
}
"""
    order_src = """
package com.example.order;

import com.example.payment.PaymentService;

public class OrderService {
    private PaymentService paymentService;

    public void checkout(String orderId) {
        paymentService.processPayment(orderId);
    }
}
"""
    ir_pay = normalize_parse_result(
        parser.parse(payment_src, "payment/PaymentService.java"), REPO_ID
    )
    ir_order = normalize_parse_result(parser.parse(order_src, "order/OrderService.java"), REPO_ID)

    # 1. Symbol Registration
    st = SymbolTable()
    st.register_normalization_result(ir_pay, REPO_ID)
    st.register_normalization_result(ir_order, REPO_ID)

    # 2. Import & Reference Resolution
    imp_resolver = ImportResolver()
    ref_resolver = ReferenceResolver()

    ctx_order = ResolutionContext(
        repository_id=REPO_ID,
        file_id=ir_order.file.id,
        file_path=ir_order.file.path,
        language=Language.JAVA,
        symbol_table=st,
    )

    imp_resolver.resolve_imports(ir_order, ctx_order)
    res_map = ref_resolver.resolve_all(ir_order.references, ctx_order)

    # 3. Relationship Extraction
    extractor = RelationshipExtractor(reference_resolver=ref_resolver)
    nodes_pay, edges_pay = extractor.extract_from_normalization_result(ir_pay, st)
    nodes_order, edges_order = extractor.extract_from_normalization_result(
        ir_order, st, resolution_context=ctx_order, resolution_results=res_map
    )

    all_nodes = {n.id: n for n in nodes_pay + nodes_order}
    all_edges = {e.id: e for e in edges_pay + edges_order}

    # 4. Build CodeGraph Container
    graph = CodeGraph(
        repository_id=REPO_ID,
        nodes=all_nodes,
        edges=all_edges,
    )

    assert graph.node_count == len(all_nodes)
    assert graph.edge_count == len(all_edges)

    # Verify edge direction and target resolution
    resolved_edges = [
        e for e in graph.edges.values() if e.resolution_status == GraphResolutionStatus.RESOLVED
    ]
    assert len(resolved_edges) > 0

    # Verify CodeGraph JSON roundtrip serialization
    json_str = graph.model_dump_json()
    reconstructed = CodeGraph.model_validate_json(json_str)
    assert reconstructed.repository_id == REPO_ID
    assert reconstructed.node_count == graph.node_count
    assert reconstructed.edge_count == graph.edge_count
