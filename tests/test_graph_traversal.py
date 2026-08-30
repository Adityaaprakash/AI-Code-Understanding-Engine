"""Unit and integration tests for Task 3F Graph Traversal (GraphQueryEngine)."""

import pytest

from code_analyzer.normalization import normalize_parse_result
from code_analyzer.parsers.java import JavaParser
from code_analyzer.parsers.models import Language
from code_analyzer.resolution import (
    ImportResolver,
    ReferenceResolver,
    RelationshipExtractor,
    SymbolTable,
)
from code_analyzer.resolution.context import ResolutionContext
from graph.edges import GraphEdge, generate_edge_id
from graph.enums import EdgeKind, NodeKind
from graph.nodes import GraphNode
from graph.query_engine import GraphQueryEngine
from graph.store import InMemoryGraphStore

REPO_ID = "test-repo-traversal"


@pytest.fixture
def engine() -> GraphQueryEngine:
    """Fixture providing GraphQueryEngine instance."""
    return GraphQueryEngine()


# ──────────────────────────────────────────────────────────────────────────────
# 1. Core Traversal Operations (Callers, Callees, Neighbors)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_direct_callers_and_callees(engine: GraphQueryEngine) -> None:
    """TC-1 & TC-2: Retrieve direct callers and callees using EdgeKind.CALLS strictly."""
    store = InMemoryGraphStore()
    ctrl = GraphNode(id="ctrl", kind=NodeKind.METHOD, name="submit")
    svc = GraphNode(id="svc", kind=NodeKind.METHOD, name="processOrder")
    repo = GraphNode(id="repo", kind=NodeKind.METHOD, name="save")
    store.add_nodes([ctrl, svc, repo])

    e1 = GraphEdge(
        id=generate_edge_id("ctrl", "svc", EdgeKind.CALLS),
        source_id="ctrl",
        target_id="svc",
        kind=EdgeKind.CALLS,
    )
    e2 = GraphEdge(
        id=generate_edge_id("svc", "repo", EdgeKind.CALLS),
        source_id="svc",
        target_id="repo",
        kind=EdgeKind.CALLS,
    )
    # Add non-CALLS edge (USES)
    e3 = GraphEdge(
        id=generate_edge_id("svc", "repo", EdgeKind.USES),
        source_id="svc",
        target_id="repo",
        kind=EdgeKind.USES,
    )
    store.add_edges([e1, e2, e3])

    # Callers of svc (ctrl)
    callers = engine.get_callers("svc", store)
    assert len(callers) == 1
    assert callers[0].id == "ctrl"

    # Callees of svc (repo)
    callees = engine.get_callees("svc", store)
    assert len(callees) == 1
    assert callees[0].id == "repo"


@pytest.mark.unit
def test_inbound_and_outbound_neighbors(engine: GraphQueryEngine) -> None:
    """TC-5 & TC-6 & TC-7: Generic inbound/outbound neighbor retrieval with edge-kind filtering."""
    store = InMemoryGraphStore()
    n1 = GraphNode(id="n1", kind=NodeKind.CLASS, name="A")
    n2 = GraphNode(id="n2", kind=NodeKind.CLASS, name="B")
    n3 = GraphNode(id="n3", kind=NodeKind.INTERFACE, name="C")
    store.add_nodes([n1, n2, n3])

    store.add_edge(
        GraphEdge(
            id=generate_edge_id("n1", "n2", EdgeKind.USES),
            source_id="n1",
            target_id="n2",
            kind=EdgeKind.USES,
        )
    )
    store.add_edge(
        GraphEdge(
            id=generate_edge_id("n1", "n3", EdgeKind.IMPLEMENTS),
            source_id="n1",
            target_id="n3",
            kind=EdgeKind.IMPLEMENTS,
        )
    )

    out_uses = engine.get_outbound_neighbors("n1", store, kind=EdgeKind.USES)
    assert [n.id for n in out_uses] == ["n2"]

    in_uses = engine.get_inbound_neighbors("n2", store, kind=EdgeKind.USES)
    assert [n.id for n in in_uses] == ["n1"]


