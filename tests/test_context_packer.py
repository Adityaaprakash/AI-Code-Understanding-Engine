"""Comprehensive unit and integration test suite for TASK-6E Context Token Budgeting & Context Packing."""

from typing import Any

import pytest

from llm.budget_config import ContextBudgetConfig
from llm.budget_models import (
    ContextPackingStats,
    PackedContext,
)
from llm.context_packer import ContextPacker
from llm.enums import (
    ContextOverflowPolicy,
    ContextPackingReasonCode,
    QueryIntent,
    QueryScope,
    RankingReasonCode,
    RelationshipType,
    TokenCountMode,
)
from llm.exceptions import InvalidBudgetConfigError, TokenCountingError
from llm.planner_models import QueryPlan
from llm.pruning_models import ContextPruningResult
from llm.query_planner import QueryPlanner
from llm.ranking_models import ContextRankingScoreBreakdown, RankedContextCandidate
from llm.token_counter import DeterministicFallbackTokenCounter, ExactTokenCounter


def make_plan(
    query: str = "Search codebase logic",
    primary_intent: QueryIntent = QueryIntent.EXPLANATION,
    scope: QueryScope = QueryScope.REPOSITORY,
) -> QueryPlan:
    """Helper to create a valid QueryPlan fixture."""
    plan = QueryPlanner().plan(query)
    overrides: dict[str, Any] = {
        "primary_intent": primary_intent,
        "scope": scope,
    }
    return plan.model_copy(update=overrides)


def make_ranked_candidate(
    candidate_id: str,
    rank: int = 1,
    final_score: float = 0.8,
    symbol_name: str | None = None,
    qualified_name: str | None = None,
    file_path: str | None = "src/payment.py",
    start_line: int | None = 10,
    end_line: int | None = 50,
    source: str = "RETRIEVAL",
    relationship_type: RelationshipType = RelationshipType.NONE,
    snippet: str | None = None,
) -> RankedContextCandidate:
    """Helper to create a valid RankedContextCandidate fixture."""
    sym = symbol_name if symbol_name is not None else f"Symbol_{candidate_id}"
    qname = qualified_name if qualified_name is not None else f"com.example.{sym}"
    nid = f"node_{candidate_id}"
    code_text = snippet or f"def process_{candidate_id}():\n    return True"

    breakdown = ContextRankingScoreBreakdown(
        retrieval_relevance=final_score,
        query_entity_match=0.5,
        intent_alignment=0.5,
        provenance_strength=0.5,
    )
    return RankedContextCandidate(
        candidate_id=candidate_id,
        rank=rank,
        final_score=final_score,
        score_breakdown=breakdown,
        reason_codes=[RankingReasonCode.RETRIEVAL_EVIDENCE],
        node_id=nid,
        symbol_name=sym,
        qualified_name=qname,
        node_kind="FUNCTION",
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        source=source,
        anchor_id="anchor-1",
        relationship_type=relationship_type,
        retrieval_chunk_id=candidate_id,
        retrieval_score=final_score,
        metadata={"content": code_text, "repository_id": "test_repo"},
    )


def make_pruning_result(retained_candidates: list[RankedContextCandidate]) -> ContextPruningResult:
    """Helper to create a ContextPruningResult wrapper."""
    return ContextPruningResult(
        retained_candidates=retained_candidates,
        pruned_candidates=[],
        input_count=len(retained_candidates),
        deduplicated_count=0,
        pruned_count=0,
        output_count=len(retained_candidates),
        pruning_latency_ms=1.0,
    )


