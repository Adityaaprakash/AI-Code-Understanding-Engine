"""Unit tests for Phase 3 TASK-3A Code Graph Schema, Models, and Contracts."""

import pytest
from pydantic import ValidationError

from code_analyzer.ir import (
    Class,
    File,
    Function,
    Parameter,
    Reference,
    ReferenceKind,
    SourceLocation,
    Visibility,
    generate_entity_id,
)
from code_analyzer.parsers.models import Language
from graph import (
    CodeGraph,
    EdgeKind,
    GraphBuilderContract,
    GraphEdge,
    GraphNode,
    GraphQueryEngineContract,
    GraphStoreContract,
    ImportResolverContract,
    NodeKind,
    ReferenceResolverContract,
    RelationshipExtractorContract,
    ResolutionStatus,
    SymbolRegistrarContract,
    generate_edge_id,
)


@pytest.mark.unit
def test_node_kind_enum_values() -> None:
    """Verify all expected NodeKind enumeration values exist."""
    expected = {
        "repository",
        "file",
        "module",
        "package",
        "class",
        "interface",
        "function",
        "method",
        "variable",
        "parameter",
        "symbol",
    }
    actual = {kind.value for kind in NodeKind}
    assert expected.issubset(actual)


@pytest.mark.unit
def test_edge_kind_enum_values() -> None:
    """Verify all expected EdgeKind enumeration values exist."""
    expected = {
        "contains",
        "declares",
        "exports",
        "calls",
        "imports",
        "references",
        "extends",
        "implements",
        "typed_as",
        "overrides",
        "reads",
        "writes",
        "field_access",
    }
    actual = {kind.value for kind in EdgeKind}
    assert expected.issubset(actual)


@pytest.mark.unit
def test_resolution_status_enum_values() -> None:
    """Verify ResolutionStatus values."""
    assert ResolutionStatus.UNRESOLVED == "unresolved"
    assert ResolutionStatus.RESOLVED == "resolved"
    assert ResolutionStatus.AMBIGUOUS == "ambiguous"
    assert ResolutionStatus.BUILTIN == "builtin"
    assert ResolutionStatus.EXTERNAL == "external"


@pytest.mark.unit
def test_graph_node_validation_and_immutability() -> None:
    """Verify GraphNode validation rules and immutability."""
    node = GraphNode(
        id="node-1",
        kind=NodeKind.CLASS,
        name="UserService",
        qualified_name="com.app.UserService",
        language=Language.JAVA,
    )
    assert node.id == "node-1"
    assert node.kind == NodeKind.CLASS
    assert node.name == "UserService"

    # Verify frozen immutability
    with pytest.raises(ValidationError):
        setattr(node, "name", "ModifiedService")

    # Verify invalid empty ID
    with pytest.raises(ValidationError):
        GraphNode(id="   ", kind=NodeKind.CLASS)


@pytest.mark.unit
def test_graph_node_from_ir_entity() -> None:
    """Verify GraphNode derivation from Phase 2 Canonical Code IR entities."""
    file_id = generate_entity_id(
        kind="file", file_path="src/service.py", qualified_name="src/service.py"
    )
    class_id = generate_entity_id(
        kind="class", file_path="src/service.py", qualified_name="src.service.UserService"
    )

    ir_class = Class(
        id=class_id,
        file_id=file_id,
        name="UserService",
        qualified_name="src.service.UserService",
        visibility=Visibility.PUBLIC,
        modifiers=["export"],
        doc_comment="Service class handling users.",
        location=SourceLocation(start_line=10, start_column=0, end_line=50, end_column=1),
    )

    node = GraphNode.from_ir_entity(ir_class)
    assert node.id == class_id
    assert node.kind == NodeKind.CLASS
    assert node.name == "UserService"
    assert node.qualified_name == "src.service.UserService"
    assert node.file_id == file_id
    assert node.doc_comment == "Service class handling users."
    assert node.attributes["visibility"] == "public"
    assert node.attributes["modifiers"] == ["export"]


@pytest.mark.unit
def test_generate_edge_id_determinism() -> None:
    """Verify edge identity generator produces deterministic UUID v5 values."""
    id1 = generate_edge_id("node-a", "node-b", EdgeKind.CALLS, source_line=42)
    id2 = generate_edge_id("node-a", "node-b", EdgeKind.CALLS, source_line=42)
    id_diff_line = generate_edge_id("node-a", "node-b", EdgeKind.CALLS, source_line=43)
    id_diff_kind = generate_edge_id("node-a", "node-b", EdgeKind.IMPORTS, source_line=42)

    assert id1 == id2
    assert id1 != id_diff_line
    assert id1 != id_diff_kind