# ──────────────────────────────────────────────────────────────────────────────
# 2. Dependency Policy & Multi-Hop Traversal
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_direct_and_transitive_dependencies(engine: GraphQueryEngine) -> None:
    """TC-3 & TC-4 & TC-14 & TC-16: Direct and transitive dependencies with depth limiting."""
    store = InMemoryGraphStore()
    a = GraphNode(id="a", kind=NodeKind.CLASS, name="A")
    b = GraphNode(id="b", kind=NodeKind.CLASS, name="B")
    c = GraphNode(id="c", kind=NodeKind.CLASS, name="C")
    d = GraphNode(id="d", kind=NodeKind.CLASS, name="D")
    store.add_nodes([a, b, c, d])

    # Chain: A -> USES -> B -> CALLS -> C -> IMPORTS -> D
    store.add_edge(
        GraphEdge(
            id=generate_edge_id("a", "b", EdgeKind.USES),
            source_id="a",
            target_id="b",
            kind=EdgeKind.USES,
        )
    )
    store.add_edge(
        GraphEdge(
            id=generate_edge_id("b", "c", EdgeKind.CALLS),
            source_id="b",
            target_id="c",
            kind=EdgeKind.CALLS,
        )
    )
    store.add_edge(
        GraphEdge(
            id=generate_edge_id("c", "d", EdgeKind.IMPORTS),
            source_id="c",
            target_id="d",
            kind=EdgeKind.IMPORTS,
        )
    )

    # Structural edge (DECLARES) — should be ignored by dependency policy
    decl_edge = GraphEdge(
        id=generate_edge_id("a", "d", EdgeKind.DECLARES),
        source_id="a",
        target_id="d",
        kind=EdgeKind.DECLARES,
    )
    store.add_edge(decl_edge)

    # Direct dependencies (depth=1)
    dep_d1 = engine.get_dependencies("a", store, max_depth=1)
    assert [n.id for n in dep_d1] == ["b"]

    # Transitive dependencies (depth=2)
    dep_d2 = engine.get_dependencies("a", store, max_depth=2)
    assert {n.id for n in dep_d2} == {"b", "c"}

    # Transitive dependencies (unlimited depth)
    dep_all = engine.get_dependencies("a", store, max_depth=None)
    assert {n.id for n in dep_all} == {"b", "c", "d"}


@pytest.mark.unit
def test_dependents_and_impact_radius(engine: GraphQueryEngine) -> None:
    """TC-4 & TC-15: Direct/transitive dependents and reverse impact radius."""
    store = InMemoryGraphStore()
    core = GraphNode(id="core", kind=NodeKind.CLASS, name="CoreUtil")
    svc = GraphNode(id="svc", kind=NodeKind.CLASS, name="BusinessService")
    ctrl = GraphNode(id="ctrl", kind=NodeKind.CLASS, name="Controller")
    store.add_nodes([core, svc, ctrl])

    # Ctrl -> USES -> Svc -> CALLS -> Core
    store.add_edge(
        GraphEdge(
            id=generate_edge_id("svc", "core", EdgeKind.CALLS),
            source_id="svc",
            target_id="core",
            kind=EdgeKind.CALLS,
        )
    )
    store.add_edge(
        GraphEdge(
            id=generate_edge_id("ctrl", "svc", EdgeKind.USES),
            source_id="ctrl",
            target_id="svc",
            kind=EdgeKind.USES,
        )
    )

    # Direct dependents of core
    dep_d1 = engine.get_dependents("core", store, max_depth=1)
    assert [n.id for n in dep_d1] == ["svc"]

    # Impact radius of core (max_depth=5)
    impact = engine.get_impact_radius("core", store)
    assert {n.id for n in impact} == {"svc", "ctrl"}


# ──────────────────────────────────────────────────────────────────────────────
# 3. Edge Cases: Cycles, Edge Cases & Determinism
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_cyclic_graph_traversal_terminates(engine: GraphQueryEngine) -> None:
    """TC-13 & TC-24: Traversal over cyclic graphs terminates safely without infinite loops."""
    store = InMemoryGraphStore()
    n1 = GraphNode(id="n1", kind=NodeKind.FUNCTION, name="fn1")
    n2 = GraphNode(id="n2", kind=NodeKind.FUNCTION, name="fn2")
    n3 = GraphNode(id="n3", kind=NodeKind.FUNCTION, name="fn3")
    store.add_nodes([n1, n2, n3])

    # Cycle: n1 -> CALLS -> n2 -> CALLS -> n3 -> CALLS -> n1
    store.add_edge(
        GraphEdge(
            id=generate_edge_id("n1", "n2", EdgeKind.CALLS),
            source_id="n1",
            target_id="n2",
            kind=EdgeKind.CALLS,
        )
    )
    store.add_edge(
        GraphEdge(
            id=generate_edge_id("n2", "n3", EdgeKind.CALLS),
            source_id="n2",
            target_id="n3",
            kind=EdgeKind.CALLS,
        )
    )
    store.add_edge(
        GraphEdge(
            id=generate_edge_id("n3", "n1", EdgeKind.CALLS),
            source_id="n3",
            target_id="n1",
            kind=EdgeKind.CALLS,
        )
    )

    deps = engine.get_dependencies("n1", store, max_depth=None)
    assert len(deps) == 2
    assert {n.id for n in deps} == {"n2", "n3"}