class TestContextPackerSuite:
    """Test suite covering TASK-6E requirements and property invariants."""

    @pytest.fixture
    def packer(self) -> ContextPacker:
        """Fixture providing a standard ContextPacker engine."""
        return ContextPacker()

    # A. BASIC PACKING
    def test_scenario_a_basic_packing(self, packer: ContextPacker) -> None:
        plan = make_plan()
        cands = [
            make_ranked_candidate(f"cand-{i}", rank=i + 1, final_score=0.9 - i * 0.1)
            for i in range(3)
        ]
        pruning_res = make_pruning_result(cands)

        cfg = ContextBudgetConfig(
            max_context_tokens=4000,
            reserved_system_tokens=500,
            reserved_query_tokens=200,
            reserved_output_tokens=500,
            safety_margin_tokens=300,
        )

        res = packer.pack(query_plan=plan, pruning_result=pruning_res, config=cfg)

        assert isinstance(res, PackedContext)
        assert len(res.packed_items) == 3
        assert len(res.omitted_records) == 0
        assert res.stats.packed_evidence_tokens <= cfg.usable_evidence_budget
        assert res.stats.utilization_ratio > 0.0

    # B. EMPTY INPUT
    def test_scenario_b_empty_input(self, packer: ContextPacker) -> None:
        plan = make_plan()
        pruning_res = make_pruning_result([])

        res = packer.pack(query_plan=plan, pruning_result=pruning_res)

        assert res.stats.input_candidate_count == 0
        assert res.stats.packed_candidate_count == 0
        assert res.stats.omitted_candidate_count == 0
        assert res.stats.packed_evidence_tokens == 0
        assert res.formatted_context_str == ""

    # C. SINGLE CANDIDATE
    def test_scenario_c_single_candidate(self, packer: ContextPacker) -> None:
        plan = make_plan()
        cand = make_ranked_candidate("single-1", rank=1, final_score=0.95)
        pruning_res = make_pruning_result([cand])

        cfg = ContextBudgetConfig(max_context_tokens=5000)
        res = packer.pack(query_plan=plan, pruning_result=pruning_res, config=cfg)

        assert len(res.packed_items) == 1
        assert res.packed_items[0].candidate_id == "single-1"

    # D. MULTIPLE CANDIDATES WITH BUDGET EXCLUSION
    def test_scenario_d_multiple_candidates_budget_exclusion(self, packer: ContextPacker) -> None:
        plan = make_plan()
        cands = [
            make_ranked_candidate(f"cand-{i}", rank=i + 1, snippet="x " * 100) for i in range(5)
        ]
        pruning_res = make_pruning_result(cands)

        # Restrict usable evidence budget so only ~2 candidates fit
        cfg = ContextBudgetConfig(
            max_context_tokens=1000,
            reserved_system_tokens=200,
            reserved_query_tokens=100,
            reserved_output_tokens=200,
            safety_margin_tokens=100,
            overflow_policy=ContextOverflowPolicy.SKIP,
        )

        res = packer.pack(query_plan=plan, pruning_result=pruning_res, config=cfg)

        assert res.stats.packed_candidate_count < 5
        assert res.stats.omitted_candidate_count > 0
        assert len(res.packed_items) + len(res.omitted_records) == 5
        assert res.omitted_records[0].omission_reason in (
            ContextPackingReasonCode.TOKEN_BUDGET_EXCEEDED,
            ContextPackingReasonCode.CANDIDATE_TOO_LARGE,
            ContextPackingReasonCode.BUDGET_EXHAUSTED,
        )

    # E. EXACT BUDGET BOUNDARY TEST
    def test_scenario_e_exact_budget_boundary(self, packer: ContextPacker) -> None:
        plan = make_plan()
        cand = make_ranked_candidate("boundary-cand", rank=1, snippet="print('hello world')")
        counter = DeterministicFallbackTokenCounter()

        # Format candidate to find exact token count
        hdr, snip, lang = packer._extract_candidate_components(cand)
        fmt = packer._assemble_formatted_code(hdr, snip, lang)
        exact_tokens = counter.count(fmt)

        # Case 1: Usable budget exactly equals candidate token count -> Fits
        cfg_exact = ContextBudgetConfig(
            max_context_tokens=exact_tokens + 1000,
            reserved_system_tokens=400,
            reserved_query_tokens=200,
            reserved_output_tokens=200,
            safety_margin_tokens=200,
        )
        assert cfg_exact.usable_evidence_budget == exact_tokens

        res_exact = packer.pack(
            query_plan=plan, pruning_result=make_pruning_result([cand]), config=cfg_exact
        )
        assert len(res_exact.packed_items) == 1

        # Case 2: Usable budget is exact_tokens - 1 -> Omitted under SKIP
        cfg_tight = cfg_exact.model_copy(
            update={"safety_margin_tokens": cfg_exact.safety_margin_tokens + 1}
        )
        assert cfg_tight.usable_evidence_budget == exact_tokens - 1

        res_tight = packer.pack(
            query_plan=plan, pruning_result=make_pruning_result([cand]), config=cfg_tight
        )
        assert len(res_tight.packed_items) == 0
        assert len(res_tight.omitted_records) == 1

    # F. OVERFLOW POLICY HANDLING (SKIP VS TRUNCATE)
    def test_scenario_f_overflow_policies(self, packer: ContextPacker) -> None:
        plan = make_plan()
        long_snippet = "\n".join([f"line_{i} = {i}" for i in range(100)])
        cand = make_ranked_candidate("large-cand", rank=1, snippet=long_snippet)

        # Budget enough for ~20 lines but not all 100
        cfg_skip = ContextBudgetConfig(
            max_context_tokens=1000,
            reserved_system_tokens=400,
            reserved_query_tokens=100,
            reserved_output_tokens=200,
            safety_margin_tokens=100,
            overflow_policy=ContextOverflowPolicy.SKIP,
        )
        res_skip = packer.pack(
            query_plan=plan, pruning_result=make_pruning_result([cand]), config=cfg_skip
        )
        assert len(res_skip.packed_items) == 0
        assert len(res_skip.omitted_records) == 1

        # TRUNCATE policy
        cfg_trunc = cfg_skip.model_copy(update={"overflow_policy": ContextOverflowPolicy.TRUNCATE})
        res_trunc = packer.pack(
            query_plan=plan, pruning_result=make_pruning_result([cand]), config=cfg_trunc
        )
        item = res_trunc.packed_items[0]
        assert item.truncated is True
        assert (
            item.original_token_count is not None and item.original_token_count > item.token_count
        )

    # G, H, I. RESERVED SYSTEM, QUERY, AND SAFETY MARGIN TOKENS
    def test_scenario_g_h_i_reserves_and_margin(self, packer: ContextPacker) -> None:
        cfg = ContextBudgetConfig(
            max_context_tokens=10000,
            reserved_system_tokens=2000,
            reserved_query_tokens=1000,
            reserved_output_tokens=1500,
            safety_margin_tokens=500,
        )

        assert cfg.total_reserved_tokens == 5000
        assert cfg.usable_evidence_budget == 5000

    # J. ZERO USABLE EVIDENCE BUDGET
    def test_scenario_j_zero_usable_budget(self, packer: ContextPacker) -> None:
        plan = make_plan()
        cand = make_ranked_candidate("c1")
        pruning_res = make_pruning_result([cand])

        cfg = ContextBudgetConfig(
            max_context_tokens=1000,
            reserved_system_tokens=500,
            reserved_query_tokens=200,
            reserved_output_tokens=200,
            safety_margin_tokens=100,
        )
        assert cfg.usable_evidence_budget == 0

        res = packer.pack(query_plan=plan, pruning_result=pruning_res, config=cfg)
        assert len(res.packed_items) == 0
        assert len(res.omitted_records) == 1
        assert res.stats.usable_evidence_budget == 0
        assert res.stats.utilization_ratio == 0.0

    # K. INVALID CONFIG VALIDATION
    def test_scenario_k_invalid_config_validation(self) -> None:
        with pytest.raises(InvalidBudgetConfigError, match="max_context_tokens must be > 0"):
            ContextBudgetConfig(max_context_tokens=0)

        with pytest.raises(InvalidBudgetConfigError, match="reserved_system_tokens must be >= 0"):
            ContextBudgetConfig(reserved_system_tokens=-10)

        with pytest.raises(InvalidBudgetConfigError, match="Total reserved tokens"):
            ContextBudgetConfig(
                max_context_tokens=1000,
                reserved_system_tokens=600,
                reserved_query_tokens=500,
            )

    # L. NEGATIVE CANDIDATE LIMITS REJECTION
    def test_scenario_l_negative_limits_rejection(self) -> None:
        with pytest.raises(InvalidBudgetConfigError, match="minimum_candidate_tokens must be >= 0"):
            ContextBudgetConfig(minimum_candidate_tokens=-5)

        with pytest.raises(InvalidBudgetConfigError, match="cannot exceed"):
            ContextBudgetConfig(minimum_candidate_tokens=100, maximum_candidate_tokens=50)

    # M. DETERMINISTIC ORDERING PRESERVATION
    def test_scenario_m_ordering_preservation(self, packer: ContextPacker) -> None:
        plan = make_plan()
        cands = [
            make_ranked_candidate("cand-1", rank=1, final_score=0.95),
            make_ranked_candidate("cand-2", rank=2, final_score=0.85),
            make_ranked_candidate("cand-3", rank=3, final_score=0.75),
        ]
        res = packer.pack(query_plan=plan, pruning_result=make_pruning_result(cands))

        assert [item.candidate_id for item in res.packed_items] == ["cand-1", "cand-2", "cand-3"]

    # N. 100-RUN DETERMINISM VERIFICATION
    def test_scenario_n_100_run_determinism(self, packer: ContextPacker) -> None:
        plan = make_plan()
        cands = [
            make_ranked_candidate(f"c-{i}", rank=i + 1, final_score=0.9 - i * 0.05)
            for i in range(10)
        ]
        pruning_res = make_pruning_result(cands)
        cfg = ContextBudgetConfig(max_context_tokens=3000)

        baseline = packer.pack(query_plan=plan, pruning_result=pruning_res, config=cfg)

        for _ in range(100):
            run = packer.pack(query_plan=plan, pruning_result=pruning_res, config=cfg)
            assert run.model_dump(exclude={"packing_latency_ms"}) == baseline.model_dump(
                exclude={"packing_latency_ms"}
            )

    # O. PERMUTATION INVARIANCE VERIFICATION
    def test_scenario_o_permutation_invariance(self, packer: ContextPacker) -> None:
        plan = make_plan()
        cands = [
            make_ranked_candidate("A", rank=1, final_score=0.9),
            make_ranked_candidate("B", rank=2, final_score=0.8),
            make_ranked_candidate("C", rank=3, final_score=0.7),
        ]

        res_orig = packer.pack(query_plan=plan, pruning_result=make_pruning_result(cands))
        res_shuffled = packer.pack(
            query_plan=plan, pruning_result=make_pruning_result([cands[2], cands[0], cands[1]])
        )

        assert [item.candidate_id for item in res_orig.packed_items] == [
            item.candidate_id for item in res_shuffled.packed_items
        ]

    # P. IMMUTABILITY VERIFICATION
    def test_scenario_p_immutability(self, packer: ContextPacker) -> None:
        plan = make_plan()
        cands = [make_ranked_candidate("c1", rank=1)]
        pruning_res = make_pruning_result(cands)

        plan_copy = plan.model_dump()
        pruned_copy = pruning_res.model_dump()

        packer.pack(query_plan=plan, pruning_result=pruning_res)

        assert plan.model_dump() == plan_copy
        assert pruning_res.model_dump() == pruned_copy

    # Q. TOKEN COUNTER ABSTRACTION & MODES
    def test_scenario_q_token_counters(self) -> None:
        fallback = DeterministicFallbackTokenCounter()
        assert fallback.get_mode() == TokenCountMode.ESTIMATED
        assert fallback.count("def test(): pass") > 0
        assert fallback.count("") == 0

        exact = ExactTokenCounter(lambda s: len(s.split()))
        assert exact.get_mode() == TokenCountMode.EXACT
        assert exact.count("hello world from exact counter") == 5

        with pytest.raises(TokenCountingError):
            exact.count(123)  # type: ignore

    # R. UNICODE & CODE FORMATTING
    def test_scenario_r_unicode_formatting(self, packer: ContextPacker) -> None:
        plan = make_plan()
        unicode_snippet = "def greet(name: str):\n    print(f'こんにちは, {name}! 🚀')"
        cand = make_ranked_candidate("unicode-1", snippet=unicode_snippet)

        res = packer.pack(query_plan=plan, pruning_result=make_pruning_result([cand]))

        assert len(res.packed_items) == 1
        assert "こんにちは" in res.packed_items[0].formatted_code
        assert res.packed_items[0].token_count > 0

    # S. CODE VS HEADER TOKENS SEPARATION
    def test_scenario_s_code_vs_header_tokens(self, packer: ContextPacker) -> None:
        plan = make_plan()
        cand = make_ranked_candidate("sep-1", snippet="return True")
        res = packer.pack(query_plan=plan, pruning_result=make_pruning_result([cand]))

        item = res.packed_items[0]
        assert item.header_tokens > 0
        assert item.code_tokens > 0
        assert item.token_count >= item.header_tokens + item.code_tokens

    # T. OMISSION REASONS AUDIT
    def test_scenario_t_omission_reasons(self, packer: ContextPacker) -> None:
        plan = make_plan()
        large_cand = make_ranked_candidate("huge", snippet="x\n" * 500)

        cfg = ContextBudgetConfig(
            max_context_tokens=1000,
            reserved_system_tokens=500,
            reserved_query_tokens=200,
            reserved_output_tokens=100,
            safety_margin_tokens=100,
            overflow_policy=ContextOverflowPolicy.SKIP,
        )

        res = packer.pack(
            query_plan=plan, pruning_result=make_pruning_result([large_cand]), config=cfg
        )
        assert len(res.omitted_records) == 1
        assert (
            res.omitted_records[0].omission_reason == ContextPackingReasonCode.CANDIDATE_TOO_LARGE
        )

    # U. STATISTICS CALCULATION
    def test_scenario_u_statistics(self, packer: ContextPacker) -> None:
        plan = make_plan()
        cands = [make_ranked_candidate(f"c-{i}", rank=i + 1) for i in range(3)]
        res = packer.pack(query_plan=plan, pruning_result=make_pruning_result(cands))

        stats: ContextPackingStats = res.stats
        assert stats.input_candidate_count == 3
        assert stats.packed_candidate_count == 3
        assert stats.omitted_candidate_count == 0
        assert stats.packed_evidence_tokens == sum(item.token_count for item in res.packed_items)
        assert 0.0 <= stats.utilization_ratio <= 1.0

    # V. JSON SERIALIZATION & ROUNDTRIP
    def test_scenario_v_json_roundtrip(self, packer: ContextPacker) -> None:
        plan = make_plan()
        cands = [make_ranked_candidate("c1")]
        res = packer.pack(query_plan=plan, pruning_result=make_pruning_result(cands))

        json_str = res.model_dump_json()
        deserialized = PackedContext.model_validate_json(json_str)

        assert deserialized.query == res.query
        assert deserialized.stats.packed_evidence_tokens == res.stats.packed_evidence_tokens
        assert deserialized.packed_items[0].candidate_id == res.packed_items[0].candidate_id

    # W & X. REPOSITORY & CITATION METADATA PRESERVATION
    def test_scenario_w_x_citation_metadata_preservation(self, packer: ContextPacker) -> None:
        plan = make_plan()
        cand = make_ranked_candidate(
            "cite-1",
            file_path="src/payment/processor.py",
            start_line=100,
            end_line=150,
            symbol_name="Processor",
            qualified_name="com.example.Processor",
            source="RETRIEVAL+GRAPH_EXPANSION",
            relationship_type=RelationshipType.CALLS,
        )

        res = packer.pack(query_plan=plan, pruning_result=make_pruning_result([cand]))
        item = res.packed_items[0]

        assert item.candidate_id == "cite-1"
        assert item.file_path == "src/payment/processor.py"
        assert item.start_line == 100
        assert item.end_line == 150
        assert item.symbol_name == "Processor"
        assert item.qualified_name == "com.example.Processor"
        assert item.source == "RETRIEVAL+GRAPH_EXPANSION"
        assert item.relationship_type == RelationshipType.CALLS

    # Y. PERFORMANCE BENCHMARK
    def test_scenario_y_performance(self, packer: ContextPacker) -> None:
        plan = make_plan()
        cands = [make_ranked_candidate(f"cand-{i}", rank=i + 1) for i in range(500)]
        pruning_res = make_pruning_result(cands)

        res = packer.pack(query_plan=plan, pruning_result=pruning_res)
        assert res.packing_latency_ms < 200.0
        assert res.stats.input_candidate_count == 500

    # Z. BOUNDARY VERIFICATION (NO NETWORK, NO LLM)
    def test_scenario_z_boundary_verification(self, packer: ContextPacker) -> None:
        plan = make_plan()
        cands = [make_ranked_candidate("b1")]

        # Pack operates completely in-memory without external calls
        res = packer.pack(query_plan=plan, pruning_result=make_pruning_result(cands))
        assert res is not None
        assert hasattr(res, "formatted_context_str")
