"""Unit and integration tests for Task 3E Graph Storage (InMemoryGraphStore)."""

import pytest

from graph.edges import GraphEdge, generate_edge_id
from graph.enums import EdgeKind, NodeKind, ResolutionStatus
from graph.models import CodeGraph
from graph.nodes import GraphNode
from graph.store import InMemoryGraphStore


@pytest.fixture
def store() -> InMemoryGraphStore:
    """Fixture providing an empty InMemoryGraphStore."""
    return InMemoryGraphStore(repository_id="repo-1")


@pytest.fixture
def sample_nodes() -> tuple[GraphNode, GraphNode, GraphNode]:
    """Fixture providing a trio of sample GraphNode objects."""
    n1 = GraphNode(id="node-1", kind=NodeKind.CLASS, name="UserService")
    n2 = GraphNode(id="node-2", kind=NodeKind.METHOD, name="createUser")
    n3 = GraphNode(id="node-3", kind=NodeKind.CLASS, name="UserRepository")
    return n1, n2, n3


# ──────────────────────────────────────────────────────────────────────────────
# 1. Node Operations & Identity Tests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_add_and_retrieve_node(
    store: InMemoryGraphStore, sample_nodes: tuple[GraphNode, ...]
) -> None:
    """TC-1 & TC-2: Add node and retrieve node by ID."""
    n1, _, _ = sample_nodes
    store.add_node(n1)

    assert store.node_count == 1
    assert store.has_node("node-1") is True
    assert store.get_node("node-1") == n1


@pytest.mark.unit
def test_add_duplicate_identical_node(
    store: InMemoryGraphStore, sample_nodes: tuple[GraphNode, ...]
) -> None:
    """TC-3: Duplicate identical node insertion is idempotent."""
    n1, _, _ = sample_nodes
    store.add_node(n1)
    store.add_node(n1)  # Re-insert exact same node

    assert store.node_count == 1
    assert store.get_node("node-1") == n1


@pytest.mark.unit
def test_add_conflicting_node_raises(
    store: InMemoryGraphStore, sample_nodes: tuple[GraphNode, ...]
) -> None:
    """TC-4: Conflicting node with same ID but different properties raises ValueError."""
    n1, _, _ = sample_nodes
    store.add_node(n1)

    conflict_n1 = GraphNode(id="node-1", kind=NodeKind.FUNCTION, name="DifferentName")
    with pytest.raises(ValueError, match="Conflicting node with ID 'node-1'"):
        store.add_node(conflict_n1)


@pytest.mark.unit
def test_remove_node_removes_incident_edges(
    store: InMemoryGraphStore, sample_nodes: tuple[GraphNode, ...]
) -> None:
    """TC-5: Removing a node also removes incident edges to preserve graph consistency."""
    n1, n2, n3 = sample_nodes
    store.add_nodes([n1, n2, n3])

    e1 = GraphEdge(
        id=generate_edge_id("node-1", "node-2", EdgeKind.DECLARES),
        source_id="node-1",
        target_id="node-2",
        kind=EdgeKind.DECLARES,
    )
    e2 = GraphEdge(
        id=generate_edge_id("node-2", "node-3", EdgeKind.CALLS),
        source_id="node-2",
        target_id="node-3",
        kind=EdgeKind.CALLS,
    )
    store.add_edges([e1, e2])
    assert store.edge_count == 2

    # Remove central node-2
    removed = store.remove_node("node-2")
    assert removed is True
    assert store.has_node("node-2") is False
    assert store.node_count == 2

    # Both incident edges (e1 and e2) must be removed automatically
    assert store.edge_count == 0
    assert store.has_edge(e1.id) is False
    assert store.has_edge(e2.id) is False


