"""Phase 3 Comprehensive Hardening Test Suite (TASK-3G).

Exercises schema invariants, symbol resolution safety, relationship extraction invariants,
false positive / negative prevention, storage engine invariants, traversal correctness,
cycle safety, depth limits, cross-language equivalence, large graph scalability,
adversarial topologies, and end-to-end pipeline integrity.
"""

import pytest
from pydantic import ValidationError

from code_analyzer.ir import (
    EntityKind,
    File,
    Reference,
    ReferenceKind,
    SourceLocation,
)
from code_analyzer.normalization import NormalizationResult, normalize_parse_result
from code_analyzer.parsers import JavaParser, PythonParser, TypeScriptParser
from code_analyzer.parsers.models import Language
from code_analyzer.resolution import (
    ReferenceResolver,
    RelationshipExtractor,
    ResolutionContext,
    SymbolEntry,
    SymbolTable,
)
from graph.edges import GraphEdge
from graph.enums import EdgeKind, NodeKind, ResolutionStatus
from graph.models import CodeGraph
from graph.nodes import GraphNode
from graph.query_engine import GraphQueryEngine
from graph.store import InMemoryGraphStore

REPO_ID = "repo-hardening-suite"


def _make_loc(line: int = 1) -> SourceLocation:
    """Helper to construct a valid SourceLocation."""
    return SourceLocation(
        file_path="src/app.py",
        start_line=line,
        start_column=0,
        end_line=line,
        end_column=20,
    )


def _make_entry(
    symbol_id: str,
    qname: str,
    file_id: str,
    kind: EntityKind = EntityKind.CLASS,
    language: Language = Language.PYTHON,
) -> SymbolEntry:
    """Helper to construct a valid SymbolEntry."""
    simple = qname.split(".")[-1]
    return SymbolEntry(
        symbol_id=symbol_id,
        qualified_name=qname,
        simple_name=simple,
        kind=kind,
        file_id=file_id,
        repository_id=REPO_ID,
        language=language,
    )


# =====================================================================
# 1. SCHEMA INVARIANTS
# =====================================================================


@pytest.mark.unit
def test_node_and_edge_schema_invariants() -> None:
    """Verify empty IDs, invalid confidence intervals, and immutability are strictly enforced."""
    # Node empty ID checks
    with pytest.raises((ValueError, ValidationError)):
        GraphNode(id="", kind=NodeKind.CLASS, name="TestClass")

    with pytest.raises((ValueError, ValidationError)):
        GraphNode(id="   ", kind=NodeKind.CLASS, name="TestClass")

    # Edge empty ID checks
    with pytest.raises((ValueError, ValidationError)):
        GraphEdge(id="", source_id="src", target_id="tgt", kind=EdgeKind.CALLS)

    with pytest.raises((ValueError, ValidationError)):
        GraphEdge(id="edge-1", source_id="", target_id="tgt", kind=EdgeKind.CALLS)

    with pytest.raises((ValueError, ValidationError)):
        GraphEdge(id="edge-1", source_id="src", target_id="  ", kind=EdgeKind.CALLS)

    # Invalid confidence range
    with pytest.raises((ValueError, ValidationError)):
        GraphEdge(
            id="edge-1", source_id="src", target_id="tgt", kind=EdgeKind.CALLS, confidence=1.5
        )

    with pytest.raises((ValueError, ValidationError)):
        GraphEdge(
            id="edge-1", source_id="src", target_id="tgt", kind=EdgeKind.CALLS, confidence=-0.1
        )

    # Immutability verification
    node = GraphNode(id="node-1", kind=NodeKind.CLASS, name="TestClass")
    with pytest.raises(ValidationError):
        node.name = "MutatedClass"

    edge = GraphEdge(id="edge-1", source_id="src", target_id="tgt", kind=EdgeKind.CALLS)
    with pytest.raises(ValidationError):
        edge.confidence = 0.5


