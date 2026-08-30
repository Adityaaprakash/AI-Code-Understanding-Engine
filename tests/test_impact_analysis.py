"""Unit and integration test suite for Task 3H Initial Impact Analysis (ImpactAnalyzer).

Exercises direct vs transitive impact, depth limits, minimum impact depth calculation,
path explanation reconstruction, cycle safety, self-loops, disconnected components,
structural edge exclusion, custom edge kind filtering, error handling for missing roots,
Pydantic model immutability & serialization, multi-language E2E pipelines (Java, Python, TypeScript),
large fan-in, synthetic 5,000-node graph performance, and adversarial topology correctness.
"""


import pytest
from pydantic import ValidationError

from code_analyzer.ir import EntityKind, Reference, ReferenceKind
from code_analyzer.normalization import normalize_parse_result
from code_analyzer.parsers import JavaParser, PythonParser, TypeScriptParser
from code_analyzer.parsers.models import Language
from code_analyzer.resolution import (
    RelationshipExtractor,
    ResolutionResult,
    SymbolEntry,
    SymbolTable,
)
from graph.edges import GraphEdge
from graph.enums import EdgeKind, NodeKind
from graph.impact_analyzer import (
    ImpactAnalysisResult,
    ImpactAnalyzer,
)
from graph.nodes import GraphNode
from graph.store import InMemoryGraphStore

REPO_ID = "repo-impact-suite"


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
# 1. DIRECT & TRANSITIVE IMPACT, DEPTH SEMANTICS
# =====================================================================


@pytest.mark.unit
def test_direct_and_transitive_impact_depth_semantics() -> None:
    """Verify max_depth=0, 1, 2, 3, and None for direct and multi-hop transitive impact."""
    store = InMemoryGraphStore(repository_id=REPO_ID)

    # Chain: D -> REFERENCES -> C -> CALLS -> A -> USES -> B (Root)
    nb = GraphNode(id="B", kind=NodeKind.CLASS, name="PaymentService")
    na = GraphNode(id="A", kind=NodeKind.CLASS, name="CheckoutService")
    nc = GraphNode(id="C", kind=NodeKind.METHOD, name="processOrder")
    nd = GraphNode(id="D", kind=NodeKind.FILE, name="app.py")
    store.add_nodes([nb, na, nc, nd])

    e1 = GraphEdge(id="e1", source_id="A", target_id="B", kind=EdgeKind.USES)
    e2 = GraphEdge(id="e2", source_id="C", target_id="A", kind=EdgeKind.CALLS)
    e3 = GraphEdge(id="e3", source_id="D", target_id="C", kind=EdgeKind.REFERENCES)
    store.add_edges([e1, e2, e3])

    analyzer = ImpactAnalyzer()

    # max_depth = 0 -> root metadata only, 0 impacted nodes
    res_d0 = analyzer.analyze_impact("B", store, max_depth=0)
    assert res_d0.root_symbol_id == "B"
    assert res_d0.root_name == "PaymentService"
    assert res_d0.total_impacted == 0
    assert res_d0.impacted_nodes == []

    # max_depth = 1 -> direct dependent: A
    res_d1 = analyzer.analyze_impact("B", store, max_depth=1)
    assert res_d1.total_impacted == 1
    assert res_d1.impacted_symbol_ids == ["A"]
    assert res_d1.impacted_nodes[0].minimum_depth == 1

    # max_depth = 2 -> A (depth 1), C (depth 2)
    res_d2 = analyzer.analyze_impact("B", store, max_depth=2)
    assert res_d2.total_impacted == 2
    assert res_d2.impacted_symbol_ids == ["A", "C"]

    # max_depth = 3 or None -> A (1), C (2), D (3)
    res_d3 = analyzer.analyze_impact("B", store, max_depth=3)
    assert res_d3.total_impacted == 3
    assert res_d3.impacted_symbol_ids == ["A", "C", "D"]

    res_all = analyzer.analyze_impact("B", store, max_depth=None)
    assert res_all.total_impacted == 3
    assert res_all.impacted_symbol_ids == ["A", "C", "D"]


# =====================================================================
# 2. MINIMUM DEPTH & MULTIPLE PATHS
# =====================================================================


