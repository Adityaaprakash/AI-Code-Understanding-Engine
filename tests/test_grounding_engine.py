"""Test suite for Grounding Verification Engine (TASK-6H)."""

import pytest

from llm.answer_models import GeneratedAnswer
from llm.budget_models import ContextPackingStats, PackedContext, PackedContextItem
from llm.enums import (
    CitationStatus,
    ClaimStatus,
    ContextOverflowPolicy,
    GroundingReasonCode,
    GroundingStatus,
    LLMFinishReason,
    QueryIntent,
    RelationshipType,
    TokenCountMode,
)
from llm.exceptions import InvalidGroundingConfigError
from llm.grounding_config import GroundingVerificationConfig
from llm.grounding_engine import GroundingEngine


@pytest.fixture
def engine() -> GroundingEngine:
    return GroundingEngine()


@pytest.fixture
def config() -> GroundingVerificationConfig:
    return GroundingVerificationConfig()


def get_mock_context() -> PackedContext:
    item1 = PackedContextItem(
        candidate_id="item-123",
        rank=1,
        final_score=0.9,
        repository_id="repo1",
        file_path="auth.py",
        start_line=1,
        end_line=10,
        symbol_name="login",
        qualified_name="pkg.login",
        node_id="n1",
        node_kind="function",
        source="RETRIEVAL",
        relationship_type=RelationshipType.NONE,
        formatted_code="FILE: auth.py\n\n```python\n# This method delegates authentication to the provider.\ndef login(): pass\n```",
        code_tokens=10,
        header_tokens=5,
        token_count=15,
        truncated=False,
        original_token_count=15,
        reason_codes=[],
    )
    item2 = PackedContextItem(
        candidate_id="item-456",
        rank=2,
        final_score=0.8,
        repository_id="repo1",
        file_path="db.py",
        start_line=1,
        end_line=10,
        symbol_name="saveUser",
        qualified_name="pkg.saveUser",
        node_id="n2",
        node_kind="function",
        source="RETRIEVAL",
        relationship_type=RelationshipType.NONE,
        formatted_code="FILE: db.py\n\n```python\n# Helper to save users\ndef saveUser(): pass\n```",
        code_tokens=10,
        header_tokens=5,
        token_count=15,
        truncated=False,
        original_token_count=15,
        reason_codes=[],
    )

    return PackedContext(
        query="login process",
        query_plan_summary={},
        packed_items=[item1, item2],
        omitted_records=[],
        stats=ContextPackingStats(
            total_model_context_limit=1000,
            reserved_system_tokens=10,
            reserved_query_tokens=10,
            reserved_output_tokens=10,
            safety_margin_tokens=10,
            usable_evidence_budget=600,
            packed_evidence_tokens=30,
            remaining_evidence_budget=570,
            utilization_ratio=0.1,
            input_candidate_count=2,
            packed_candidate_count=2,
            omitted_candidate_count=0,
            token_count_mode=TokenCountMode.EXACT,
            overflow_policy=ContextOverflowPolicy.SKIP,
        ),
        formatted_context_str="...",
        packing_latency_ms=1.0,
    )


def get_mock_answer(answer_text: str = "") -> GeneratedAnswer:
    return GeneratedAnswer(
        query="login process",
        intent=QueryIntent.EXPLANATION,
        answer_text=answer_text,
        provider_name="fake",
        model_name="fake-model",
        input_tokens=10,
        output_tokens=10,
        total_tokens=20,
        generation_latency_ms=1.5,
        finish_reason=LLMFinishReason.STOP,
        context_item_count=2,
        context_token_count=30,
        metadata={"answer_id": "ans-1"},
    )