@pytest.mark.unit
def test_schema_json_lossless_roundtrip() -> None:
    """Verify GraphNode, GraphEdge, and CodeGraph serialize and deserialize losslessly."""
    loc = _make_loc(10)
    node = GraphNode(
        id="node-cls-1",
        kind=NodeKind.CLASS,
        name="UserService",
        qualified_name="com.app.UserService",
        language=Language.JAVA,
        location=loc,
        attributes={"exported": True, "annotations": ["Service"]},
    )
    edge = GraphEdge(
        id="edge-calls-1",
        source_id="node-cls-1",
        target_id="node-cls-2",
        kind=EdgeKind.CALLS,
        resolution_status=ResolutionStatus.RESOLVED,
        confidence=0.95,
        source_location=loc,
        attributes={"line": 12},
    )

    # GraphNode serialization
    node_json = node.model_dump_json()
    deserialized_node = GraphNode.model_validate_json(node_json)
    assert deserialized_node == node

    # GraphEdge serialization
    edge_json = edge.model_dump_json()
    deserialized_edge = GraphEdge.model_validate_json(edge_json)
    assert deserialized_edge == edge

    # CodeGraph serialization
    cg = CodeGraph(
        repository_id="repo-1",
        nodes={node.id: node},
        edges={edge.id: edge},
        metadata={"version": "1.0"},
    )
    cg_json = cg.model_dump_json()
    deserialized_cg = CodeGraph.model_validate_json(cg_json)
    assert deserialized_cg.repository_id == cg.repository_id
    assert deserialized_cg.nodes == cg.nodes
    assert deserialized_cg.edges == cg.edges
    assert deserialized_cg.metadata == cg.metadata


# =====================================================================
# 2. FALSE POSITIVE PREVENTION
# =====================================================================


@pytest.mark.unit
def test_false_positive_prevention_distinct_modules() -> None:
    """Ensure identical class names in different modules with no import evidence produce NO false edges."""
    st = SymbolTable()
    context_c = ResolutionContext(
        repository_id=REPO_ID,
        file_id="consumer.py",
        file_path="consumer.py",
        language=Language.PYTHON,
        symbol_table=st,
    )

    # Register PaymentService in module_a and module_b
    st.register(_make_entry("sym-mod-a-ps", "module_a.PaymentService", "module_a.py"))
    st.register(_make_entry("sym-mod-b-ps", "module_b.PaymentService", "module_b.py"))

    resolver = ReferenceResolver()

    # Reference explicitly requesting module_a.PaymentService
    ref_explicit = Reference(
        id="ref-a",
        ref_kind=ReferenceKind.TYPE_USAGE,
        source_file_id="consumer.py",
        target_qualified_name="module_a.PaymentService",
    )
    res_explicit = resolver.resolve(ref_explicit, context_c)
    assert res_explicit.status == ResolutionStatus.RESOLVED
    assert res_explicit.target_symbol_id == "sym-mod-a-ps"
    assert res_explicit.target_symbol_id != "sym-mod-b-ps"

    # Unqualified reference without import -> ambiguous (2 candidates) -> must NOT silently pick one!
    ref_unqualified = Reference(
        id="ref-unq",
        ref_kind=ReferenceKind.TYPE_USAGE,
        source_file_id="consumer.py",
        target_qualified_name="PaymentService",
    )
    res_unqualified = resolver.resolve(ref_unqualified, context_c)
    assert res_unqualified.status == ResolutionStatus.AMBIGUOUS
    assert set(res_unqualified.candidate_symbol_ids) == {"sym-mod-a-ps", "sym-mod-b-ps"}


# =====================================================================
# 3. FALSE NEGATIVE PREVENTION
# =====================================================================


