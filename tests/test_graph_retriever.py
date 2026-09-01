"""Unit and integration test suite for TASK-5D Phase 5 Graph Retrieval (GraphRetriever)."""

import pytest

from code_analyzer.ir import SourceLocation
from code_analyzer.parsers.models import Language
from graph.edges import GraphEdge, generate_edge_id
from graph.enums import EdgeKind, NodeKind
from graph.models import CodeGraph
from graph.nodes import GraphNode
from retrieval.enums import ChunkType
from retrieval.exceptions import GraphQueryError
from retrieval.graph_retriever import GraphRetriever
from retrieval.models import CodeChunk
from retrieval.retrieval_models import RetrievalResultSet

REPO_ALPHA = "repo-alpha"
REPO_BETA = "repo-beta"


@pytest.fixture
def graph_fixture() -> tuple[CodeGraph, dict[str, CodeChunk]]:
    """Construct a realistic multi-tier Phase 3 CodeGraph and matching CodeChunk lookup dictionary.

    Topology:
        PaymentController (CLASS) --CALLS--> PaymentService (CLASS) --CALLS--> PaymentRepository (CLASS)
        PaymentService (CLASS) --EXTENDS--> BaseService (CLASS)
        StripePaymentProcessor (CLASS) --IMPLEMENTS--> PaymentProcessor (INTERFACE)
        UserService (CLASS) --USES--> AuthService (CLASS)
        UserModule (MODULE) --IMPORTS--> AuthModule (MODULE)
    """
    graph = CodeGraph(repository_id=REPO_ALPHA)

    n_ctrl = GraphNode(
        id="chunk_ctrl",
        kind=NodeKind.CLASS,
        name="PaymentController",
        qualified_name="com.example.controller.PaymentController",
        language="java",
        file_id="src/PaymentController.java",
        location=SourceLocation(start_line=10, end_line=50, start_column=0, end_column=0),
        attributes={"commit_sha": "sha_100", "path": "src/PaymentController.java"},
    )
    n_svc = GraphNode(
        id="chunk_svc",
        kind=NodeKind.CLASS,
        name="PaymentService",
        qualified_name="com.example.service.PaymentService",
        language="java",
        file_id="src/PaymentService.java",
        location=SourceLocation(start_line=15, end_line=80, start_column=0, end_column=0),
        attributes={"commit_sha": "sha_100", "path": "src/PaymentService.java"},
    )
    n_repo = GraphNode(
        id="chunk_repo",
        kind=NodeKind.CLASS,
        name="PaymentRepository",
        qualified_name="com.example.repo.PaymentRepository",
        language="java",
        file_id="src/PaymentRepository.java",
        location=SourceLocation(start_line=5, end_line=40, start_column=0, end_column=0),
        attributes={"commit_sha": "sha_100", "path": "src/PaymentRepository.java"},
    )
    n_proc_iface = GraphNode(
        id="chunk_proc_iface",
        kind=NodeKind.INTERFACE,
        name="PaymentProcessor",
        qualified_name="com.example.service.PaymentProcessor",
        language="java",
        file_id="src/PaymentProcessor.java",
        location=SourceLocation(start_line=1, end_line=20, start_column=0, end_column=0),
        attributes={"commit_sha": "sha_100", "path": "src/PaymentProcessor.java"},
    )
    n_stripe_proc = GraphNode(
        id="chunk_stripe_proc",
        kind=NodeKind.CLASS,
        name="StripePaymentProcessor",
        qualified_name="com.example.service.StripePaymentProcessor",
        language="java",
        file_id="src/StripePaymentProcessor.java",
        location=SourceLocation(start_line=22, end_line=100, start_column=0, end_column=0),
        attributes={"commit_sha": "sha_100", "path": "src/StripePaymentProcessor.java"},
    )
    n_base = GraphNode(
        id="chunk_base",
        kind=NodeKind.CLASS,
        name="BaseService",
        qualified_name="com.example.service.BaseService",
        language="java",
        file_id="src/BaseService.java",
        location=SourceLocation(start_line=1, end_line=30, start_column=0, end_column=0),
        attributes={"commit_sha": "sha_100", "path": "src/BaseService.java"},
    )
    n_auth = GraphNode(
        id="chunk_auth",
        kind=NodeKind.CLASS,
        name="AuthService",
        qualified_name="com.example.auth.AuthService",
        language="java",
        file_id="src/AuthService.java",
        location=SourceLocation(start_line=5, end_line=60, start_column=0, end_column=0),
        attributes={"commit_sha": "sha_100", "path": "src/AuthService.java"},
    )
    n_user = GraphNode(
        id="chunk_user",
        kind=NodeKind.CLASS,
        name="UserService",
        qualified_name="com.example.user.UserService",
        language="java",
        file_id="src/UserService.java",
        location=SourceLocation(start_line=8, end_line=75, start_column=0, end_column=0),
        attributes={"commit_sha": "sha_100", "path": "src/UserService.java"},
    )

    nodes = [n_ctrl, n_svc, n_repo, n_proc_iface, n_stripe_proc, n_base, n_auth, n_user]
    graph.add_nodes(nodes)

    edges = [
        GraphEdge(
            id=generate_edge_id("chunk_ctrl", "chunk_svc", EdgeKind.CALLS),
            source_id="chunk_ctrl",
            target_id="chunk_svc",
            kind=EdgeKind.CALLS,
        ),
        GraphEdge(
            id=generate_edge_id("chunk_svc", "chunk_repo", EdgeKind.CALLS),
            source_id="chunk_svc",
            target_id="chunk_repo",
            kind=EdgeKind.CALLS,
        ),
        GraphEdge(
            id=generate_edge_id("chunk_svc", "chunk_base", EdgeKind.EXTENDS),
            source_id="chunk_svc",
            target_id="chunk_base",
            kind=EdgeKind.EXTENDS,
        ),
        GraphEdge(
            id=generate_edge_id("chunk_stripe_proc", "chunk_proc_iface", EdgeKind.IMPLEMENTS),
            source_id="chunk_stripe_proc",
            target_id="chunk_proc_iface",
            kind=EdgeKind.IMPLEMENTS,
        ),
        GraphEdge(
            id=generate_edge_id("chunk_user", "chunk_auth", EdgeKind.USES),
            source_id="chunk_user",
            target_id="chunk_auth",
            kind=EdgeKind.USES,
        ),
    ]
    graph.add_edges(edges)

    chunk_lookup: dict[str, CodeChunk] = {}
    for node in nodes:
        fpath = node.file_id or "src/File.java"
        chunk = CodeChunk(
            id=node.id,
            chunk_type=_node_kind_to_chunk_type(node.kind),
            repository_id=REPO_ALPHA,
            commit_sha="sha_100",
            file_path=fpath,
            language=Language.JAVA,
            name=node.name,
            qualified_name=node.qualified_name,
            source_location=node.location
            or SourceLocation(start_line=1, end_line=1, start_column=0, end_column=0),
            content=f"// Content for {node.name}",
        )
        chunk_lookup[node.id] = chunk

    return graph, chunk_lookup