@pytest.mark.unit
def test_graph_edge_validation_and_immutability() -> None:
    """Verify GraphEdge validation and immutability rules."""
    edge_id = generate_edge_id("node-a", "node-b", EdgeKind.CALLS)
    edge = GraphEdge(
        id=edge_id,
        source_id="node-a",
        target_id="node-b",
        kind=EdgeKind.CALLS,
        resolution_status=ResolutionStatus.RESOLVED,
        confidence=0.95,
    )

    assert edge.id == edge_id
    assert edge.source_id == "node-a"
    assert edge.target_id == "node-b"
    assert edge.kind == EdgeKind.CALLS
    assert edge.resolution_status == ResolutionStatus.RESOLVED
    assert edge.confidence == 0.95

    # Immutability check
    with pytest.raises(ValidationError):
        setattr(edge, "confidence", 0.5)

    # Invalid confidence check
    with pytest.raises(ValidationError):
        GraphEdge(
            id=edge_id,
            source_id="node-a",
            target_id="node-b",
            kind=EdgeKind.CALLS,
            confidence=1.5,
        )


@pytest.mark.unit
def test_graph_edge_from_ir_reference() -> None:
    """Verify GraphEdge derivation from Canonical IR Reference entities."""
    ref_id = generate_entity_id(kind="reference", file_path="app.py", qualified_name="utils.helper")
    ir_ref = Reference(
        id=ref_id,
        ref_kind=ReferenceKind.CALL,
        source_symbol_id="caller-sym-id",
        source_file_id="file-1",
        source_location=SourceLocation(start_line=15, start_column=4, end_line=15, end_column=20),
        target_qualified_name="utils.helper",
        target_symbol_id="target-sym-id",
        confidence=1.0,
    )

    edge = GraphEdge.from_ir_reference(ir_ref, repository_id="repo-1")
    assert edge.source_id == "caller-sym-id"
    assert edge.target_id == "target-sym-id"
    assert edge.kind == EdgeKind.CALLS
    assert edge.resolution_status == ResolutionStatus.RESOLVED
    assert edge.confidence == 1.0
    assert edge.attributes["target_qualified_name"] == "utils.helper"
    assert edge.attributes["repository_id"] == "repo-1"

    # Test unresolved reference
    unresolved_ref = Reference(
        id="ref-2",
        ref_kind=ReferenceKind.IMPORT,
        source_file_id="file-1",
        target_qualified_name="external_pkg.module",
    )
    unresolved_edge = GraphEdge.from_ir_reference(unresolved_ref)
    assert unresolved_edge.source_id == "file-1"
    assert unresolved_edge.target_id == "external_pkg.module"
    assert unresolved_edge.kind == EdgeKind.IMPORTS
    assert unresolved_edge.resolution_status == ResolutionStatus.UNRESOLVED


@pytest.mark.unit
def test_code_graph_container_operations() -> None:
    """Verify CodeGraph node/edge management and graph queries."""
    graph = CodeGraph(repository_id="repo-123")

    node_file = GraphNode(id="f1", kind=NodeKind.FILE, name="main.py")
    node_func = GraphNode(id="fn1", kind=NodeKind.FUNCTION, name="main", file_id="f1")
    node_dep = GraphNode(id="fn2", kind=NodeKind.FUNCTION, name="helper", file_id="f1")

    graph.add_nodes([node_file, node_func, node_dep])
    assert graph.node_count == 3
    assert len(graph.get_nodes_by_kind(NodeKind.FUNCTION)) == 2

    edge_contains = GraphEdge(
        id=generate_edge_id("f1", "fn1", EdgeKind.CONTAINS),
        source_id="f1",
        target_id="fn1",
        kind=EdgeKind.CONTAINS,
    )
    edge_calls = GraphEdge(
        id=generate_edge_id("fn1", "fn2", EdgeKind.CALLS),
        source_id="fn1",
        target_id="fn2",
        kind=EdgeKind.CALLS,
        resolution_status=ResolutionStatus.RESOLVED,
    )

    graph.add_edges([edge_contains, edge_calls])
    assert graph.edge_count == 2

    # Query outbound/inbound
    outbound = graph.get_outbound_edges("fn1", kind=EdgeKind.CALLS)
    assert len(outbound) == 1
    assert outbound[0].target_id == "fn2"

    inbound = graph.get_inbound_edges("fn2", kind=EdgeKind.CALLS)
    assert len(inbound) == 1
    assert inbound[0].source_id == "fn1"

    # Query neighbors
    neighbors_out = graph.get_neighbors("fn1", direction="outbound")
    assert [n.id for n in neighbors_out] == ["fn2"]

    neighbors_in = graph.get_neighbors("fn2", direction="inbound")
    assert [n.id for n in neighbors_in] == ["fn1"]