@pytest.mark.unit
def test_unknown_and_empty_nodes(engine: GraphQueryEngine) -> None:
    """TC-8 & TC-9 & TC-10 & TC-26: Empty store and unknown node queries return empty lists."""
    store = InMemoryGraphStore()
    assert engine.get_callers("missing", store) == []
    assert engine.get_callees("missing", store) == []
    assert engine.get_dependencies("missing", store) == []
    assert engine.get_dependents("missing", store) == []


@pytest.mark.unit
def test_deterministic_ordering(engine: GraphQueryEngine) -> None:
    """TC-12 & TC-23: Output lists are deterministically ordered."""
    store = InMemoryGraphStore()
    root = GraphNode(id="root", kind=NodeKind.CLASS, name="Root")
    store.add_node(root)

    nodes = [
        GraphNode(id="n-c", kind=NodeKind.CLASS, name="ZClass", qualified_name="com.ZClass"),
        GraphNode(id="n-a", kind=NodeKind.CLASS, name="AClass", qualified_name="com.AClass"),
        GraphNode(id="n-b", kind=NodeKind.METHOD, name="BMethod", qualified_name="com.AClass.b"),
    ]
    store.add_nodes(nodes)

    for n in nodes:
        store.add_edge(
            GraphEdge(
                id=generate_edge_id("root", n.id, EdgeKind.USES),
                source_id="root",
                target_id=n.id,
                kind=EdgeKind.USES,
            )
        )

    res1 = engine.get_dependencies("root", store)
    res2 = engine.get_dependencies("root", store)

    assert [n.id for n in res1] == [n.id for n in res2]
    # Class comes before Method alphabetically by kind value ('class' < 'method')
    # Within 'class', 'com.AClass' comes before 'com.ZClass'
    assert [n.id for n in res1] == ["n-a", "n-c", "n-b"]


# ──────────────────────────────────────────────────────────────────────────────
# 4. Realistic Tiered Graph Test
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_realistic_controller_service_repo_graph(engine: GraphQueryEngine) -> None:
    """Realistic Multi-tier Architecture Graph Test.

    Topology:
        Controller  ──CALLS──>  Service  ──CALLS──>  Repository
                                   │
                                 USES
                                   ▼
                            PaymentService  ──USES──>  Gateway
    """
    store = InMemoryGraphStore()
    ctrl = GraphNode(id="ctrl", kind=NodeKind.CLASS, name="OrderController")
    svc = GraphNode(id="svc", kind=NodeKind.CLASS, name="OrderService")
    repo = GraphNode(id="repo", kind=NodeKind.CLASS, name="OrderRepository")
    pay_svc = GraphNode(id="pay_svc", kind=NodeKind.CLASS, name="PaymentService")
    gtw = GraphNode(id="gtw", kind=NodeKind.CLASS, name="StripeGateway")

    store.add_nodes([ctrl, svc, repo, pay_svc, gtw])

    store.add_edge(
        GraphEdge(
            id=generate_edge_id("ctrl", "svc", EdgeKind.CALLS),
            source_id="ctrl",
            target_id="svc",
            kind=EdgeKind.CALLS,
        )
    )
    store.add_edge(
        GraphEdge(
            id=generate_edge_id("svc", "repo", EdgeKind.CALLS),
            source_id="svc",
            target_id="repo",
            kind=EdgeKind.CALLS,
        )
    )
    store.add_edge(
        GraphEdge(
            id=generate_edge_id("svc", "pay_svc", EdgeKind.USES),
            source_id="svc",
            target_id="pay_svc",
            kind=EdgeKind.USES,
        )
    )
    store.add_edge(
        GraphEdge(
            id=generate_edge_id("pay_svc", "gtw", EdgeKind.USES),
            source_id="pay_svc",
            target_id="gtw",
            kind=EdgeKind.USES,
        )
    )

    # 1. Controller callees
    assert [n.id for n in engine.get_callees("ctrl", store)] == ["svc"]

    # 2. Service callees
    assert [n.id for n in engine.get_callees("svc", store)] == ["repo"]

    # 3. Service direct dependencies (repo, pay_svc)
    svc_deps = engine.get_dependencies("svc", store, max_depth=1)
    assert {n.id for n in svc_deps} == {"repo", "pay_svc"}

    # 4. PaymentService direct dependents (svc)
    assert [n.id for n in engine.get_dependents("pay_svc", store, max_depth=1)] == ["svc"]

    # 5. Gateway dependents (pay_svc direct, svc transitive)
    gtw_dependents = engine.get_dependents("gtw", store, max_depth=None)
    assert {n.id for n in gtw_dependents} == {"pay_svc", "svc", "ctrl"}