def _node_kind_to_chunk_type(kind: NodeKind) -> ChunkType:
    if kind == NodeKind.CLASS:
        return ChunkType.CLASS_CONTEXT
    if kind == NodeKind.INTERFACE:
        return ChunkType.INTERFACE_CONTEXT
    if kind == NodeKind.FUNCTION:
        return ChunkType.FUNCTION
    if kind == NodeKind.METHOD:
        return ChunkType.METHOD
    return ChunkType.FILE_CONTEXT


# ──────────────────────────────────────────────────────────────────────────────
# 1. Structural Intent Queries (CALLS, IMPLEMENTS, EXTENDS, DEPENDS_ON)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_direct_calls_query(graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]]) -> None:
    """TC-1: 'Who calls PaymentService?' returns PaymentController as top candidate."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    res = retriever.retrieve("Who calls PaymentService?", repository_id=REPO_ALPHA)

    assert isinstance(res, RetrievalResultSet)
    assert len(res.results) == 1
    top = res.results[0]
    assert top.chunk_id == "chunk_ctrl"
    assert top.symbol_name == "PaymentController"
    assert top.metadata["graph_relationship"] == "CALLS"
    assert top.metadata["graph_direction"] == "inbound"


@pytest.mark.unit
def test_reverse_calls_query(graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]]) -> None:
    """TC-2: 'What does PaymentService call?' returns PaymentRepository."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    res = retriever.retrieve("What does PaymentService call?", repository_id=REPO_ALPHA)

    assert len(res.results) == 1
    top = res.results[0]
    assert top.chunk_id == "chunk_repo"
    assert top.symbol_name == "PaymentRepository"
    assert top.metadata["graph_relationship"] == "CALLS"
    assert top.metadata["graph_direction"] == "outbound"


@pytest.mark.unit
def test_implements_query(graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]]) -> None:
    """TC-3: 'Which classes implement PaymentProcessor?' returns StripePaymentProcessor."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    res = retriever.retrieve("Which classes implement PaymentProcessor?", repository_id=REPO_ALPHA)

    assert len(res.results) == 1
    top = res.results[0]
    assert top.chunk_id == "chunk_stripe_proc"
    assert top.symbol_name == "StripePaymentProcessor"
    assert top.metadata["graph_relationship"] == "IMPLEMENTS"


@pytest.mark.unit
def test_inherits_query(graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]]) -> None:
    """TC-4: 'What inherits from BaseService?' returns PaymentService."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    res = retriever.retrieve("What inherits from BaseService?", repository_id=REPO_ALPHA)

    assert len(res.results) == 1
    top = res.results[0]
    assert top.chunk_id == "chunk_svc"
    assert top.symbol_name == "PaymentService"
    assert top.metadata["graph_relationship"] == "EXTENDS"


