"""Comprehensive unit and integration test suite for TASK-6D Context Deduplication & Pruning."""

from typing import Any

import pytest

from llm.context_pruner import ContextPruner
from llm.enums import (
    PruningReasonCode,
    QueryIntent,
    QueryScope,
    RankingReasonCode,
    RelationshipType,
)
from llm.exceptions import InvalidPruningConfigError
from llm.planner_models import QueryPlan
from llm.pruning_config import ContextPruningConfig
from llm.pruning_models import ContextPruningResult
from llm.query_planner import QueryPlanner
from llm.ranking_models import (
    ContextRankingResult,
    ContextRankingScoreBreakdown,
    RankedContextCandidate,
)


@pytest.fixture
def pruner() -> ContextPruner:
    return ContextPruner()


@pytest.fixture
def planner() -> QueryPlanner:
    return QueryPlanner()


def make_plan(
    query: str = "Search codebase logic",
    primary_intent: QueryIntent = QueryIntent.EXPLANATION,
    relationship_type: RelationshipType = RelationshipType.NONE,
    target_entities: list[str] | None = None,
    scope: QueryScope = QueryScope.REPOSITORY,
) -> QueryPlan:
    plan = QueryPlanner().plan(query)
    overrides: dict[str, Any] = {
        "primary_intent": primary_intent,
        "relationship_type": relationship_type,
        "scope": scope,
        "target_entities": [] if target_entities is None else target_entities,
    }
    return plan.model_copy(update=overrides)


def make_ranked_candidate(
    candidate_id: str,
    final_score: float = 0.8,
    symbol_name: str | None = None,
    qualified_name: str | None = None,
    file_path: str | None = "src/payment.py",
    start_line: int | None = None,
    end_line: int | None = None,
    source: str = "RETRIEVAL",
    relationship_type: RelationshipType = RelationshipType.NONE,
    traversal_depth: int = 0,
    reason_codes: list[str] | None = None,
    retrieval_chunk_id: str | None = None,
    retrieval_score: float | None = 0.8,
    node_id: str | None = None,
    node_kind: str | None = "CLASS",
) -> RankedContextCandidate:
    sym = symbol_name if symbol_name is not None else f"Symbol_{candidate_id}"
    qname = qualified_name if qualified_name is not None else f"com.example.{sym}"
    nid = node_id if node_id is not None else f"node_{candidate_id}"

    breakdown = ContextRankingScoreBreakdown(
        retrieval_relevance=final_score,
        query_entity_match=0.0,
        intent_alignment=0.5,
        relationship_alignment=0.0,
        provenance_strength=0.9 if "+" in source else 0.5,
        graph_proximity=1.0 / (1.0 + traversal_depth * 0.5),
        scope_alignment=0.5,
        locality=0.5,
    )
    return RankedContextCandidate(
        candidate_id=candidate_id,
        rank=1,
        final_score=final_score,
        score_breakdown=breakdown,
        reason_codes=reason_codes or [RankingReasonCode.RETRIEVAL_EVIDENCE],
        node_id=nid,
        symbol_name=sym,
        qualified_name=qname,
        node_kind=node_kind,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        source=source,
        anchor_id="anchor-1",
        relationship_type=relationship_type,
        traversal_depth=traversal_depth,
        retrieval_chunk_id=retrieval_chunk_id or candidate_id,
        retrieval_score=retrieval_score,
        metadata={},
    )