@pytest.mark.unit
def test_code_graph_json_serialization_roundtrip() -> None:
    """Verify full JSON roundtrip serialization of CodeGraph container."""
    graph = CodeGraph(repository_id="repo-abc", metadata={"env": "test"})
    n1 = GraphNode(id="n1", kind=NodeKind.CLASS, name="A")
    n2 = GraphNode(id="n2", kind=NodeKind.METHOD, name="foo")
    e1 = GraphEdge(
        id=generate_edge_id("n1", "n2", EdgeKind.CONTAINS),
        source_id="n1",
        target_id="n2",
        kind=EdgeKind.CONTAINS,
    )
    graph.add_nodes([n1, n2])
    graph.add_edge(e1)

    json_data = graph.model_dump_json()
    reconstructed = CodeGraph.model_validate_json(json_data)

    assert reconstructed.repository_id == "repo-abc"
    assert reconstructed.metadata == {"env": "test"}
    assert reconstructed.node_count == 2
    assert reconstructed.edge_count == 1
    assert reconstructed.get_node("n1") == n1
    assert reconstructed.get_node("n2") == n2
    assert reconstructed.get_edge(e1.id) == e1


@pytest.mark.unit
def test_phase3_contracts_abstract_instantiation() -> None:
    """Verify that Phase 3 abstract contracts enforce interface implementations."""
    with pytest.raises(TypeError):
        SymbolRegistrarContract()  # type: ignore[abstract]

    with pytest.raises(TypeError):
        ImportResolverContract()  # type: ignore[abstract]

    with pytest.raises(TypeError):
        ReferenceResolverContract()  # type: ignore[abstract]

    with pytest.raises(TypeError):
        RelationshipExtractorContract()  # type: ignore[abstract]

    with pytest.raises(TypeError):
        GraphBuilderContract()  # type: ignore[abstract]

    with pytest.raises(TypeError):
        GraphStoreContract()  # type: ignore[abstract]

    with pytest.raises(TypeError):
        GraphQueryEngineContract()  # type: ignore[abstract]


@pytest.mark.unit
def test_end_to_end_ir_derivation_topology() -> None:
    """Integration verification: derive CodeGraph topology directly from Phase 2 IR entities."""
    repo_id = "repo-xyz"
    file_id = generate_entity_id("file", "math_utils.py", "math_utils.py")
    func_id = generate_entity_id("function", "math_utils.py", "math_utils.add")
    param_id = generate_entity_id("parameter", "math_utils.py", "math_utils.add.a")

    ir_file = File(
        id=file_id,
        repository_id=repo_id,
        path="math_utils.py",
        language=Language.PYTHON,
        loc=20,
    )
    ir_func = Function(
        id=func_id,
        file_id=file_id,
        name="add",
        qualified_name="math_utils.add",
        parameters=[Parameter(id=param_id, name="a", position=0)],
        return_type="int",
    )
    ir_ref = Reference(
        id=generate_entity_id("reference", "math_utils.py", "builtins.int"),
        ref_kind=ReferenceKind.TYPE_USAGE,
        source_symbol_id=func_id,
        source_file_id=file_id,
        target_qualified_name="builtins.int",
    )

    # Derivation
    node_file = GraphNode.from_ir_entity(ir_file)
    node_func = GraphNode.from_ir_entity(ir_func)
    edge_declares = GraphEdge(
        id=generate_edge_id(file_id, func_id, EdgeKind.DECLARES),
        source_id=file_id,
        target_id=func_id,
        kind=EdgeKind.DECLARES,
    )
    edge_ref = GraphEdge.from_ir_reference(ir_ref, repository_id=repo_id)

    graph = CodeGraph(repository_id=repo_id)
    graph.add_nodes([node_file, node_func])
    graph.add_edges([edge_declares, edge_ref])

    assert graph.node_count == 2
    assert graph.edge_count == 2
    assert graph.get_node(file_id) == node_file
    assert graph.get_node(func_id) == node_func
    assert len(graph.get_outbound_edges(file_id, kind=EdgeKind.DECLARES)) == 1
    assert graph.get_outbound_edges(func_id, kind=EdgeKind.TYPED_AS)[0].target_id == "builtins.int"