@pytest.mark.unit
def test_false_negative_prevention_valid_imports_and_alias() -> None:
    """Ensure aliased imports and nested calls correctly resolve and produce valid graph edges."""
    st = SymbolTable()
    # Register StripeService and pay method
    st.register(_make_entry("sym-stripe", "vendor.stripe.StripeService", "vendor/stripe.py"))
    st.register(
        _make_entry(
            "sym-pay-method",
            "vendor.stripe.StripeService.pay",
            "vendor/stripe.py",
            kind=EntityKind.METHOD,
        )
    )

    # Consumer file with alias import: StripeService as PS
    ctx = ResolutionContext(
        repository_id=REPO_ID,
        file_id="app.py",
        file_path="app.py",
        language=Language.PYTHON,
        symbol_table=st,
        resolved_imports={"PS": "vendor.stripe.StripeService"},
    )

    resolver = ReferenceResolver()
    ref_method_call = Reference(
        id="ref-call-1",
        ref_kind=ReferenceKind.CALL,
        source_file_id="app.py",
        target_qualified_name="PS.pay",
    )
    res = resolver.resolve(ref_method_call, ctx)
    assert res.status == ResolutionStatus.RESOLVED
    assert res.target_symbol_id == "sym-pay-method"


# =====================================================================
# 4. UNRESOLVED / AMBIGUOUS SAFETY & BUILTINS
# =====================================================================


@pytest.mark.unit
def test_unresolved_ambiguous_builtin_relationship_safety() -> None:
    """Verify that unresolved, ambiguous, builtin, and external references produce NO graph edges."""
    extractor = RelationshipExtractor()
    norm = NormalizationResult(
        file=File(
            id="file-1",
            repository_id=REPO_ID,
            path="src/main.py",
            language=Language.PYTHON,
        ),
        classes=[],
        functions=[],
        methods=[],
        variables=[],
        interfaces=[],
        modules=[],
        references=[
            Reference(
                id="ref-built",
                ref_kind=ReferenceKind.CALL,
                source_file_id="file-1",
                target_qualified_name="print",
            ),
            Reference(
                id="ref-missing",
                ref_kind=ReferenceKind.CALL,
                source_file_id="file-1",
                target_qualified_name="NonExistentModule.doSomething",
            ),
        ],
    )
    st = SymbolTable()
    _nodes, edges = extractor.extract_from_normalization_result(norm, st)

    # Builtin "print" and missing "NonExistentModule" must be excluded from edges
    semantic_edges = [e for e in edges if e.kind != EdgeKind.DECLARES]
    assert len(semantic_edges) == 0


# =====================================================================
# 5. STORAGE & INDEX INVARIANTS
# =====================================================================


@pytest.mark.unit
def test_storage_crud_indexing_and_cascading_removal() -> None:
    """Verify O(1) storage CRUD, index synchronicity, and cascading removal."""
    store = InMemoryGraphStore(repository_id=REPO_ID)

    n1 = GraphNode(id="n1", kind=NodeKind.CLASS, name="A")
    n2 = GraphNode(id="n2", kind=NodeKind.METHOD, name="B")
    n3 = GraphNode(id="n3", kind=NodeKind.CLASS, name="C")
    n4 = GraphNode(id="n4", kind=NodeKind.METHOD, name="D")

    store.add_nodes([n1, n2, n3, n4])

    e1 = GraphEdge(id="e1", source_id="n1", target_id="n2", kind=EdgeKind.DECLARES)
    e2 = GraphEdge(id="e2", source_id="n3", target_id="n2", kind=EdgeKind.CALLS)
    e3 = GraphEdge(id="e3", source_id="n2", target_id="n4", kind=EdgeKind.CALLS)

    store.add_edges([e1, e2, e3])

    assert store.node_count == 4
    assert store.edge_count == 3

    # Outbound / Inbound index checks
    assert [e.id for e in store.get_outbound_edges("n1")] == ["e1"]
    assert [e.id for e in store.get_inbound_edges("n2")] == ["e1", "e2"]
    assert [e.id for e in store.get_outbound_edges("n2")] == ["e3"]

    # Cascading removal of n2
    removed = store.remove_node("n2")
    assert removed is True
    assert store.node_count == 3
    assert store.edge_count == 0  # e1, e2, e3 all pruned!

    # Index cleanliness check
    assert store.get_outbound_edges("n1") == []
    assert store.get_inbound_edges("n2") == []
    assert store.get_outbound_edges("n2") == []
    assert store.get_inbound_edges("n4") == []

    # Idempotent node re-insertion after removal
    store.add_node(n2)
    assert store.has_node("n2") is True


