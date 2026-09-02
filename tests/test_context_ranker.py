"""Comprehensive unit and integration test suite for TASK-6C Context Ranking."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from code_analyzer.parsers.models import Language
from llm.context_ranker import ContextRanker
from llm.enums import (
    AnswerStyle,
    QueryIntent,
    QueryScope,
    RankingReasonCode,
    RelationshipType,
)
from llm.exceptions import InvalidRankingConfigError
from llm.expansion_models import GraphExpansionCandidate
from llm.query_planner import QueryPlanner
from llm.ranking_config import ContextRankingConfig
from llm.ranking_models import ContextRankingResult
from retrieval.enums import ChunkType, RetrievalSource
from retrieval.retrieval_models import RetrievalResult

if TYPE_CHECKING:
    from llm.planner_models import QueryPlan


@pytest.fixture
def ranker() -> ContextRanker:
    return ContextRanker()


@pytest.fixture
def planner() -> QueryPlanner:
    return QueryPlanner()


def make_plan(
    query: str,
    primary_intent: QueryIntent = QueryIntent.DEPENDENCY,
    relationship_type: RelationshipType = RelationshipType.NONE,
    target_entities: list[str] | None = None,
    scope: QueryScope = QueryScope.REPOSITORY,
    answer_style: AnswerStyle = AnswerStyle.EXPLANATION,
) -> QueryPlan:
    plan = QueryPlanner().plan(query)
    overrides: dict[str, Any] = {
        "primary_intent": primary_intent,
        "relationship_type": relationship_type,
        "scope": scope,
        "answer_style": answer_style,
    }
    if target_entities is not None:
        overrides["target_entities"] = target_entities
    return plan.model_copy(update=overrides)


def make_graph_candidate(
    candidate_id: str,
    node_id: str,
    symbol_name: str | None = None,
    qualified_name: str | None = None,
    node_kind: str = "CLASS",
    file_path: str | None = "src/payment.py",
    source: str = "GRAPH_EXPANSION",
    anchor_id: str = "anchor-1",
    relationship_type: RelationshipType = RelationshipType.CALLS,
    traversal_depth: int = 1,
    retrieval_chunk_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GraphExpansionCandidate:
    return GraphExpansionCandidate(
        candidate_id=candidate_id,
        node_id=node_id,
        symbol_name=symbol_name,
        qualified_name=qualified_name,
        node_kind=node_kind,
        file_path=file_path,
        start_line=10,
        end_line=50,
        source=source,
        anchor_id=anchor_id,
        relationship_type=relationship_type,
        traversal_depth=traversal_depth,
        expansion_reason=f"EXPANDED_{relationship_type.value.upper()}",
        retrieval_chunk_id=retrieval_chunk_id,
        metadata=metadata or {},
    )


def make_retrieval_candidate(
    chunk_id: str,
    score: float = 0.8,
    file_path: str = "src/payment.py",
    symbol_name: str | None = None,
    qualified_name: str | None = None,
    chunk_type: ChunkType = ChunkType.CLASS_CONTEXT,
    rerank_score: float | None = None,
    fused_score: float | None = None,
    sources: list[RetrievalSource] | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        score=score,
        rank=1,
        repository_id="repo-6c-test",
        file_path=file_path,
        language=Language.PYTHON,
        chunk_type=chunk_type,
        symbol_name=symbol_name,
        qualified_name=qualified_name,
        start_line=1,
        end_line=20,
        rerank_score=rerank_score,
        fused_score=fused_score,
        sources=sources or [RetrievalSource.BM25],
    )


class TestContextRankerScenarios:
    """Test suite covering scenarios A through T and property invariants."""

    # A. BASIC RANKING
    def test_scenario_a_basic_ranking(self, ranker: ContextRanker) -> None:
        plan = make_plan("Explain PaymentService", target_entities=["PaymentService"])
        c1 = make_graph_candidate(
            "cand-1", "node-1", symbol_name="PaymentService", traversal_depth=1
        )
        c2 = make_graph_candidate(
            "cand-2", "node-2", symbol_name="UnrelatedHelper", traversal_depth=3
        )
        res = ranker.rank(query_plan=plan, candidates=[c2, c1])

        assert len(res.ranked_candidates) == 2
        assert res.ranked_candidates[0].candidate_id == "cand-1"
        assert res.ranked_candidates[0].rank == 1
        assert res.ranked_candidates[1].candidate_id == "cand-2"
        assert res.ranked_candidates[1].rank == 2

    # B. DIRECT QUERY TARGET
    def test_scenario_b_direct_query_target(self, ranker: ContextRanker) -> None:
        plan = make_plan("What is PaymentService?", target_entities=["PaymentService"])
        target_cand = make_graph_candidate(
            "target",
            "n1",
            symbol_name="PaymentService",
            qualified_name="com.example.PaymentService",
        )
        other_cand = make_graph_candidate("other", "n2", symbol_name="Logger")

        res = ranker.rank(query_plan=plan, candidates=[other_cand, target_cand])
        first = res.ranked_candidates[0]
        assert first.candidate_id == "target"
        assert RankingReasonCode.DIRECT_QUERY_TARGET in first.reason_codes
        assert RankingReasonCode.SAME_SYMBOL in first.reason_codes

    # C. PRIMARY INTENT
    def test_scenario_c_primary_intent_callers(self, ranker: ContextRanker) -> None:
        plan = make_plan(
            "Who calls PaymentService?",
            primary_intent=QueryIntent.DEPENDENCY,
            relationship_type=RelationshipType.CALLERS,
            target_entities=["PaymentService"],
        )
        caller_cand = make_graph_candidate(
            "caller", "n1", relationship_type=RelationshipType.CALLERS
        )
        unrelated_cand = make_graph_candidate(
            "unrelated", "n2", relationship_type=RelationshipType.NONE
        )

        res = ranker.rank(query_plan=plan, candidates=[unrelated_cand, caller_cand])
        first = res.ranked_candidates[0]
        assert first.candidate_id == "caller"
        assert RankingReasonCode.PRIMARY_INTENT_MATCH in first.reason_codes

    # D. RELATIONSHIP ALIGNMENT
    def test_scenario_d_relationship_alignment(self, ranker: ContextRanker) -> None:
        plan = make_plan(
            "Show callees of AuthService",
            relationship_type=RelationshipType.CALLS,
            target_entities=["AuthService"],
        )
        exact_rel = make_graph_candidate("exact", "n1", relationship_type=RelationshipType.CALLS)
        other_rel = make_graph_candidate("other", "n2", relationship_type=RelationshipType.IMPORTS)

        res = ranker.rank(query_plan=plan, candidates=[other_rel, exact_rel])
        first = res.ranked_candidates[0]
        assert first.candidate_id == "exact"
        assert RankingReasonCode.RELATIONSHIP_MATCH in first.reason_codes

    # E. GRAPH PROXIMITY
    def test_scenario_e_graph_proximity(self, ranker: ContextRanker) -> None:
        plan = make_plan("Dependencies of TokenStore")
        depth1 = make_graph_candidate("depth1", "n1", traversal_depth=1)
        depth3 = make_graph_candidate("depth3", "n2", traversal_depth=3)

        res = ranker.rank(query_plan=plan, candidates=[depth3, depth1])
        assert res.ranked_candidates[0].candidate_id == "depth1"
        assert (
            res.ranked_candidates[0].score_breakdown.graph_proximity
            > res.ranked_candidates[1].score_breakdown.graph_proximity
        )

    # F. MULTI-SOURCE EVIDENCE
    def test_scenario_f_multi_source_evidence(self, ranker: ContextRanker) -> None:
        plan = make_plan("Find AuthController")
        multi = make_graph_candidate("multi", "n1", source="RETRIEVAL+GRAPH_EXPANSION")
        single = make_graph_candidate("single", "n2", source="GRAPH_EXPANSION")

        res = ranker.rank(query_plan=plan, candidates=[single, multi])
        first = res.ranked_candidates[0]
        assert first.candidate_id == "multi"
        assert RankingReasonCode.MULTI_SOURCE_EVIDENCE in first.reason_codes

    # G. RETRIEVAL SCORE
    def test_scenario_g_retrieval_score(self, ranker: ContextRanker) -> None:
        plan = make_plan("Search payment logic")
        high_ret = make_retrieval_candidate("high", score=0.95, rerank_score=0.95)
        low_ret = make_retrieval_candidate("low", score=0.20, rerank_score=0.20)

        res = ranker.rank(query_plan=plan, candidates=[low_ret, high_ret])
        assert res.ranked_candidates[0].candidate_id == "high"

    # H. SCOPE
    def test_scenario_h_scope_matching(self, ranker: ContextRanker) -> None:
        plan = make_plan(
            "Check PaymentController.java",
            scope=QueryScope.FILE,
            target_entities=["PaymentController.java"],
        )
        file_cand = make_graph_candidate("file-cand", "n1", file_path="PaymentController.java")
        other_file = make_graph_candidate("other-cand", "n2", file_path="OtherFile.java")

        res = ranker.rank(query_plan=plan, candidates=[other_file, file_cand])
        first = res.ranked_candidates[0]
        assert first.candidate_id == "file-cand"
        assert RankingReasonCode.SCOPE_MATCH in first.reason_codes

    # I. ANSWER STYLE
    def test_scenario_i_answer_style(self, ranker: ContextRanker) -> None:
        plan = make_plan("Where is PaymentService located?", answer_style=AnswerStyle.CODE_LOCATION)
        loc_cand = make_graph_candidate("loc", "n1", file_path="src/payment.py")
        no_loc = make_graph_candidate("noloc", "n2", file_path=None)

        res = ranker.rank(query_plan=plan, candidates=[no_loc, loc_cand])
        assert res.ranked_candidates[0].candidate_id == "loc"

    # J. SYMBOL MATCHING
    def test_scenario_j_symbol_matching(self, ranker: ContextRanker) -> None:
        plan = make_plan("Explain UserService", target_entities=["UserService"])
        exact = make_graph_candidate("exact", "n1", symbol_name="UserService")
        partial = make_graph_candidate("partial", "n2", symbol_name="UserServiceHelper")
        unrelated = make_graph_candidate("unrelated", "n3", symbol_name="DatabaseConnection")

        res = ranker.rank(query_plan=plan, candidates=[unrelated, partial, exact])
        ids = [c.candidate_id for c in res.ranked_candidates]
        assert ids == ["exact", "partial", "unrelated"]

    # K. TIE BREAKING
    def test_scenario_k_tie_breaking(self, ranker: ContextRanker) -> None:
        plan = make_plan("Query")
        # Identical parameters except candidate_id
        c_b = make_graph_candidate("cand-b", "n-b", symbol_name="Same")
        c_a = make_graph_candidate("cand-a", "n-a", symbol_name="Same")

        res = ranker.rank(query_plan=plan, candidates=[c_b, c_a])
        assert [c.candidate_id for c in res.ranked_candidates] == ["cand-a", "cand-b"]

    # L. DETERMINISM (100 runs)
    def test_scenario_l_determinism_100_runs(self, ranker: ContextRanker) -> None:
        plan = make_plan("Explain PaymentService", target_entities=["PaymentService"])
        c1 = make_graph_candidate("c1", "n1", symbol_name="PaymentService")
        c2 = make_retrieval_candidate("c2", score=0.85, symbol_name="PaymentService")
        c3 = make_graph_candidate("c3", "n3", symbol_name="PaymentRepository")

        first_run = ranker.rank(query_plan=plan, candidates=[c3, c1, c2])

        for _ in range(100):
            run = ranker.rank(query_plan=plan, candidates=[c3, c1, c2])
            assert [c.candidate_id for c in run.ranked_candidates] == [
                c.candidate_id for c in first_run.ranked_candidates
            ]
            assert [c.final_score for c in run.ranked_candidates] == [
                c.final_score for c in first_run.ranked_candidates
            ]
            assert [c.reason_codes for c in run.ranked_candidates] == [
                c.reason_codes for c in first_run.ranked_candidates
            ]

    # M. EMPTY INPUT
    def test_scenario_m_empty_input(self, ranker: ContextRanker) -> None:
        plan = make_plan("Empty query")
        res = ranker.rank(query_plan=plan, candidates=[])
        assert res.total_candidates == 0
        assert len(res.ranked_candidates) == 0

    # N. MISSING METADATA
    def test_scenario_n_missing_metadata(self, ranker: ContextRanker) -> None:
        plan = make_plan("Missing metadata test")
        bare_cand = GraphExpansionCandidate(
            candidate_id="bare",
            node_id="bare-node",
            node_kind="UNKNOWN",
            anchor_id="anchor",
            relationship_type=RelationshipType.NONE,
            traversal_depth=0,
            expansion_reason="NONE",
        )
        res = ranker.rank(query_plan=plan, candidates=[bare_cand])
        assert res.total_candidates == 1
        assert res.ranked_candidates[0].candidate_id == "bare"

    # O. INVALID CONFIGURATION
    def test_scenario_o_invalid_configuration(self) -> None:
        with pytest.raises(InvalidRankingConfigError):
            ContextRankingConfig(
                weight_retrieval_relevance=0.0,
                weight_query_entity_match=0.0,
                weight_intent_alignment=0.0,
                weight_relationship_alignment=0.0,
                weight_provenance_strength=0.0,
                weight_graph_proximity=0.0,
                weight_scope_alignment=0.0,
                weight_locality=0.0,
            )

    # P. SERIALIZATION
    def test_scenario_p_serialization(self, ranker: ContextRanker) -> None:
        plan = make_plan("Serialization test", target_entities=["PaymentService"])
        c1 = make_graph_candidate("c1", "n1", symbol_name="PaymentService")
        res = ranker.rank(query_plan=plan, candidates=[c1])

        json_str = res.model_dump_json()
        roundtripped = ContextRankingResult.model_validate_json(json_str)
        assert roundtripped == res

    # Q. NO PRUNING
    def test_scenario_q_no_pruning(self, ranker: ContextRanker) -> None:
        plan = make_plan("Pruning check")
        low_score_cands = [
            make_graph_candidate(f"cand-{i}", f"n-{i}", symbol_name="Irrelevant") for i in range(10)
        ]
        res = ranker.rank(query_plan=plan, candidates=low_score_cands)
        assert res.total_candidates == 10
        assert len(res.ranked_candidates) == 10

    # R. NO GRAPH TRAVERSAL
    def test_scenario_r_no_graph_traversal(self, ranker: ContextRanker) -> None:
        plan = make_plan("No graph traversal")
        cand = make_graph_candidate("c1", "n1")
        # Ranker should operate without any graph store dependency passed
        res = ranker.rank(query_plan=plan, candidates=[cand])
        assert res.total_candidates == 1

    # S. PROVENANCE PRESERVATION
    def test_scenario_s_provenance_preservation(self, ranker: ContextRanker) -> None:
        plan = make_plan("Provenance test")
        g_cand = make_graph_candidate(
            "gc1", "gn1", source="RETRIEVAL+GRAPH_EXPANSION", anchor_id="anc-123"
        )
        r_cand = make_retrieval_candidate("rc1", score=0.9, chunk_type=ChunkType.FUNCTION)

        res = ranker.rank(query_plan=plan, candidates=[g_cand, r_cand])

        gc_ranked = next(c for c in res.ranked_candidates if c.candidate_id == "gc1")
        rc_ranked = next(c for c in res.ranked_candidates if c.candidate_id == "rc1")

        assert gc_ranked.anchor_id == "anc-123"
        assert gc_ranked.source == "RETRIEVAL+GRAPH_EXPANSION"
        assert rc_ranked.retrieval_chunk_id == "rc1"
        assert rc_ranked.retrieval_score == 0.9

    # T. COMPOUND QUERY
    def test_scenario_t_compound_query(self, ranker: ContextRanker) -> None:
        plan = make_plan(
            "Who calls PaymentService and what does it depend on?",
            primary_intent=QueryIntent.DEPENDENCY,
            relationship_type=RelationshipType.CALLERS,
            target_entities=["PaymentService"],
        )
        cand1 = make_graph_candidate(
            "c1", "n1", symbol_name="PaymentController", relationship_type=RelationshipType.CALLERS
        )
        cand2 = make_graph_candidate(
            "c2",
            "n2",
            symbol_name="PaymentRepository",
            relationship_type=RelationshipType.DEPENDENCIES,
        )

        res = ranker.rank(query_plan=plan, candidates=[cand2, cand1])
        assert res.total_candidates == 2
        assert res.ranked_candidates[0].candidate_id == "c1"

    # PERMUTATION INVARIANCE PROPERTY TEST
    def test_permutation_invariance(self, ranker: ContextRanker) -> None:
        plan = make_plan("Invariance test", target_entities=["PaymentService"])
        c1 = make_graph_candidate("c1", "n1", symbol_name="PaymentService")
        c2 = make_graph_candidate("c2", "n2", symbol_name="PaymentController")
        c3 = make_retrieval_candidate("c3", score=0.9, symbol_name="PaymentService")
        c4 = make_graph_candidate("c4", "n4", symbol_name="OtherService")

        perm1 = ranker.rank(query_plan=plan, candidates=[c1, c2, c3, c4])
        perm2 = ranker.rank(query_plan=plan, candidates=[c4, c2, c1, c3])
        perm3 = ranker.rank(query_plan=plan, candidates=[c3, c1, c4, c2])

        order1 = [c.candidate_id for c in perm1.ranked_candidates]
        order2 = [c.candidate_id for c in perm2.ranked_candidates]
        order3 = [c.candidate_id for c in perm3.ranked_candidates]

        assert order1 == order2 == order3