@pytest.mark.unit
def test_depends_on_query(graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]]) -> None:
    """TC-5: 'Who depends on AuthService?' returns UserService."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    res = retriever.retrieve("Who depends on AuthService?", repository_id=REPO_ALPHA)

    assert len(res.results) == 1
    top = res.results[0]
    assert top.chunk_id == "chunk_user"
    assert top.symbol_name == "UserService"


@pytest.mark.unit
def test_qualified_identifier_query(
    graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]],
) -> None:
    """TC-6: Fully qualified target symbol lookup in relationship query."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    res = retriever.retrieve(
        "Who calls com.example.service.PaymentService?", repository_id=REPO_ALPHA
    )

    assert len(res.results) == 1
    assert res.results[0].chunk_id == "chunk_ctrl"


# ──────────────────────────────────────────────────────────────────────────────
# 2. Query Classification & Negative / Non-Graph Scenarios
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_non_graph_prose_query(graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]]) -> None:
    """TC-10: Pure natural-language non-graph query returns 0 candidates."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    res = retriever.retrieve("How does payment authentication work?", repository_id=REPO_ALPHA)

    assert isinstance(res, RetrievalResultSet)
    assert len(res.results) == 0
    assert res.total_matches == 0


@pytest.mark.unit
def test_zero_result_unresolved_symbol(
    graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]],
) -> None:
    """TC-13 & TC-14: Query referencing a non-existent symbol returns 0 candidates cleanly."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    res = retriever.retrieve("Who calls NonExistentService?", repository_id=REPO_ALPHA)

    assert len(res.results) == 0
    assert res.total_matches == 0


@pytest.mark.unit
def test_pure_identifier_query(graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]]) -> None:
    """TC-12: Pure identifier query returns exact target node + structural neighbors."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    res = retriever.retrieve("PaymentService", repository_id=REPO_ALPHA)

    assert len(res.results) > 0
    chunk_ids = {r.chunk_id for r in res.results}
    assert "chunk_svc" in chunk_ids  # target node itself
    assert "chunk_ctrl" in chunk_ids  # caller neighbor


# ──────────────────────────────────────────────────────────────────────────────
# 3. Repository & Version Isolation
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_repository_isolation(graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]]) -> None:
    """TC-11: Queries for repo-beta do not leak candidates from repo-alpha."""
    graph_alpha, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph_alpha, chunk_lookup=chunk_lookup)

    res_beta = retriever.retrieve("Who calls PaymentService?", repository_id=REPO_BETA)

    assert len(res_beta.results) == 0
    assert res_beta.total_matches == 0


@pytest.mark.unit
def test_version_commit_sha_filtering(
    graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]],
) -> None:
    """TC-12: Filtering candidates by commit_sha."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    # Matching commit_sha
    res_match = retriever.retrieve(
        "Who calls PaymentService?", repository_id=REPO_ALPHA, commit_sha="sha_100"
    )
    assert len(res_match.results) == 1

    # Mismatched commit_sha
    res_mismatch = retriever.retrieve(
        "Who calls PaymentService?", repository_id=REPO_ALPHA, commit_sha="sha_999"
    )
    assert len(res_mismatch.results) == 0


# ──────────────────────────────────────────────────────────────────────────────
# 4. Cycle Safety, Determinism, Immutability & Deduplication
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_cycle_safe_graph_traversal() -> None:
    """TC-17: Traversal over cyclic graph terminates cleanly without recursion error."""
    graph = CodeGraph(repository_id=REPO_ALPHA)
    n1 = GraphNode(id="c1", kind=NodeKind.CLASS, name="A", qualified_name="com.A")
    n2 = GraphNode(id="c2", kind=NodeKind.CLASS, name="B", qualified_name="com.B")
    n3 = GraphNode(id="c3", kind=NodeKind.CLASS, name="C", qualified_name="com.C")
    graph.add_nodes([n1, n2, n3])

    # Cycle: A --CALLS--> B --CALLS--> C --CALLS--> A
    graph.add_edge(
        GraphEdge(
            id=generate_edge_id("c1", "c2", EdgeKind.CALLS),
            source_id="c1",
            target_id="c2",
            kind=EdgeKind.CALLS,
        )
    )
    graph.add_edge(
        GraphEdge(
            id=generate_edge_id("c2", "c3", EdgeKind.CALLS),
            source_id="c2",
            target_id="c3",
            kind=EdgeKind.CALLS,
        )
    )
    graph.add_edge(
        GraphEdge(
            id=generate_edge_id("c3", "c1", EdgeKind.CALLS),
            source_id="c3",
            target_id="c1",
            kind=EdgeKind.CALLS,
        )
    )

    retriever = GraphRetriever(graph=graph)

    # What does A call? (Callees of A)
    res = retriever.retrieve("What does A call?", repository_id=REPO_ALPHA)
    assert len(res.results) == 1
    assert res.results[0].chunk_id == "c2"