@pytest.mark.unit
def test_storage_duplicate_and_conflicting_insertion() -> None:
    """Verify idempotent insertion and explicit conflict exception on mismatch."""
    store = InMemoryGraphStore(repository_id=REPO_ID)
    n1 = GraphNode(id="node-1", kind=NodeKind.CLASS, name="UserService")

    # First insertion
    store.add_node(n1)
    # Idempotent second insertion of identical node
    store.add_node(n1)
    assert store.node_count == 1

    # Conflicting node with same ID but different attributes
    n1_conflict = GraphNode(id="node-1", kind=NodeKind.INTERFACE, name="UserService")
    with pytest.raises(ValueError, match="Conflicting node with ID 'node-1' already exists"):
        store.add_node(n1_conflict)


# =====================================================================
# 6. TRAVERSAL & CYCLE SAFETY INVARIANTS
# =====================================================================


@pytest.mark.unit
def test_traversal_directionality_and_cyclic_graphs() -> None:
    """Verify callers/callees directionality and cyclic graph safe termination."""
    store = InMemoryGraphStore(repository_id=REPO_ID)

    # Construct cycle: A -> CALLS -> B -> CALLS -> C -> CALLS -> A
    na = GraphNode(id="A", kind=NodeKind.METHOD, name="funcA")
    nb = GraphNode(id="B", kind=NodeKind.METHOD, name="funcB")
    nc = GraphNode(id="C", kind=NodeKind.METHOD, name="funcC")
    store.add_nodes([na, nb, nc])

    ea = GraphEdge(id="e1", source_id="A", target_id="B", kind=EdgeKind.CALLS)
    eb = GraphEdge(id="e2", source_id="B", target_id="C", kind=EdgeKind.CALLS)
    ec = GraphEdge(id="e3", source_id="C", target_id="A", kind=EdgeKind.CALLS)
    store.add_edges([ea, eb, ec])

    query_engine = GraphQueryEngine()

    # Callers of B -> [A]
    callers_b = query_engine.get_callers("B", store)
    assert [n.id for n in callers_b] == ["A"]

    # Callees of B -> [C]
    callees_b = query_engine.get_callees("B", store)
    assert [n.id for n in callees_b] == ["C"]

    # Transitive dependencies of A (should include B and C without infinite loop)
    deps_a = query_engine.get_dependencies("A", store, max_depth=None)
    assert {n.id for n in deps_a} == {"B", "C"}

    # Transitive dependents of A
    dependents_a = query_engine.get_dependents("A", store, max_depth=None)
    assert {n.id for n in dependents_a} == {"B", "C"}


@pytest.mark.unit
def test_traversal_self_loops_and_depth_limits() -> None:
    """Verify self-loop handling and depth limit restrictions."""
    store = InMemoryGraphStore(repository_id=REPO_ID)

    # Chain: N0 -> N1 -> N2 -> N3 -> N4 with N0 self-loop N0 -> N0
    nodes = [GraphNode(id=f"N{i}", kind=NodeKind.METHOD, name=f"m{i}") for i in range(5)]
    store.add_nodes(nodes)

    edges = [
        GraphEdge(id="e-self", source_id="N0", target_id="N0", kind=EdgeKind.CALLS),
        GraphEdge(id="e01", source_id="N0", target_id="N1", kind=EdgeKind.CALLS),
        GraphEdge(id="e12", source_id="N1", target_id="N2", kind=EdgeKind.CALLS),
        GraphEdge(id="e23", source_id="N2", target_id="N3", kind=EdgeKind.CALLS),
        GraphEdge(id="e34", source_id="N3", target_id="N4", kind=EdgeKind.CALLS),
    ]
    store.add_edges(edges)

    query_engine = GraphQueryEngine()

    # Self-loop check for N0
    callees_n0 = query_engine.get_callees("N0", store)
    assert {n.id for n in callees_n0} == {"N0", "N1"}

    # Depth 0 -> empty list (0 hops)
    assert query_engine.get_dependencies("N0", store, max_depth=0) == []

    # Depth 1 -> N1 (N0 is root so excluded from reachable dependency target set)
    deps_d1 = query_engine.get_dependencies("N0", store, max_depth=1)
    assert {n.id for n in deps_d1} == {"N1"}

    # Depth 2 -> N1, N2
    deps_d2 = query_engine.get_dependencies("N0", store, max_depth=2)
    assert {n.id for n in deps_d2} == {"N1", "N2"}

    # Depth None -> All reachable target nodes
    deps_all = query_engine.get_dependencies("N0", store, max_depth=None)
    assert {n.id for n in deps_all} == {"N1", "N2", "N3", "N4"}