@pytest.mark.unit
def test_minimum_depth_calculation_and_multiple_paths() -> None:
    """Verify shortest path (minimum_depth) calculation and multi-path tracking."""
    store = InMemoryGraphStore(repository_id=REPO_ID)

    # Topology:
    # Path 1: B -> USES -> Root (length 1)
    # Path 2: B -> CALLS -> A -> USES -> Root (length 2)
    n_root = GraphNode(id="Root", kind=NodeKind.CLASS, name="RootService")
    na = GraphNode(id="A", kind=NodeKind.CLASS, name="ServiceA")
    nb = GraphNode(id="B", kind=NodeKind.CLASS, name="ServiceB")
    store.add_nodes([n_root, na, nb])

    e1 = GraphEdge(id="e1", source_id="B", target_id="Root", kind=EdgeKind.USES)
    e2 = GraphEdge(id="e2", source_id="A", target_id="Root", kind=EdgeKind.USES)
    e3 = GraphEdge(id="e3", source_id="B", target_id="A", kind=EdgeKind.CALLS)
    store.add_edges([e1, e2, e3])

    analyzer = ImpactAnalyzer()
    result = analyzer.analyze_impact("Root", store)

    assert result.total_impacted == 2
    # B is reachable directly (depth 1) and via A (depth 2). Its minimum_depth MUST be 1.
    node_b = result.get_impacted_node("B")
    assert node_b is not None
    assert node_b.minimum_depth == 1

    node_a = result.get_impacted_node("A")
    assert node_a is not None
    assert node_a.minimum_depth == 1

    # Check that paths for B contain both Path 1 (direct) and Path 2 (via A)
    b_paths = result.get_paths_for_node("B")
    assert len(b_paths) == 2
    depths = {p.depth for p in b_paths}
    assert depths == {1, 2}


# =====================================================================
# 3. PATH EXPLANATION STRUCTURE & DIRECTION
# =====================================================================


@pytest.mark.unit
def test_path_explanation_structure_and_edge_direction() -> None:
    """Verify ImpactPath and ImpactPathStep preserve original edge directions and metadata."""
    store = InMemoryGraphStore(repository_id=REPO_ID)

    # PaymentService <- USES <- CheckoutService <- CALLS <- CheckoutController
    ps = GraphNode(id="ps", kind=NodeKind.CLASS, name="PaymentService")
    cs = GraphNode(id="cs", kind=NodeKind.CLASS, name="CheckoutService")
    cc = GraphNode(id="cc", kind=NodeKind.CLASS, name="CheckoutController")
    store.add_nodes([ps, cs, cc])

    e1 = GraphEdge(id="e1", source_id="cs", target_id="ps", kind=EdgeKind.USES)
    e2 = GraphEdge(id="e2", source_id="cc", target_id="cs", kind=EdgeKind.CALLS)
    store.add_edges([e1, e2])

    analyzer = ImpactAnalyzer()
    result = analyzer.analyze_impact("ps", store)

    cc_paths = result.get_paths_for_node("cc")
    assert len(cc_paths) == 1
    path = cc_paths[0]
    assert path.target_id == "cc"
    assert path.depth == 2
    assert path.node_ids == ["ps", "cs", "cc"]

    # Step 1: cs -> ps (USES)
    # Step 2: cc -> cs (CALLS)
    assert len(path.steps) == 2
    assert path.steps[0].source_id == "cs"
    assert path.steps[0].target_id == "ps"
    assert path.steps[0].kind == EdgeKind.USES

    assert path.steps[1].source_id == "cc"
    assert path.steps[1].target_id == "cs"
    assert path.steps[1].kind == EdgeKind.CALLS


# =====================================================================
# 4. SAFETY: CYCLES, SELF-LOOPS, DISCONNECTED COMPONENTS
# =====================================================================


@pytest.mark.unit
def test_cycle_safety_self_loops_and_disconnected_components() -> None:
    """Verify cycle safety, root self-loop exclusion, and disconnected graph isolation."""
    store = InMemoryGraphStore(repository_id=REPO_ID)

    # Component 1: A -> CALLS -> B -> CALLS -> C -> CALLS -> A (Cycle) with A self-loop
    na = GraphNode(id="A", kind=NodeKind.METHOD, name="funcA")
    nb = GraphNode(id="B", kind=NodeKind.METHOD, name="funcB")
    nc = GraphNode(id="C", kind=NodeKind.METHOD, name="funcC")

    # Component 2: Isolated D
    nd = GraphNode(id="D", kind=NodeKind.METHOD, name="isolatedD")
    store.add_nodes([na, nb, nc, nd])

    ea = GraphEdge(id="e_self", source_id="A", target_id="A", kind=EdgeKind.CALLS)
    e1 = GraphEdge(id="e1", source_id="A", target_id="B", kind=EdgeKind.CALLS)
    e2 = GraphEdge(id="e2", source_id="B", target_id="C", kind=EdgeKind.CALLS)
    e3 = GraphEdge(id="e3", source_id="C", target_id="A", kind=EdgeKind.CALLS)
    store.add_edges([ea, e1, e2, e3])

    analyzer = ImpactAnalyzer()

    # Impact of A: dependents are C (via C->A) and B (via C->B->A)
    # Root A must NOT appear in impacted_nodes!
    res_a = analyzer.analyze_impact("A", store)
    assert res_a.total_impacted == 2
    assert set(res_a.impacted_symbol_ids) == {"B", "C"}
    assert "A" not in res_a.impacted_symbol_ids

    # Isolated node D -> 0 impacted
    res_d = analyzer.analyze_impact("D", store)
    assert res_d.total_impacted == 0
    assert res_d.impacted_nodes == []