@pytest.mark.unit
def test_deterministic_ordering_repeatability(
    graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]],
) -> None:
    """TC-16: Executing the same query 5 times produces 100% identical results."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    results_list = [
        retriever.retrieve("PaymentService", repository_id=REPO_ALPHA) for _ in range(5)
    ]

    first_ids = [r.chunk_id for r in results_list[0].results]
    first_scores = [r.score for r in results_list[0].results]

    for next_res in results_list[1:]:
        assert [r.chunk_id for r in next_res.results] == first_ids
        assert [r.score for r in next_res.results] == first_scores


@pytest.mark.unit
def test_graph_immutability(graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]]) -> None:
    """TC-23: Phase 3 graph is unmutated during search calls."""
    graph, chunk_lookup = graph_fixture
    node_count_before = graph.node_count
    edge_count_before = graph.edge_count

    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)
    retriever.retrieve("Who calls PaymentService?", repository_id=REPO_ALPHA)
    retriever.retrieve("PaymentService", repository_id=REPO_ALPHA)

    assert graph.node_count == node_count_before
    assert graph.edge_count == edge_count_before


# ──────────────────────────────────────────────────────────────────────────────
# 5. Metadata Preservation, Canonical Identity & Top-K Limiting
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_metadata_preservation_and_canonical_identity(
    graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]],
) -> None:
    """TC-18 & TC-19: Canonical chunk identity and metadata enrichment."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    res = retriever.retrieve("Who calls PaymentService?", repository_id=REPO_ALPHA)
    top = res.results[0]

    assert top.chunk_id == chunk_lookup["chunk_ctrl"].id
    assert top.file_path == chunk_lookup["chunk_ctrl"].file_path
    assert top.symbol_name == "PaymentController"
    assert top.qualified_name == "com.example.controller.PaymentController"
    assert top.start_line == 10
    assert top.end_line == 50
    assert "graph_relationship" in top.metadata
    assert "graph_direction" in top.metadata
    assert "graph_depth" in top.metadata


@pytest.mark.unit
def test_top_k_limiting(graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]]) -> None:
    """TC-20: Truncate candidate list to top_k limit."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    res = retriever.retrieve("PaymentService", repository_id=REPO_ALPHA, top_k=1)
    assert len(res.results) == 1
    assert res.total_matches > 1


@pytest.mark.unit
def test_serialization_roundtrip(graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]]) -> None:
    """TC-21: RetrievalResultSet Pydantic JSON serialization roundtrip."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    res = retriever.retrieve("Who calls PaymentService?", repository_id=REPO_ALPHA)
    json_str = res.model_dump_json()

    deserialized = RetrievalResultSet.model_validate_json(json_str)
    assert deserialized.repository_id == res.repository_id
    assert len(deserialized.results) == len(res.results)
    assert deserialized.results[0].chunk_id == res.results[0].chunk_id


@pytest.mark.unit
def test_latency_metrics_observability(
    graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]],
) -> None:
    """TC-22: Latency metrics are recorded and non-negative."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    res = retriever.retrieve("Who calls PaymentService?", repository_id=REPO_ALPHA)
    assert res.preprocessing_latency_ms >= 0.0
    assert res.retrieval_latency_ms >= 0.0
    assert res.total_latency_ms >= 0.0


@pytest.mark.unit
def test_input_validation(graph_fixture: tuple[CodeGraph, dict[str, CodeChunk]]) -> None:
    """TC-24: Input parameter validation raises GraphQueryError."""
    graph, chunk_lookup = graph_fixture
    retriever = GraphRetriever(graph=graph, chunk_lookup=chunk_lookup)

    # Empty repository_id
    with pytest.raises(GraphQueryError, match="repository_id cannot be empty"):
        retriever.retrieve("Who calls PaymentService?", repository_id="")

    # top_k <= 0
    with pytest.raises(GraphQueryError, match="top_k must be > 0"):
        retriever.retrieve("Who calls PaymentService?", repository_id=REPO_ALPHA, top_k=0)

    # Empty query
    with pytest.raises(GraphQueryError, match="Query string cannot be empty"):
        retriever.retrieve("", repository_id=REPO_ALPHA)