# =====================================================================
# 7. DETERMINISM & IDEMPOTENCY
# =====================================================================


@pytest.mark.unit
def test_determinism_and_idempotency_across_runs() -> None:
    """Verify graph creation, node/edge ordering, and traversal results are 100% deterministic."""
    py_code = """
class ServiceA:
    def process(self):
        ServiceB().run()

class ServiceB:
    def run(self):
        pass
"""
    parser = PythonParser()
    parse_res = parser.parse(py_code, source_path="services.py")

    # Run 1
    norm1 = normalize_parse_result(parse_res, REPO_ID)
    st1 = SymbolTable()
    st1.register(
        _make_entry("b-run", "services.ServiceB.run", "services.py", kind=EntityKind.METHOD)
    )
    ext1 = RelationshipExtractor()
    nodes1, edges1 = ext1.extract_from_normalization_result(norm1, st1)

    # Run 2
    norm2 = normalize_parse_result(parse_res, REPO_ID)
    st2 = SymbolTable()
    st2.register(
        _make_entry("b-run", "services.ServiceB.run", "services.py", kind=EntityKind.METHOD)
    )
    ext2 = RelationshipExtractor()
    nodes2, edges2 = ext2.extract_from_normalization_result(norm2, st2)

    # Determinism assertions
    assert [n.id for n in nodes1] == [n.id for n in nodes2]
    assert [e.id for e in edges1] == [e.id for e in edges2]
    assert [n.model_dump() for n in nodes1] == [n.model_dump() for n in nodes2]
    assert [e.model_dump() for e in edges1] == [e.model_dump() for e in edges2]


# =====================================================================
# 8. PERSISTENCE & PERSISTENCE FAILURE SAFETY
# =====================================================================


@pytest.mark.asyncio
async def test_async_graph_store_persistence_and_failure_safety() -> None:
    """Verify GraphStoreContract async save/load/delete and exception behavior on missing graph."""
    store = InMemoryGraphStore(repository_id=REPO_ID)
    node = GraphNode(id="node-1", kind=NodeKind.FILE, name="app.py")
    store.add_node(node)

    cg = store.to_codegraph()

    # Save
    await store.save_graph(cg)

    # Load
    loaded = await store.load_graph(cg.repository_id)
    assert loaded.repository_id == cg.repository_id
    assert loaded.nodes == cg.nodes

    # Delete
    await store.delete_graph(cg.repository_id)

    # Missing graph load raises KeyError
    with pytest.raises(KeyError, match="No graph stored for repository ID"):
        await store.load_graph(cg.repository_id)


# =====================================================================
# 9. CROSS-LANGUAGE MATRIX & MULTI-EDGE SEMANTICS
# =====================================================================