# =====================================================================
# 5. STRUCTURAL EDGE EXCLUSION
# =====================================================================


@pytest.mark.unit
def test_structural_edge_exclusion() -> None:
    """Verify DECLARES, CONTAINS, EXPORTS edges do NOT yield impact relationships."""
    store = InMemoryGraphStore(repository_id=REPO_ID)

    n_file = GraphNode(id="file.py", kind=NodeKind.FILE, name="file.py")
    n_cls = GraphNode(id="MyClass", kind=NodeKind.CLASS, name="MyClass")
    n_mthd = GraphNode(id="my_method", kind=NodeKind.METHOD, name="my_method")
    store.add_nodes([n_file, n_cls, n_mthd])

    # file.py -> DECLARES -> MyClass -> DECLARES -> my_method
    e1 = GraphEdge(id="e1", source_id="file.py", target_id="MyClass", kind=EdgeKind.DECLARES)
    e2 = GraphEdge(id="e2", source_id="MyClass", target_id="my_method", kind=EdgeKind.DECLARES)
    store.add_edges([e1, e2])

    analyzer = ImpactAnalyzer()
    res = analyzer.analyze_impact("my_method", store)
    # DECLARES is structural, so no dependency impact created
    assert res.total_impacted == 0


# =====================================================================
# 6. SEMANTIC EDGE MATRIX & CUSTOM EDGE KIND FILTERING
# =====================================================================


@pytest.mark.unit
def test_semantic_edge_matrix_and_custom_filtering() -> None:
    """Verify each semantic EdgeKind participates in impact, and custom edge_kinds filter works."""
    store = InMemoryGraphStore(repository_id=REPO_ID)
    root = GraphNode(id="R", kind=NodeKind.CLASS, name="Root")
    store.add_node(root)

    semantic_kinds = [
        EdgeKind.CALLS,
        EdgeKind.IMPORTS,
        EdgeKind.USES,
        EdgeKind.REFERENCES,
        EdgeKind.EXTENDS,
        EdgeKind.IMPLEMENTS,
        EdgeKind.TYPED_AS,
        EdgeKind.READS,
        EdgeKind.WRITES,
        EdgeKind.FIELD_ACCESS,
    ]

    for idx, kind in enumerate(semantic_kinds):
        node_id = f"node_{kind.value}"
        n = GraphNode(id=node_id, kind=NodeKind.CLASS, name=f"Node_{kind.value}")
        store.add_node(n)
        e = GraphEdge(id=f"e_{idx}", source_id=node_id, target_id="R", kind=kind)
        store.add_edge(e)

    analyzer = ImpactAnalyzer()

    # All semantic edge kinds included by default
    res_all = analyzer.analyze_impact("R", store)
    assert res_all.total_impacted == len(semantic_kinds)

    # Custom filtering: CALLS only
    res_calls = analyzer.analyze_impact("R", store, edge_kinds={EdgeKind.CALLS})
    assert res_calls.total_impacted == 1
    assert res_calls.impacted_symbol_ids == ["node_calls"]


# =====================================================================
# 7. MISSING ROOT & EMPTY GRAPH HANDLING
# =====================================================================


@pytest.mark.unit
def test_missing_root_and_empty_graph_error_safety() -> None:
    """Verify requesting impact analysis for a missing node or empty store raises KeyError."""
    store = InMemoryGraphStore(repository_id=REPO_ID)
    analyzer = ImpactAnalyzer()

    with pytest.raises(KeyError, match="Root node 'missing-id' not found in graph"):
        analyzer.analyze_impact("missing-id", store)


# =====================================================================
# 8. IMMUTABILITY, DETERMINISM & JSON SERIALIZATION
# =====================================================================