# ──────────────────────────────────────────────────────────────────────────────
# 2. Edge Operations, Consistency & Indexing Tests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_add_and_retrieve_edge(
    store: InMemoryGraphStore, sample_nodes: tuple[GraphNode, ...]
) -> None:
    """TC-6 & TC-7: Add and retrieve edge."""
    n1, n2, _ = sample_nodes
    store.add_nodes([n1, n2])

    eid = generate_edge_id("node-1", "node-2", EdgeKind.DECLARES)
    edge = GraphEdge(id=eid, source_id="node-1", target_id="node-2", kind=EdgeKind.DECLARES)
    store.add_edge(edge)

    assert store.edge_count == 1
    assert store.has_edge(eid) is True
    assert store.get_edge(eid) == edge


@pytest.mark.unit
def test_duplicate_identical_edge_idempotent(
    store: InMemoryGraphStore, sample_nodes: tuple[GraphNode, ...]
) -> None:
    """TC-8: Duplicate identical edge insertion is idempotent."""
    n1, n2, _ = sample_nodes
    store.add_nodes([n1, n2])

    eid = generate_edge_id("node-1", "node-2", EdgeKind.DECLARES)
    edge = GraphEdge(id=eid, source_id="node-1", target_id="node-2", kind=EdgeKind.DECLARES)
    store.add_edge(edge)
    store.add_edge(edge)

    assert store.edge_count == 1


@pytest.mark.unit
def test_conflicting_edge_raises(
    store: InMemoryGraphStore, sample_nodes: tuple[GraphNode, ...]
) -> None:
    """TC-9: Conflicting edge with same ID raises ValueError."""
    n1, n2, _ = sample_nodes
    store.add_nodes([n1, n2])

    eid = generate_edge_id("node-1", "node-2", EdgeKind.DECLARES)
    e1 = GraphEdge(
        id=eid, source_id="node-1", target_id="node-2", kind=EdgeKind.DECLARES, confidence=1.0
    )
    e2 = GraphEdge(
        id=eid, source_id="node-1", target_id="node-2", kind=EdgeKind.DECLARES, confidence=0.5
    )

    store.add_edge(e1)
    with pytest.raises(ValueError, match="Conflicting edge with ID"):
        store.add_edge(e2)


@pytest.mark.unit
def test_remove_edge(store: InMemoryGraphStore, sample_nodes: tuple[GraphNode, ...]) -> None:
    """TC-10: Remove edge by ID and verify index cleanup."""
    n1, n2, _ = sample_nodes
    store.add_nodes([n1, n2])

    eid = generate_edge_id("node-1", "node-2", EdgeKind.DECLARES)
    edge = GraphEdge(id=eid, source_id="node-1", target_id="node-2", kind=EdgeKind.DECLARES)
    store.add_edge(edge)

    removed = store.remove_edge(eid)
    assert removed is True
    assert store.edge_count == 0
    assert store.get_outbound_edges("node-1") == []


@pytest.mark.unit
def test_graph_consistency_enforcement(store: InMemoryGraphStore) -> None:
    """TC-17 & TC-18 & TC-19: Enforce graph consistency when adding edges with missing nodes."""
    n1 = GraphNode(id="n1", kind=NodeKind.CLASS, name="A")
    store.add_node(n1)

    eid = generate_edge_id("n1", "missing-target", EdgeKind.CALLS)
    edge = GraphEdge(id=eid, source_id="n1", target_id="missing-target", kind=EdgeKind.CALLS)

    with pytest.raises(ValueError, match="target node 'missing-target' does not exist"):
        store.add_edge(edge, enforce_consistency=True)