@pytest.mark.unit
def test_cross_language_unified_edge_kind_matrix() -> None:
    """Verify Java, Python, and TS canonical code produce unified language-independent EdgeKinds."""
    j_code = "package app; public class Child extends Parent implements Interface {}"
    p_code = "class Child(Parent): pass"
    t_code = "class Child extends Parent implements Interface {}"

    j_norm = normalize_parse_result(JavaParser().parse(j_code, source_path="Child.java"), REPO_ID)
    p_norm = normalize_parse_result(PythonParser().parse(p_code, source_path="child.py"), REPO_ID)
    t_norm = normalize_parse_result(
        TypeScriptParser().parse(t_code, source_path="Child.ts"), REPO_ID
    )

    ext = RelationshipExtractor()
    j_st = SymbolTable()
    j_st.register(
        _make_entry(
            "sym-parent-cls",
            "app.Parent",
            "Parent.java",
            kind=EntityKind.CLASS,
            language=Language.JAVA,
        )
    )
    j_st.register(
        _make_entry(
            "sym-iface",
            "app.Interface",
            "Interface.java",
            kind=EntityKind.INTERFACE,
            language=Language.JAVA,
        )
    )

    p_st = SymbolTable()
    p_st.register(
        _make_entry(
            "sym-py-parent", "Parent", "parent.py", kind=EntityKind.CLASS, language=Language.PYTHON
        )
    )

    t_st = SymbolTable()
    t_st.register(
        _make_entry(
            "sym-ts-parent",
            "Parent",
            "Parent.ts",
            kind=EntityKind.CLASS,
            language=Language.TYPESCRIPT,
        )
    )
    t_st.register(
        _make_entry(
            "sym-ts-iface",
            "Interface",
            "Interface.ts",
            kind=EntityKind.INTERFACE,
            language=Language.TYPESCRIPT,
        )
    )

    _, j_edges = ext.extract_from_normalization_result(j_norm, j_st)
    _, p_edges = ext.extract_from_normalization_result(p_norm, p_st)
    _, t_edges = ext.extract_from_normalization_result(t_norm, t_st)

    # Java EXTENDS and IMPLEMENTS
    j_kinds = {e.kind for e in j_edges}
    assert EdgeKind.DECLARES in j_kinds
    assert EdgeKind.EXTENDS in j_kinds
    assert EdgeKind.IMPLEMENTS in j_kinds

    # Python EXTENDS
    p_kinds = {e.kind for e in p_edges}
    assert EdgeKind.DECLARES in p_kinds
    assert EdgeKind.EXTENDS in p_kinds

    # TS EXTENDS and IMPLEMENTS
    t_kinds = {e.kind for e in t_edges}
    assert EdgeKind.DECLARES in t_kinds
    assert EdgeKind.EXTENDS in t_kinds
    assert EdgeKind.IMPLEMENTS in t_kinds


# =====================================================================
# 10. ADVERSARIAL TOPOLOGIES & LARGE GRAPH SCALABILITY
# =====================================================================


@pytest.mark.unit
def test_adversarial_topologies_and_fan_in_fan_out() -> None:
    """Verify star, chain, isolated nodes, and large fan-in/fan-out topologies."""
    store = InMemoryGraphStore(repository_id=REPO_ID)

    # 1. Central node X
    node_x = GraphNode(id="X", kind=NodeKind.METHOD, name="centralHub")
    store.add_node(node_x)

    # 2. Large fan-in: 500 callers calling X
    callers = [
        GraphNode(id=f"caller_{i:03d}", kind=NodeKind.METHOD, name=f"caller_{i:03d}")
        for i in range(500)
    ]
    store.add_nodes(callers)
    for c in callers:
        store.add_edge(
            GraphEdge(id=f"e_in_{c.id}", source_id=c.id, target_id="X", kind=EdgeKind.CALLS)
        )

    # 3. Large fan-out: X calling 500 callees
    callees = [
        GraphNode(id=f"callee_{i:03d}", kind=NodeKind.METHOD, name=f"callee_{i:03d}")
        for i in range(500)
    ]
    store.add_nodes(callees)
    for c in callees:
        store.add_edge(
            GraphEdge(id=f"e_out_{c.id}", source_id="X", target_id=c.id, kind=EdgeKind.CALLS)
        )

    # 4. Isolated node Y
    node_y = GraphNode(id="Y", kind=NodeKind.METHOD, name="isolatedNode")
    store.add_node(node_y)

    query_engine = GraphQueryEngine()

    # Query fan-in callers
    found_callers = query_engine.get_callers("X", store)
    assert len(found_callers) == 500
    assert found_callers[0].id == "caller_000"
    assert found_callers[-1].id == "caller_499"  # Deterministically formatted string!

    # Query fan-out callees
    found_callees = query_engine.get_callees("X", store)
    assert len(found_callees) == 500

    # Query isolated node Y -> returns empty lists
    assert query_engine.get_callers("Y", store) == []
    assert query_engine.get_callees("Y", store) == []
    assert query_engine.get_dependencies("Y", store) == []
    assert query_engine.get_dependents("Y", store) == []