@pytest.mark.unit
def test_immutability_determinism_and_lossless_serialization() -> None:
    """Verify result immutability, deterministic ordering across runs, and JSON round-tripping."""
    store = InMemoryGraphStore(repository_id=REPO_ID)
    n0 = GraphNode(id="N0", kind=NodeKind.CLASS, name="Service0")
    n1 = GraphNode(id="N1", kind=NodeKind.CLASS, name="Service1")
    n2 = GraphNode(id="N2", kind=NodeKind.CLASS, name="Service2")
    store.add_nodes([n0, n1, n2])

    e1 = GraphEdge(id="e1", source_id="N1", target_id="N0", kind=EdgeKind.USES)
    e2 = GraphEdge(id="e2", source_id="N2", target_id="N1", kind=EdgeKind.CALLS)
    store.add_edges([e1, e2])

    analyzer = ImpactAnalyzer()

    # Run 1
    res1 = analyzer.analyze_impact("N0", store)
    # Run 2
    res2 = analyzer.analyze_impact("N0", store)

    # Immutability
    with pytest.raises(ValidationError):
        res1.total_impacted = 99

    # Determinism
    assert res1.model_dump() == res2.model_dump()

    # Lossless JSON serialization round-trip
    json_str = res1.model_dump_json()
    deserialized = ImpactAnalysisResult.model_validate_json(json_str)
    assert deserialized == res1


# =====================================================================
# 9. END-TO-END MULTI-LANGUAGE PIPELINES (JAVA, PYTHON, TYPESCRIPT)
# =====================================================================


@pytest.mark.unit
def test_end_to_end_java_impact_pipeline() -> None:
    """Verify full end-to-end Java source code impact analysis pipeline."""
    jp = JavaParser()
    svc_code = "package com.app; public class PaymentService { public void process() {} }"
    chk_code = "package com.app; public class CheckoutService { public void checkout() {} }"

    r_svc = jp.parse(svc_code, source_path="PaymentService.java")
    r_chk = jp.parse(chk_code, source_path="CheckoutService.java")

    n_svc = normalize_parse_result(r_svc, REPO_ID)
    n_chk = normalize_parse_result(r_chk, REPO_ID)

    st = SymbolTable()
    st.register_normalization_result(n_svc, REPO_ID)
    st.register_normalization_result(n_chk, REPO_ID)

    ps_id = n_svc.classes[0].id
    cs_id = n_chk.classes[0].id

    ref = Reference(
        id="ref-java-1",
        ref_kind=ReferenceKind.CALL,
        source_file_id=n_chk.file.id,
        source_symbol_id=cs_id,
        target_qualified_name="com.app.PaymentService",
        target_symbol_id=ps_id,
    )
    n_chk.references.append(ref)
    res_map = {"ref-java-1": ResolutionResult.resolved("ref-java-1", "com.app.PaymentService", ps_id)}

    ext = RelationshipExtractor()
    nd1, ed1 = ext.extract_from_normalization_result(n_svc, st)
    nd2, ed2 = ext.extract_from_normalization_result(n_chk, st, resolution_results=res_map)

    store = InMemoryGraphStore(repository_id=REPO_ID)
    store.add_nodes(nd1 + nd2)
    store.add_edges(ed1 + ed2)

    analyzer = ImpactAnalyzer()
    res = analyzer.analyze_impact(ps_id, store)

    assert res.total_impacted == 1
    assert res.impacted_symbol_ids == [cs_id]


@pytest.mark.unit
def test_end_to_end_python_impact_pipeline() -> None:
    """Verify full end-to-end Python source code impact analysis pipeline."""
    p_parser = PythonParser()
    db_code = "class Database:\n    def connect(self):\n        pass"
    app_code = "class App:\n    def run(self):\n        pass"

    r_db = p_parser.parse(db_code, source_path="db.py")
    r_app = p_parser.parse(app_code, source_path="app.py")

    n_db = normalize_parse_result(r_db, REPO_ID)
    n_app = normalize_parse_result(r_app, REPO_ID)

    st = SymbolTable()
    st.register_normalization_result(n_db, REPO_ID)
    st.register_normalization_result(n_app, REPO_ID)

    db_id = n_db.classes[0].id
    app_id = n_app.classes[0].id

    ref = Reference(
        id="ref-py-1",
        ref_kind=ReferenceKind.TYPE_USAGE,
        source_file_id=n_app.file.id,
        source_symbol_id=app_id,
        target_qualified_name="Database",
        target_symbol_id=db_id,
    )
    n_app.references.append(ref)
    res_map = {"ref-py-1": ResolutionResult.resolved("ref-py-1", "Database", db_id)}

    ext = RelationshipExtractor()
    nd1, ed1 = ext.extract_from_normalization_result(n_db, st)
    nd2, ed2 = ext.extract_from_normalization_result(n_app, st, resolution_results=res_map)

    store = InMemoryGraphStore(repository_id=REPO_ID)
    store.add_nodes(nd1 + nd2)
    store.add_edges(ed1 + ed2)

    analyzer = ImpactAnalyzer()
    res = analyzer.analyze_impact(db_id, store)
    assert res.total_impacted == 1
    assert res.impacted_symbol_ids == [app_id]


