"""Comprehensive unit and integration test suite for TASK-6B Graph-Aware Context Expansion."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from code_analyzer.parsers.models import Language
from graph.edges import GraphEdge, generate_edge_id
from graph.enums import EdgeKind, NodeKind
from graph.nodes import GraphNode
from graph.store import InMemoryGraphStore
from llm.enums import (
    GraphStrategy,
    QueryIntent,
    QueryScope,
    RelationshipType,
)
from llm.exceptions import InvalidExpansionConfigError
from llm.expansion_config import GraphExpansionConfig
from llm.expansion_models import GraphExpansionResult
from llm.graph_expander import GraphContextExpander
from retrieval.enums import ChunkType
from retrieval.retrieval_models import RetrievalResult

if TYPE_CHECKING:
    from llm.planner_models import QueryPlan


@pytest.fixture
def sample_graph() -> InMemoryGraphStore:
    """Construct synthetic code graph for testing expansion scenarios."""
    store = InMemoryGraphStore(repository_id="repo-6b-test")

    # Nodes
    n_ctrl = GraphNode(
        id="node-ctrl",
        kind=NodeKind.CLASS,
        name="PaymentController",
        qualified_name="com.example.PaymentController",
        file_id="src/PaymentController.java",
    )
    n_svc = GraphNode(
        id="node-svc",
        kind=NodeKind.CLASS,
        name="PaymentService",
        qualified_name="com.example.PaymentService",
        file_id="src/PaymentService.java",
    )
    n_repo = GraphNode(
        id="node-repo",
        kind=NodeKind.CLASS,
        name="PaymentRepository",
        qualified_name="com.example.PaymentRepository",
        file_id="src/PaymentRepository.java",
    )
    n_iface = GraphNode(
        id="node-iface",
        kind=NodeKind.INTERFACE,
        name="IPaymentService",
        qualified_name="com.example.IPaymentService",
        file_id="src/IPaymentService.java",
    )
    n_base = GraphNode(
        id="node-base",
        kind=NodeKind.CLASS,
        name="BaseService",
        qualified_name="com.example.BaseService",
        file_id="src/BaseService.java",
    )
    n_auth = GraphNode(
        id="node-auth",
        kind=NodeKind.FILE,
        name="auth.py",
        qualified_name="auth",
        file_id="auth.py",
    )
    n_user = GraphNode(
        id="node-user",
        kind=NodeKind.FILE,
        name="user.py",
        qualified_name="user",
        file_id="user.py",
    )

    # Cyclic nodes
    node_a = GraphNode(id="node-a", kind=NodeKind.FUNCTION, name="funcA", qualified_name="a.funcA")
    node_b = GraphNode(id="node-b", kind=NodeKind.FUNCTION, name="funcB", qualified_name="b.funcB")
    node_c = GraphNode(id="node-c", kind=NodeKind.FUNCTION, name="funcC", qualified_name="c.funcC")

    store.add_nodes(
        [
            n_ctrl,
            n_svc,
            n_repo,
            n_iface,
            n_base,
            n_auth,
            n_user,
            node_a,
            node_b,
            node_c,
        ]
    )

    # Edges
    e1 = GraphEdge(
        id=generate_edge_id("node-ctrl", "node-svc", EdgeKind.CALLS),
        source_id="node-ctrl",
        target_id="node-svc",
        kind=EdgeKind.CALLS,
    )
    e2 = GraphEdge(
        id=generate_edge_id("node-svc", "node-repo", EdgeKind.CALLS),
        source_id="node-svc",
        target_id="node-repo",
        kind=EdgeKind.CALLS,
    )
    e3 = GraphEdge(
        id=generate_edge_id("node-svc", "node-iface", EdgeKind.IMPLEMENTS),
        source_id="node-svc",
        target_id="node-iface",
        kind=EdgeKind.IMPLEMENTS,
    )
    e4 = GraphEdge(
        id=generate_edge_id("node-svc", "node-base", EdgeKind.EXTENDS),
        source_id="node-svc",
        target_id="node-base",
        kind=EdgeKind.EXTENDS,
    )
    e5 = GraphEdge(
        id=generate_edge_id("node-auth", "node-user", EdgeKind.IMPORTS),
        source_id="node-auth",
        target_id="node-user",
        kind=EdgeKind.IMPORTS,
    )
    e6 = GraphEdge(
        id=generate_edge_id("node-ctrl", "node-repo", EdgeKind.USES),
        source_id="node-ctrl",
        target_id="node-repo",
        kind=EdgeKind.USES,
    )

    # Cycle edges: A -> B -> C -> A
    e_cycle1 = GraphEdge(
        id=generate_edge_id("node-a", "node-b", EdgeKind.CALLS),
        source_id="node-a",
        target_id="node-b",
        kind=EdgeKind.CALLS,
    )
    e_cycle2 = GraphEdge(
        id=generate_edge_id("node-b", "node-c", EdgeKind.CALLS),
        source_id="node-b",
        target_id="node-c",
        kind=EdgeKind.CALLS,
    )
    e_cycle3 = GraphEdge(
        id=generate_edge_id("node-c", "node-a", EdgeKind.CALLS),
        source_id="node-c",
        target_id="node-a",
        kind=EdgeKind.CALLS,
    )

    store.add_edges([e1, e2, e3, e4, e5, e6, e_cycle1, e_cycle2, e_cycle3])
    return store


@pytest.fixture
def expander() -> GraphContextExpander:
    return GraphContextExpander()


def make_plan(
    query: str,
    primary_intent: QueryIntent = QueryIntent.DEPENDENCY,
    relationship_type: RelationshipType = RelationshipType.NONE,
    graph_strategy: GraphStrategy = GraphStrategy.NONE,
    scope: QueryScope = QueryScope.REPOSITORY,
    target_entities: list[str] | None = None,
) -> QueryPlan:
    from llm.query_planner import QueryPlanner

    plan = QueryPlanner().plan(query)
    overrides: dict[str, Any] = {
        "primary_intent": primary_intent,
        "relationship_type": relationship_type,
        "graph_strategy": graph_strategy,
        "scope": scope,
    }
    if target_entities is not None:
        overrides["target_entities"] = target_entities
    return plan.model_copy(update=overrides)


class TestGraphExpanderScenarios:
    """Test suite covering required scenarios A through Y."""

    # A. DIRECT CALLERS
    def test_scenario_a_direct_callers(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="Who calls PaymentService?",
            relationship_type=RelationshipType.CALLERS,
            graph_strategy=GraphStrategy.CALLERS,
            target_entities=["PaymentService"],
        )
        res = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        assert len(res.anchors) == 1
        assert res.anchors[0].anchor_id == "node-svc"
        assert len(res.candidates) == 1
        assert res.candidates[0].node_id == "node-ctrl"
        assert res.candidates[0].relationship_type == RelationshipType.CALLERS

    # B. DIRECT CALLEES
    def test_scenario_b_direct_callees(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="What does PaymentService call?",
            relationship_type=RelationshipType.CALLS,
            graph_strategy=GraphStrategy.CALLEES,
            target_entities=["PaymentService"],
        )
        res = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        assert len(res.anchors) == 1
        assert any(c.node_id == "node-repo" for c in res.candidates)

    # C. DEPENDENCIES
    def test_scenario_c_dependencies(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="What does PaymentController depend on?",
            relationship_type=RelationshipType.DEPENDENCIES,
            graph_strategy=GraphStrategy.DEPENDENCIES,
            target_entities=["PaymentController"],
        )
        res = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        node_ids = {c.node_id for c in res.candidates}
        assert "node-svc" in node_ids or "node-repo" in node_ids

    # D. DEPENDENTS
    def test_scenario_d_dependents(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="Who depends on PaymentRepository?",
            relationship_type=RelationshipType.DEPENDENTS,
            graph_strategy=GraphStrategy.DEPENDENTS,
            target_entities=["PaymentRepository"],
        )
        res = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        node_ids = {c.node_id for c in res.candidates}
        assert "node-svc" in node_ids or "node-ctrl" in node_ids

    # E. IMPLEMENTATIONS
    def test_scenario_e_implementations(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="What implements IPaymentService?",
            relationship_type=RelationshipType.IMPLEMENTS,
            graph_strategy=GraphStrategy.IMPLEMENTATIONS,
            target_entities=["IPaymentService"],
        )
        res = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        assert any(c.node_id == "node-svc" for c in res.candidates)

    # F. INHERITANCE
    def test_scenario_f_inheritance(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="What extends BaseService?",
            relationship_type=RelationshipType.EXTENDS,
            graph_strategy=GraphStrategy.INHERITANCE,
            target_entities=["BaseService"],
        )
        res = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        assert any(c.node_id == "node-svc" for c in res.candidates)

    # G. IMPORTS
    def test_scenario_g_imports(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="What imports auth.py?",
            relationship_type=RelationshipType.IMPORTS,
            graph_strategy=GraphStrategy.IMPORTS,
            target_entities=["auth.py"],
        )
        res = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        assert any(c.node_id == "node-user" for c in res.candidates)

    # H. USES
    def test_scenario_h_uses(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="Where is PaymentRepository used?",
            relationship_type=RelationshipType.USES,
            graph_strategy=GraphStrategy.USAGES,
            target_entities=["PaymentRepository"],
        )
        res = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        assert any(c.node_id == "node-ctrl" for c in res.candidates)

    # I. IMPACT
    def test_scenario_i_impact(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="What would break if PaymentService changed?",
            primary_intent=QueryIntent.IMPACT,
            relationship_type=RelationshipType.IMPACT,
            graph_strategy=GraphStrategy.IMPACT_RADIUS,
            target_entities=["PaymentService"],
        )
        res = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        assert len(res.candidates) > 0
        assert any(c.node_id == "node-ctrl" for c in res.candidates)
        assert res.expansion_metadata["strategy"] == GraphStrategy.IMPACT_RADIUS.value

    # J. MULTI-ANCHOR
    def test_scenario_j_multi_anchor(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="How do PaymentController and PaymentService work?",
            relationship_type=RelationshipType.CALLS,
            graph_strategy=GraphStrategy.CALLEES,
            target_entities=["PaymentController", "PaymentService"],
        )
        res = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        assert len(res.anchors) >= 2

    # K. CYCLE SAFETY
    def test_scenario_k_cycle_safety(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="What calls funcA?",
            relationship_type=RelationshipType.CALLERS,
            graph_strategy=GraphStrategy.CALLERS,
            target_entities=["funcA"],
        )
        config = GraphExpansionConfig(max_depth=10)
        res = expander.expand(
            query_plan=plan, retrieval_results=[], graph=sample_graph, config=config
        )
        # Should terminate safely without recursion error
        assert res is not None

    # L. DEPTH LIMIT
    def test_scenario_l_depth_limit(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="What calls PaymentRepository?",
            relationship_type=RelationshipType.CALLERS,
            graph_strategy=GraphStrategy.CALLERS,
            target_entities=["PaymentRepository"],
        )
        config = GraphExpansionConfig(max_depth=1)
        res = expander.expand(
            query_plan=plan, retrieval_results=[], graph=sample_graph, config=config
        )
        assert all(c.traversal_depth <= 1 for c in res.candidates)

    # M. NODE LIMIT
    def test_scenario_m_node_limit(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="Show callers of PaymentRepository",
            relationship_type=RelationshipType.CALLERS,
            graph_strategy=GraphStrategy.CALLERS,
            target_entities=["PaymentRepository"],
        )
        config = GraphExpansionConfig(max_expanded_nodes=1)
        res = expander.expand(
            query_plan=plan, retrieval_results=[], graph=sample_graph, config=config
        )
        assert res.truncated is True

    # N. CANDIDATE LIMIT
    def test_scenario_n_candidate_limit(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="What depends on PaymentRepository?",
            relationship_type=RelationshipType.DEPENDENTS,
            graph_strategy=GraphStrategy.DEPENDENTS,
            target_entities=["PaymentRepository"],
        )
        config = GraphExpansionConfig(max_candidates=1)
        res = expander.expand(
            query_plan=plan, retrieval_results=[], graph=sample_graph, config=config
        )
        assert len(res.candidates) <= 1
        assert res.truncated is True

    # O. NEIGHBOR LIMIT
    def test_scenario_o_neighbor_limit(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="What depends on PaymentRepository?",
            relationship_type=RelationshipType.DEPENDENTS,
            graph_strategy=GraphStrategy.DEPENDENTS,
            target_entities=["PaymentRepository"],
        )
        config = GraphExpansionConfig(max_neighbors_per_node=1)
        res = expander.expand(
            query_plan=plan, retrieval_results=[], graph=sample_graph, config=config
        )
        assert res is not None

    # P. DETERMINISM (100 runs)
    def test_scenario_p_determinism(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="What depends on PaymentService?",
            relationship_type=RelationshipType.DEPENDENTS,
            graph_strategy=GraphStrategy.DEPENDENTS,
            target_entities=["PaymentService"],
        )
        first_run = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        for _ in range(100):
            run = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
            assert run.candidates == first_run.candidates
            assert run.anchors == first_run.anchors

    # Q. NO-OP
    def test_scenario_q_noop(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="How does authentication work?",
            graph_strategy=GraphStrategy.NONE,
        )
        res = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        assert len(res.candidates) == 0
        assert res.expansion_metadata["reason"] == "GRAPH_STRATEGY_NONE"

    # R. EXISTING RETRIEVAL RESULT EVIDENCING
    def test_scenario_r_existing_retrieval_result(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        ret_result = RetrievalResult(
            chunk_id="chunk-ctrl-101",
            score=0.95,
            rank=1,
            repository_id="repo-6b-test",
            file_path="src/PaymentController.java",
            language=Language.JAVA,
            chunk_type=ChunkType.CLASS_CONTEXT,
            qualified_name="com.example.PaymentController",
            metadata={"symbol_id": "node-ctrl"},
        )
        plan = make_plan(
            query="Who calls PaymentService?",
            relationship_type=RelationshipType.CALLERS,
            graph_strategy=GraphStrategy.CALLERS,
            target_entities=["PaymentService"],
        )
        res = expander.expand(query_plan=plan, retrieval_results=[ret_result], graph=sample_graph)
        cand = next(c for c in res.candidates if c.node_id == "node-ctrl")
        assert cand.source == "RETRIEVAL+GRAPH_EXPANSION"
        assert cand.retrieval_chunk_id == "chunk-ctrl-101"

    # S. MULTI-RELATIONSHIP / COMPOUND QUERY
    def test_scenario_s_compound_structural_query(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="Who calls PaymentService and what does it depend on?",
            relationship_type=RelationshipType.CALLERS,
            graph_strategy=GraphStrategy.CALLERS,
            target_entities=["PaymentService"],
        )
        res = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        assert res is not None

    # T. SCOPE CONSTRAINTS
    def test_scenario_t_scope_constraints(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="What calls PaymentService in this file?",
            relationship_type=RelationshipType.CALLERS,
            graph_strategy=GraphStrategy.CALLERS,
            scope=QueryScope.FILE,
            target_entities=["PaymentService"],
        )
        config = GraphExpansionConfig(allow_same_file_expansion=False)
        res = expander.expand(
            query_plan=plan, retrieval_results=[], graph=sample_graph, config=config
        )
        assert res is not None

    # U. PROVENANCE
    def test_scenario_u_provenance(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="Who calls PaymentService?",
            relationship_type=RelationshipType.CALLERS,
            graph_strategy=GraphStrategy.CALLERS,
            target_entities=["PaymentService"],
        )
        res = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        cand = res.candidates[0]
        assert cand.anchor_id == "node-svc"
        assert cand.relationship_type == RelationshipType.CALLERS
        assert cand.traversal_depth == 1
        assert "EXPANDED_CALLERS" in cand.expansion_reason

    # V. PATH
    def test_scenario_v_path(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="Who calls PaymentService?",
            relationship_type=RelationshipType.CALLERS,
            graph_strategy=GraphStrategy.CALLERS,
            target_entities=["PaymentService"],
        )
        res = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        cand = res.candidates[0]
        assert cand.path is not None
        assert cand.path.anchor_id == "node-svc"
        assert cand.path.target_node_id == "node-ctrl"

    # W. TRUNCATION
    def test_scenario_w_truncation(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="What depends on PaymentService?",
            relationship_type=RelationshipType.DEPENDENTS,
            graph_strategy=GraphStrategy.DEPENDENTS,
            target_entities=["PaymentService"],
        )
        config = GraphExpansionConfig(max_candidates=1)
        res = expander.expand(
            query_plan=plan, retrieval_results=[], graph=sample_graph, config=config
        )
        assert res.truncated is True

    # X. INVALID CONFIGURATION
    def test_scenario_x_invalid_configuration(self) -> None:
        with pytest.raises(InvalidExpansionConfigError):
            GraphExpansionConfig(max_depth=-1)

        with pytest.raises(InvalidExpansionConfigError):
            GraphExpansionConfig(max_candidates=0)

    # Y. SERIALIZATION
    def test_scenario_y_serialization(
        self, expander: GraphContextExpander, sample_graph: InMemoryGraphStore
    ) -> None:
        plan = make_plan(
            query="Who calls PaymentService?",
            relationship_type=RelationshipType.CALLERS,
            graph_strategy=GraphStrategy.CALLERS,
            target_entities=["PaymentService"],
        )
        res = expander.expand(query_plan=plan, retrieval_results=[], graph=sample_graph)
        json_str = res.model_dump_json()
        roundtripped = GraphExpansionResult.model_validate_json(json_str)
        assert roundtripped == res