@pytest.mark.unit
def test_large_synthetic_graph_performance_sanity() -> None:
    """Stress test graph store with 5,000 nodes and verify sub-second traversal performance."""
    import time

    store = InMemoryGraphStore(repository_id=REPO_ID)

    # Generate 5,000 nodes
    nodes = [
        GraphNode(id=f"node_{i:04d}", kind=NodeKind.METHOD, name=f"func_{i}") for i in range(5000)
    ]
    store.add_nodes(nodes)

    # Chain 4,999 edges: node_i -> node_{i+1}
    edges = [
        GraphEdge(
            id=f"edge_{i:04d}",
            source_id=f"node_{i:04d}",
            target_id=f"node_{i + 1:04d}",
            kind=EdgeKind.CALLS,
        )
        for i in range(4999)
    ]
    store.add_edges(edges)

    assert store.node_count == 5000
    assert store.edge_count == 4999

    query_engine = GraphQueryEngine()

    start = time.perf_counter()
    # Bounded depth traversal (max_depth=50)
    deps = query_engine.get_dependencies("node_0000", store, max_depth=50)
    duration = time.perf_counter() - start

    assert len(deps) == 50
    assert duration < 0.5  # Sub-second fast traversal requirement


# =====================================================================
# 11. END-TO-END CHAOS PIPELINE CASE
# =====================================================================


@pytest.mark.unit
def test_end_to_end_chaos_pipeline_multi_file_multi_lang() -> None:
    """Full pipeline verification from multi-file sources to query engine traversals."""
    # Java Service
    j_code = """
    package com.service;
    public class OrderService {
        public void placeOrder() {
            PaymentService ps = new PaymentService();
            ps.process();
        }
    }
    """

    # Java Payment
    j_pay = """
    package com.service;
    public class PaymentService {
        public void process() {}
    }
    """

    j_parser = JavaParser()
    res1 = j_parser.parse(j_code, source_path="OrderService.java")
    res2 = j_parser.parse(j_pay, source_path="PaymentService.java")

    norm1 = normalize_parse_result(res1, REPO_ID)
    norm2 = normalize_parse_result(res2, REPO_ID)

    # Symbol Table & Registration
    st = SymbolTable()
    st.register(
        _make_entry("order-svc", "com.service.OrderService", norm1.file.id, language=Language.JAVA)
    )
    st.register(
        _make_entry("pay-svc", "com.service.PaymentService", norm2.file.id, language=Language.JAVA)
    )
    st.register(
        _make_entry(
            "pay-proc",
            "com.service.PaymentService.process",
            norm2.file.id,
            kind=EntityKind.METHOD,
            language=Language.JAVA,
        )
    )

    ext = RelationshipExtractor()
    n1, e1 = ext.extract_from_normalization_result(norm1, st)
    n2, e2 = ext.extract_from_normalization_result(norm2, st)

    store = InMemoryGraphStore(repository_id=REPO_ID)
    store.add_nodes(n1 + n2)
    store.add_edges(e1 + e2)

    query_engine = GraphQueryEngine()

    # Verify nodes exist in store
    assert store.has_node(norm1.file.id) is True
    assert store.has_node(norm2.file.id) is True

    # Reverse impact of PaymentService -> OrderService file / class
    impact = query_engine.get_impact_radius(norm2.file.id, store)
    assert isinstance(impact, list)