@pytest.mark.unit
def test_outbound_and_inbound_indexing_and_kind_filtering(store: InMemoryGraphStore) -> None:
    """TC-11 & TC-12 & TC-13: Fast indexed outbound/inbound lookups with edge-kind filtering."""
    n1 = GraphNode(id="n1", kind=NodeKind.CLASS, name="Service")
    n2 = GraphNode(id="n2", kind=NodeKind.CLASS, name="Helper")
    n3 = GraphNode(id="n3", kind=NodeKind.INTERFACE, name="IService")
    store.add_nodes([n1, n2, n3])

    e1 = GraphEdge(
        id=generate_edge_id("n1", "n2", EdgeKind.CALLS),
        source_id="n1",
        target_id="n2",
        kind=EdgeKind.CALLS,
    )
    e2 = GraphEdge(
        id=generate_edge_id("n1", "n3", EdgeKind.IMPLEMENTS),
        source_id="n1",
        target_id="n3",
        kind=EdgeKind.IMPLEMENTS,
    )
    store.add_edges([e1, e2])

    # Outbound queries
    out_all = store.get_outbound_edges("n1")
    assert len(out_all) == 2

    out_calls = store.get_outbound_edges("n1", kind=EdgeKind.CALLS)
    assert len(out_calls) == 1
    assert out_calls[0].target_id == "n2"

    out_impl = store.get_outbound_edges("n1", kind=EdgeKind.IMPLEMENTS)
    assert len(out_impl) == 1
    assert out_impl[0].target_id == "n3"

    # Inbound queries
    in_calls = store.get_inbound_edges("n2", kind=EdgeKind.CALLS)
    assert len(in_calls) == 1
    assert in_calls[0].source_id == "n1"


@pytest.mark.unit
def test_clear_graph_store(store: InMemoryGraphStore, sample_nodes: tuple[GraphNode, ...]) -> None:
    """TC-14 & TC-15 & TC-16: Verify node_count, edge_count, and clear()."""
    n1, n2, _ = sample_nodes
    store.add_nodes([n1, n2])
    edge = GraphEdge(
        id=generate_edge_id("node-1", "node-2", EdgeKind.CALLS),
        source_id="node-1",
        target_id="node-2",
        kind=EdgeKind.CALLS,
    )
    store.add_edge(edge)

    assert store.node_count == 2
    assert store.edge_count == 1

    store.clear()
    assert store.node_count == 0
    assert store.edge_count == 0


# ──────────────────────────────────────────────────────────────────────────────
# 3. Serialization & Persistence Contract Tests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_to_codegraph_and_from_codegraph_roundtrip(
    store: InMemoryGraphStore, sample_nodes: tuple[GraphNode, ...]
) -> None:
    """TC-20 & TC-21: CodeGraph container export, import, and JSON serialization roundtrip."""
    n1, n2, _ = sample_nodes
    store.add_nodes([n1, n2])
    edge = GraphEdge(
        id=generate_edge_id("node-1", "node-2", EdgeKind.CALLS),
        source_id="node-1",
        target_id="node-2",
        kind=EdgeKind.CALLS,
        resolution_status=ResolutionStatus.RESOLVED,
    )
    store.add_edge(edge)

    codegraph = store.to_codegraph(repository_id="repo-1")

    # JSON roundtrip
    json_str = codegraph.model_dump_json()
    reconstructed_graph = CodeGraph.model_validate_json(json_str)

    # Re-import into fresh store
    new_store = InMemoryGraphStore.from_codegraph(reconstructed_graph)
    assert new_store.node_count == 2
    assert new_store.edge_count == 1
    assert new_store.get_node("node-1") == n1
    assert new_store.get_edge(edge.id) == edge


@pytest.mark.asyncio
async def test_async_graph_store_contract_methods(
    store: InMemoryGraphStore, sample_nodes: tuple[GraphNode, ...]
) -> None:
    """TC-22: Save, load, and delete CodeGraph snapshots via GraphStoreContract async methods."""
    n1, n2, _ = sample_nodes
    store.add_nodes([n1, n2])
    graph = store.to_codegraph(repository_id="repo-xyz")

    await store.save_graph(graph)
    loaded = await store.load_graph("repo-xyz")

    assert loaded.repository_id == "repo-xyz"
    assert loaded.node_count == 2

    await store.delete_graph("repo-xyz")
    with pytest.raises(KeyError, match="No graph stored for repository ID"):
        await store.load_graph("repo-xyz")