class TestGroundingEngine:
    # A. Basic citation extraction
    # E. Valid citation resolution
    # G. Claim extraction
    def test_valid_citation_resolution(
        self, engine: GroundingEngine, config: GroundingVerificationConfig
    ) -> None:
        context = get_mock_context()
        answer = get_mock_answer("The login delegates authentication. [CTX:item-123]")
        result = engine.verify(answer, context, config)

        assert len(result.claims) == 1
        claim = result.claims[0]
        assert claim.status == ClaimStatus.SUPPORTED
        assert len(claim.citations) == 1
        assert claim.citations[0].status == CitationStatus.VALID
        print("citations list", claim.citations)
        assert claim.citations[0].context_id == "item-123"
        assert GroundingReasonCode.VALID_CITATION in claim.reason_codes
        assert result.overall_status == GroundingStatus.SUPPORTED

    # B. Multiple citations
    def test_multiple_citations(
        self, engine: GroundingEngine, config: GroundingVerificationConfig
    ) -> None:
        context = get_mock_context()
        answer = get_mock_answer("Login and save. [CTX:item-123] [CTX:item-456]")
        result = engine.verify(answer, context, config)

        assert len(result.claims) == 1
        claim = result.claims[0]
        assert len(claim.citations) == 2
        assert claim.citations[0].context_id == "item-123"
        assert claim.citations[1].context_id == "item-456"

    # C. Malformed citation
    def test_malformed_citation(
        self, engine: GroundingEngine, config: GroundingVerificationConfig
    ) -> None:
        context = get_mock_context()
        answer = get_mock_answer("This has empty context blocks. [CTX:]")
        result = engine.verify(answer, context, config)

        claim = result.claims[0]
        assert claim.citations[0].status == CitationStatus.MALFORMED
        assert GroundingReasonCode.MALFORMED_CITATION in claim.reason_codes

    # D. Unknown citation
    def test_unknown_citation(
        self, engine: GroundingEngine, config: GroundingVerificationConfig
    ) -> None:
        context = get_mock_context()
        answer = get_mock_answer("This references missing items. [CTX:item-999]")
        result = engine.verify(answer, context, config)

        claim = result.claims[0]
        assert claim.citations[0].status == CitationStatus.MISSING
        assert GroundingReasonCode.UNKNOWN_CONTEXT_ID in claim.reason_codes

    # I. Uncited claim
    def test_uncited_claim(
        self, engine: GroundingEngine, config: GroundingVerificationConfig
    ) -> None:
        context = get_mock_context()
        answer = get_mock_answer("This is a factual claim without citation.")
        result = engine.verify(answer, context, config)

        claim = result.claims[0]
        assert claim.status == ClaimStatus.UNCITED
        assert GroundingReasonCode.UNCITED_CLAIM in claim.reason_codes

    # J. Unsupported claim
    def test_unsupported_claim(
        self, engine: GroundingEngine, config: GroundingVerificationConfig
    ) -> None:
        # Context has nothing about 'foobar' or 'baz'
        context = get_mock_context()
        answer = get_mock_answer("Foobar accesses baz completely unrelated. [CTX:item-123]")
        result = engine.verify(answer, context, config)

        claim = result.claims[0]
        assert claim.status == ClaimStatus.UNSUPPORTED
        assert claim.evidence_score < config.supported_threshold

    # M. Empty context
    def test_empty_context(
        self, engine: GroundingEngine, config: GroundingVerificationConfig
    ) -> None:
        context = get_mock_context()
        context = context.model_copy(update={"packed_items": []})
        answer = get_mock_answer("Statement. [CTX:item-123]")

        result = engine.verify(answer, context, config)
        assert result.overall_status == GroundingStatus.UNVERIFIABLE
        assert result.metrics.valid_citations == 0

    # N. Empty answer
    def test_empty_answer(
        self, engine: GroundingEngine, config: GroundingVerificationConfig
    ) -> None:
        context = get_mock_context()
        answer = get_mock_answer("")
        result = engine.verify(answer, context, config)

        assert len(result.claims) == 0
        assert result.overall_status == GroundingStatus.UNVERIFIABLE

    # O. Citation coverage / P. Grounding coverage
    def test_metrics_calculation(
        self, engine: GroundingEngine, config: GroundingVerificationConfig
    ) -> None:
        context = get_mock_context()
        answer = get_mock_answer(
            "Delegates login. [CTX:item-123]\nUncited claim.\nBad citation. [CTX:item-999]"
        )
        result = engine.verify(answer, context, config)

        assert result.metrics.total_claims == 3
        assert result.metrics.uncited_claims == 1
        assert result.metrics.supported_claims == 1
        assert result.metrics.invalid_citations == 1

        # 1 valid out of 2 total
        assert result.metrics.valid_citations == 1

        # 2 claims have citations / 3 claims = 2/3
        assert result.metrics.citation_coverage == pytest.approx(2.0 / 3.0)
        assert result.metrics.grounding_coverage == pytest.approx(1.0 / 3.0)

    # R. Threshold behavior
    def test_invalid_config_thresholds(self) -> None:
        with pytest.raises(InvalidGroundingConfigError):
            GroundingVerificationConfig(supported_threshold=0.4, partial_threshold=0.6)

    # Y. Determinism across 100 runs
    def test_100_run_determinism(
        self, engine: GroundingEngine, config: GroundingVerificationConfig
    ) -> None:
        context = get_mock_context()
        answer = get_mock_answer("The login delegates authentication. [CTX:item-123]")
        baseline = engine.verify(answer, context, config).model_dump_json()

        for _ in range(100):
            res = engine.verify(answer, context, config).model_dump_json()
            assert res == baseline

    # X. JSON serialization
    def test_json_serialization(
        self, engine: GroundingEngine, config: GroundingVerificationConfig
    ) -> None:
        context = get_mock_context()
        answer = get_mock_answer("Login. [CTX:item-123]")
        result = engine.verify(answer, context, config)
        js = result.model_dump_json()
        assert "valid" in js
        assert "supported" in js