@pytest.mark.unit
def test_end_to_end_typescript_impact_pipeline() -> None:
    """Verify full end-to-end TypeScript source code impact analysis pipeline."""
    tp = TypeScriptParser()
    store_code = "export class BaseStore {}"
    cmp_code = "export class Component {}"

    r_store = tp.parse(store_code, source_path="BaseStore.ts")
    r_cmp = tp.parse(cmp_code, source_path="Component.ts")

    n_store = normalize_parse_result(r_store, REPO_ID)
    n_cmp = normalize_parse_result(r_cmp, REPO_ID)

    st = SymbolTable()
    st.register_normalization_result(n_store, REPO_ID)
    st.register_normalization_result(n_cmp, REPO_ID)

    base_id = n_store.classes[0].id
    cmp_id = n_cmp.classes[0].id

    ref = Reference(
        id="ref-ts-1",
        ref_kind=ReferenceKind.EXTENDS,
        source_file_id=n_cmp.file.id,
        source_symbol_id=cmp_id,
        target_qualified_name="BaseStore",
        target_symbol_id=base_id,
    )
    n_cmp.references.append(ref)
    res_map = {"ref-ts-1": ResolutionResult.resolved("ref-ts-1", "BaseStore", base_id)}

    ext = RelationshipExtractor()
    nd1, ed1 = ext.extract_from_normalization_result(n_store, st)
    nd2, ed2 = ext.extract_from_normalization_result(n_cmp, st, resolution_results=res_map)

    store = InMemoryGraphStore(repository_id=REPO_ID)
    store.add_nodes(nd1 + nd2)
    store.add_edges(ed1 + ed2)

    analyzer = ImpactAnalyzer()
    res = analyzer.analyze_impact(base_id, store)
    assert res.total_impacted == 1
    assert res.impacted_symbol_ids == [cmp_id]


# =====================================================================
# 10. SCALABILITY: LARGE FAN-IN & 5,000-NODE SYNTHETIC GRAPH
# =====================================================================


@pytest.mark.unit
def test_large_fan_in_and_synthetic_graph_performance() -> None:
    """Verify large fan-in (500 callers) and 5,000 synthetic node performance."""
    import time

    store = InMemoryGraphStore(repository_id=REPO_ID)
    root = GraphNode(id="Root", kind=NodeKind.CLASS, name="CoreService")
    store.add_node(root)

    # 500 callers
    callers = [
        GraphNode(id=f"caller_{i:03d}", kind=NodeKind.CLASS, name=f"Caller_{i:03d}") for i in range(500)
    ]
    store.add_nodes(callers)
    for c in callers:
        store.add_edge(GraphEdge(id=f"e_in_{c.id}", source_id=c.id, target_id="Root", kind=EdgeKind.CALLS))

    analyzer = ImpactAnalyzer()
    res = analyzer.analyze_impact("Root", store)
    assert res.total_impacted == 500
    assert res.impacted_symbol_ids[0] == "caller_000"
    assert res.impacted_symbol_ids[-1] == "caller_499"

    # Synthetic 5,000-node graph
    store_5k = InMemoryGraphStore(repository_id=REPO_ID)
    nodes_5k = [GraphNode(id=f"node_{i:04d}", kind=NodeKind.METHOD, name=f"m_{i}") for i in range(5000)]
    store_5k.add_nodes(nodes_5k)
    edges_5k = [
        GraphEdge(id=f"e_{i:04d}", source_id=f"node_{i+1:04d}", target_id=f"node_{i:04d}", kind=EdgeKind.CALLS)
        for i in range(4999)
    ]
    store_5k.add_edges(edges_5k)

    start = time.perf_counter()
    res_5k = analyzer.analyze_impact("node_0000", store_5k, max_depth=50)
    duration = time.perf_counter() - start

    assert res_5k.total_impacted == 50
    assert duration < 0.5  # Sub-second fast impact traversal requirement