class TestContextPrunerScenarios:
    """Test suite covering scenarios A through X for Context Deduplication & Pruning."""

    # A. EMPTY INPUT
    def test_scenario_a_empty_input(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        res = pruner.prune(query_plan=plan, candidates=[])
        assert res.input_count == 0
        assert res.output_count == 0
        assert res.deduplicated_count == 0
        assert res.pruned_count == 0
        assert len(res.retained_candidates) == 0

    # B. SINGLE CANDIDATE
    def test_scenario_b_single_candidate(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        c1 = make_ranked_candidate("cand-1")
        res = pruner.prune(query_plan=plan, candidates=[c1])
        assert res.input_count == 1
        assert res.output_count == 1
        assert res.retained_candidates[0].candidate_id == "cand-1"

    # C. EXACT DUPLICATE
    def test_scenario_c_exact_duplicate(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        c1 = make_ranked_candidate("cand-1", retrieval_chunk_id="chunk-100")
        c2 = make_ranked_candidate("cand-2", retrieval_chunk_id="chunk-100")

        res = pruner.prune(query_plan=plan, candidates=[c1, c2])
        assert res.input_count == 2
        assert res.output_count == 1
        assert res.deduplicated_count == 1
        assert res.pruned_candidates[0].pruning_reason == PruningReasonCode.EXACT_DUPLICATE

    # D. LOGICAL DUPLICATE
    def test_scenario_d_logical_duplicate(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        c1 = make_ranked_candidate(
            "cand-1", qualified_name="com.example.PaymentService", final_score=0.9
        )
        c2 = make_ranked_candidate(
            "cand-2", qualified_name="com.example.PaymentService", final_score=0.7
        )

        res = pruner.prune(query_plan=plan, candidates=[c1, c2])
        assert res.input_count == 2
        assert res.output_count == 1
        assert res.deduplicated_count == 1
        assert res.retained_candidates[0].candidate_id == "cand-1"
        assert res.pruned_candidates[0].pruning_reason == PruningReasonCode.LOGICAL_DUPLICATE

    # E. MULTI-SOURCE DUPLICATE EVIDENCE MERGING
    def test_scenario_e_multi_source_duplicate(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        c_ret = make_ranked_candidate(
            "cand-ret", source="RETRIEVAL", qualified_name="com.example.PaymentService"
        )
        c_graph = make_ranked_candidate(
            "cand-graph", source="GRAPH_EXPANSION", qualified_name="com.example.PaymentService"
        )

        res = pruner.prune(query_plan=plan, candidates=[c_ret, c_graph])
        assert res.output_count == 1
        retained = res.retained_candidates[0]
        assert retained.source == "RETRIEVAL+GRAPH_EXPANSION"
        assert RankingReasonCode.MULTI_SOURCE_EVIDENCE in retained.reason_codes

    # F. PROVENANCE PRESERVATION
    def test_scenario_f_provenance_preservation(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        c1 = make_ranked_candidate(
            "cand-1",
            qualified_name="com.example.Service",
            reason_codes=[RankingReasonCode.SAME_FILE],
        )
        c2 = make_ranked_candidate(
            "cand-2",
            qualified_name="com.example.Service",
            reason_codes=[RankingReasonCode.RELATIONSHIP_MATCH],
        )

        res = pruner.prune(query_plan=plan, candidates=[c1, c2])
        retained = res.retained_candidates[0]
        assert RankingReasonCode.SAME_FILE in retained.reason_codes
        assert RankingReasonCode.RELATIONSHIP_MATCH in retained.reason_codes
        assert "merged_candidate_ids" in retained.metadata

    # G. DETERMINISTIC SURVIVOR SELECTION
    def test_scenario_g_deterministic_survivor_selection(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        c_low = make_ranked_candidate("cand-b", final_score=0.5, qualified_name="com.example.Same")
        c_high = make_ranked_candidate("cand-a", final_score=0.9, qualified_name="com.example.Same")

        res = pruner.prune(query_plan=plan, candidates=[c_low, c_high])
        assert res.retained_candidates[0].candidate_id == "cand-a"

    # H. NEAR DUPLICATE DETECTION
    def test_scenario_h_near_duplicate(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        c1 = make_ranked_candidate(
            "cand-1", file_path="src/payment.py", start_line=10, end_line=50, symbol_name="process"
        )
        c2 = make_ranked_candidate(
            "cand-2", file_path="src/payment.py", start_line=10, end_line=50, symbol_name="process"
        )

        cfg = ContextPruningConfig(
            enable_near_duplicate_detection=True, near_duplicate_threshold=0.8
        )
        res = pruner.prune(query_plan=plan, candidates=[c1, c2], config=cfg)
        assert res.output_count == 1
        assert res.deduplicated_count == 1

    # I. NEAR DUPLICATE DISABLED
    def test_scenario_i_near_duplicate_disabled(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        c1 = make_ranked_candidate(
            "cand-1", file_path="src/payment.py", start_line=10, end_line=50, qualified_name="q1"
        )
        c2 = make_ranked_candidate(
            "cand-2", file_path="src/payment.py", start_line=60, end_line=100, qualified_name="q2"
        )

        cfg = ContextPruningConfig(enable_near_duplicate_detection=False)
        res = pruner.prune(query_plan=plan, candidates=[c1, c2], config=cfg)
        assert res.output_count == 2
        assert res.deduplicated_count == 0

    # J. SCORE THRESHOLD PRUNING
    def test_scenario_j_score_threshold(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        c_high = make_ranked_candidate("high", final_score=0.85)
        c_low = make_ranked_candidate("low", final_score=0.25)

        cfg = ContextPruningConfig(minimum_score=0.50)
        res = pruner.prune(query_plan=plan, candidates=[c_high, c_low], config=cfg)
        assert res.output_count == 1
        assert res.retained_candidates[0].candidate_id == "high"
        assert res.pruned_candidates[0].pruning_reason == PruningReasonCode.BELOW_SCORE_THRESHOLD

    # K. TOP-K MAX CANDIDATES PRUNING
    def test_scenario_k_top_k(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        cands = [
            make_ranked_candidate(f"cand-{i}", final_score=0.9 - (i * 0.05), qualified_name=f"q{i}")
            for i in range(10)
        ]

        cfg = ContextPruningConfig(max_candidates=3)
        res = pruner.prune(query_plan=plan, candidates=cands, config=cfg)
        assert res.output_count == 3
        assert res.pruned_count == 7
        assert res.pruned_candidates[0].pruning_reason == PruningReasonCode.MAX_CANDIDATES_EXCEEDED

    # L. PRIMARY TARGET PRESERVATION
    def test_scenario_l_primary_target_preservation(self, pruner: ContextPruner) -> None:
        plan = make_plan("Explain PaymentService", target_entities=["PaymentService"])
        target_cand = make_ranked_candidate(
            "target",
            final_score=0.20,
            symbol_name="PaymentService",
            reason_codes=[RankingReasonCode.DIRECT_QUERY_TARGET],
        )
        other_cands = [
            make_ranked_candidate(
                f"other-{i}", final_score=0.9 - (i * 0.05), qualified_name=f"other{i}"
            )
            for i in range(5)
        ]

        cfg = ContextPruningConfig(minimum_score=0.50, preserve_primary_targets=True)
        res = pruner.prune(query_plan=plan, candidates=[*other_cands, target_cand], config=cfg)

        retained_ids = [c.candidate_id for c in res.retained_candidates]

        assert "target" in retained_ids

    # M. STRUCTURAL COVERAGE PROTECTION
    def test_scenario_m_structural_coverage(self, pruner: ContextPruner) -> None:
        plan = make_plan("Show callers of AuthService", relationship_type=RelationshipType.CALLERS)
        rel_cand = make_ranked_candidate(
            "rel",
            final_score=0.30,
            relationship_type=RelationshipType.CALLERS,
            reason_codes=[RankingReasonCode.RELATIONSHIP_MATCH],
        )

        cfg = ContextPruningConfig(minimum_score=0.50, preserve_structural_coverage=True)
        res = pruner.prune(query_plan=plan, candidates=[rel_cand], config=cfg)
        assert res.output_count == 1
        assert res.retained_candidates[0].candidate_id == "rel"

    # N. GRAPH PATH PRESERVATION
    def test_scenario_n_graph_path_preservation(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        graph_cand = make_ranked_candidate(
            "g1",
            source="GRAPH_EXPANSION",
            traversal_depth=2,
            relationship_type=RelationshipType.DEPENDENCIES,
            reason_codes=[RankingReasonCode.PRIMARY_INTENT_MATCH],
        )

        cfg = ContextPruningConfig(preserve_structural_coverage=True)
        res = pruner.prune(query_plan=plan, candidates=[graph_cand], config=cfg)
        assert res.output_count == 1
        assert res.retained_candidates[0].candidate_id == "g1"

    # O. MULTI-SOURCE PRIORITY
    def test_scenario_o_multi_source_priority(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        multi_cand = make_ranked_candidate(
            "multi",
            source="RETRIEVAL+GRAPH_EXPANSION",
            reason_codes=[RankingReasonCode.MULTI_SOURCE_EVIDENCE],
        )

        cfg = ContextPruningConfig(preserve_multi_source_evidence=True)
        res = pruner.prune(query_plan=plan, candidates=[multi_cand], config=cfg)
        assert res.output_count == 1
        assert res.retained_candidates[0].candidate_id == "multi"

    # P. PER-SYMBOL REDUNDANCY PRUNING
    def test_scenario_p_per_symbol_redundancy(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        s_cands = [
            make_ranked_candidate(
                f"cand-{i}",
                final_score=0.9 - (i * 0.1),
                symbol_name="PaymentService",
                qualified_name=f"PaymentService.method_{i}",
                node_id=f"node-method-{i}",
            )
            for i in range(5)
        ]

        cfg = ContextPruningConfig(max_candidates_per_symbol=2)
        res = pruner.prune(query_plan=plan, candidates=s_cands, config=cfg)
        assert res.output_count == 2
        assert res.pruned_count == 3
        assert res.pruned_candidates[0].pruning_reason == PruningReasonCode.REDUNDANT_SYMBOL

    # Q. PER-FILE REDUNDANCY PRUNING
    def test_scenario_q_per_file_redundancy(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        f_cands = [
            make_ranked_candidate(
                f"cand-{i}",
                final_score=0.9 - (i * 0.1),
                file_path="src/payment.py",
                qualified_name=f"q{i}",
            )
            for i in range(5)
        ]

        cfg = ContextPruningConfig(max_candidates_per_file=2)
        res = pruner.prune(query_plan=plan, candidates=f_cands, config=cfg)
        assert res.output_count == 2
        assert res.pruned_count == 3
        assert res.pruned_candidates[0].pruning_reason == PruningReasonCode.REDUNDANT_FILE

    # R. DETERMINISTIC OUTPUT (100 RUNS)
    def test_scenario_r_determinism_100_runs(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        cands = [
            make_ranked_candidate("c1", final_score=0.9, qualified_name="q1"),
            make_ranked_candidate("c2", final_score=0.9, qualified_name="q1"),
            make_ranked_candidate("c3", final_score=0.7, qualified_name="q2"),
        ]

        first_run = pruner.prune(query_plan=plan, candidates=cands)

        for _ in range(100):
            run = pruner.prune(query_plan=plan, candidates=cands)
            assert [c.candidate_id for c in run.retained_candidates] == [
                c.candidate_id for c in first_run.retained_candidates
            ]
            assert [p.candidate_id for p in run.pruned_candidates] == [
                p.candidate_id for p in first_run.pruned_candidates
            ]

    # S. PERMUTATION INVARIANCE
    def test_scenario_s_permutation_invariance(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        c1 = make_ranked_candidate("c1", final_score=0.9, qualified_name="q1")
        c2 = make_ranked_candidate("c2", final_score=0.8, qualified_name="q2")
        c3 = make_ranked_candidate("c3", final_score=0.7, qualified_name="q3")
        c4 = make_ranked_candidate("c4", final_score=0.6, qualified_name="q4")

        cfg = ContextPruningConfig(max_candidates=2)
        perm1 = pruner.prune(query_plan=plan, candidates=[c1, c2, c3, c4], config=cfg)
        perm2 = pruner.prune(query_plan=plan, candidates=[c4, c2, c1, c3], config=cfg)
        perm3 = pruner.prune(query_plan=plan, candidates=[c3, c1, c4, c2], config=cfg)

        ids1 = [c.candidate_id for c in perm1.retained_candidates]
        ids2 = [c.candidate_id for c in perm2.retained_candidates]
        ids3 = [c.candidate_id for c in perm3.retained_candidates]

        assert ids1 == ids2 == ids3

    # T. EXPLAINABILITY AUDIT TRAIL
    def test_scenario_t_explainability(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        c1 = make_ranked_candidate("c1", final_score=0.10)
        cfg = ContextPruningConfig(minimum_score=0.50)
        res = pruner.prune(query_plan=plan, candidates=[c1], config=cfg)

        assert res.pruned_count == 1
        record = res.pruned_candidates[0]
        assert record.candidate_id == "c1"
        assert record.pruning_reason == PruningReasonCode.BELOW_SCORE_THRESHOLD
        assert "below minimum threshold" in record.details

    # U. INVALID CONFIGURATION
    def test_scenario_u_invalid_configuration(self) -> None:
        with pytest.raises(InvalidPruningConfigError):
            ContextPruningConfig(minimum_score=-0.5)

        with pytest.raises(InvalidPruningConfigError):
            ContextPruningConfig(max_candidates=0)

        with pytest.raises(InvalidPruningConfigError):
            ContextPruningConfig(near_duplicate_threshold=1.5)

    # V. MODEL SERIALIZATION
    def test_scenario_v_serialization(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        c1 = make_ranked_candidate("c1")
        res = pruner.prune(query_plan=plan, candidates=[c1])

        json_str = res.model_dump_json()
        roundtripped = ContextPruningResult.model_validate_json(json_str)
        assert roundtripped == res

    # W. CONTEXT RANKING RESULT INTEGRATION
    def test_scenario_w_ranking_result_integration(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        c1 = make_ranked_candidate("c1")
        ranking_result = ContextRankingResult(
            ranked_candidates=[c1], total_candidates=1, ranking_latency_ms=1.0
        )
        res = pruner.prune(query_plan=plan, candidates=ranking_result)
        assert res.output_count == 1
        assert res.retained_candidates[0].candidate_id == "c1"


class TestContextPrunerNegativeConstraints:
    """Negative tests verifying TASK-6D boundary constraints."""

    def test_does_not_mutate_input_candidates(self, pruner: ContextPruner) -> None:
        plan = make_plan()
        c1 = make_ranked_candidate("c1", final_score=0.9, qualified_name="q1")
        c2 = make_ranked_candidate("c2", final_score=0.8, qualified_name="q1")

        orig_c1_rank = c1.rank
        orig_c1_source = c1.source

        pruner.prune(query_plan=plan, candidates=[c1, c2])

        assert c1.rank == orig_c1_rank
        assert c1.source == orig_c1_source

    def test_does_not_mutate_query_plan(self, pruner: ContextPruner) -> None:
        plan = make_plan("Initial query")
        c1 = make_ranked_candidate("c1")

        orig_query = plan.query
        pruner.prune(query_plan=plan, candidates=[c1])

        assert plan.query == orig_query