# ──────────────────────────────────────────────────────────────────────────────
# 5. Synthetic Large Graph Performance Test
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_synthetic_large_graph_performance(engine: GraphQueryEngine) -> None:
    """TC-27: Synthetic 1,000-node sparse graph performance and termination test."""
    store = InMemoryGraphStore()
    num_nodes = 1000

    # Create 1,000 chain nodes: n0 -> n1 -> n2 ... -> n999
    nodes = [
        GraphNode(id=f"n{i}", kind=NodeKind.FUNCTION, name=f"func_{i}") for i in range(num_nodes)
    ]
    store.add_nodes(nodes)

    for i in range(num_nodes - 1):
        eid = generate_edge_id(f"n{i}", f"n{i + 1}", EdgeKind.CALLS)
        store.add_edge(
            GraphEdge(id=eid, source_id=f"n{i}", target_id=f"n{i + 1}", kind=EdgeKind.CALLS)
        )

    # Direct callee lookup is O(1)
    callees = engine.get_callees("n0", store)
    assert len(callees) == 1
    assert callees[0].id == "n1"

    # Depth-bounded traversal (depth=5)
    deps_d5 = engine.get_dependencies("n0", store, max_depth=5)
    assert len(deps_d5) == 5

    # Full traversal
    deps_all = engine.get_dependencies("n0", store, max_depth=None)
    assert len(deps_all) == 999


# ──────────────────────────────────────────────────────────────────────────────
# 6. End-to-End Pipeline Test (Source Code -> Parse -> IR -> Resolution -> Extractor -> Store -> Traversal)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_end_to_end_pipeline_traversal(engine: GraphQueryEngine) -> None:
    """TC-30: Complete E2E Pipeline Verification.

    Source Code → Parser → Canonical IR → Symbol Table → Reference Resolution → Relationship Extractor → InMemoryGraphStore → GraphQueryEngine.
    """
    parser = JavaParser()

    pay_src = """
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
    ir_pay = normalize_parse_result(parser.parse(pay_src, "payment/PaymentService.java"), REPO_ID)
    ir_order = normalize_parse_result(parser.parse(order_src, "order/OrderService.java"), REPO_ID)

    # 1. Symbol Table Registration
    st = SymbolTable()
    st.register_normalization_result(ir_pay, REPO_ID)
    st.register_normalization_result(ir_order, REPO_ID)

    # 2. Reference Resolution
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

    # 4. Populate GraphStore
    store = InMemoryGraphStore(repository_id=REPO_ID)
    store.add_nodes(nodes_pay + nodes_order)
    store.add_edges(edges_pay + edges_order)

    assert store.node_count > 0
    assert store.edge_count > 0

    # 5. Execute Graph Queries using GraphQueryEngine
    order_svc_node = next(
        n for n in store._nodes.values() if n.name == "OrderService" and n.kind == NodeKind.CLASS
    )
    pay_svc_class_node = next(
        n for n in store._nodes.values() if n.name == "PaymentService" and n.kind == NodeKind.CLASS
    )

    # Outbound edges from OrderService class
    out_edges = engine.get_outbound_edges(order_svc_node.id, store)
    assert len(out_edges) > 0

    # Traverse outbound containment from OrderService
    members = engine.traverse(
        order_svc_node.id, store, direction="outbound", edge_kinds={EdgeKind.DECLARES}
    )
    assert len(members) >= 2  # paymentService field + checkout method
    member_names = {m.name for m in members}
    assert "paymentService" in member_names
    assert "checkout" in member_names

    # Inbound traversal to PaymentService class
    pay_decl = engine.get_inbound_neighbors(pay_svc_class_node.id, store)
    assert len(pay_decl) > 0
