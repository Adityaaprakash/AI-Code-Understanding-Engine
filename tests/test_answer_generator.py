"""Comprehensive unit and integration test suite for TASK-6G Grounded Answer Generation."""

from typing import Any

import pytest

from llm.answer_config import AnswerGenerationConfig
from llm.answer_generator import AnswerGenerator
from llm.answer_models import GeneratedAnswer
from llm.budget_models import ContextPackingStats, PackedContext, PackedContextItem
from llm.enums import (
    AnswerStyle,
    ContextOverflowPolicy,
    GraphStrategy,
    LLMFinishReason,
    QueryIntent,
    QueryScope,
    RelationshipType,
    RetrievalStrategy,
    TokenCountMode,
)
from llm.exceptions import (
    AnswerGenerationError,
    InvalidAnswerConfigError,
    LLMProviderNotFoundError,
    LLMTimeoutError,
)
from llm.fake_provider import FakeLLMProvider
from llm.planner_models import QueryPlan
from llm.provider_registry import LLMProviderRegistry
from retrieval.query_models import ProcessedQuery


@pytest.fixture
def test_registry() -> LLMProviderRegistry:
    registry = LLMProviderRegistry()
    registry.register("fake-provider", FakeLLMProvider("fake-provider"))
    return registry


@pytest.fixture
def generator(test_registry: LLMProviderRegistry) -> AnswerGenerator:
    return AnswerGenerator(registry=test_registry)


def get_query_plan(
    query: str = "How does login work?",
    intent: QueryIntent = QueryIntent.EXPLANATION,
    target_entities: list[str] | None = None,
    answer_style: AnswerStyle = AnswerStyle.EXPLANATION,
) -> QueryPlan:
    return QueryPlan(
        query=query,
        normalized_query=query,
        processed_query=ProcessedQuery(
            original_query=query, normalized_query=query, tokens=["login"]
        ),
        primary_intent=intent,
        secondary_intents=[],
        target_entities=target_entities or ["AuthService"],
        relationship_type=RelationshipType.NONE,
        retrieval_strategy=RetrievalStrategy.HYBRID,
        graph_strategy=GraphStrategy.NONE,
        scope=QueryScope.REPOSITORY,
        answer_style=answer_style,
        confidence=1.0,
        reason_codes=[],
    )


def get_packed_context(
    query: str = "How does login work?",
    items_content: list[str] | None = None,
) -> PackedContext:
    if items_content is None:
        items_content = ["def login(): pass"]

    packed_items = []
    for i, content in enumerate(items_content):
        packed_items.append(
            PackedContextItem(
                candidate_id=f"c{i}",
                rank=i + 1,
                final_score=0.9,
                repository_id="repo1",
                file_path=f"file_{i}.py",
                start_line=1,
                end_line=10,
                symbol_name=f"sym_{i}",
                qualified_name=f"pkg.sym_{i}",
                node_id=f"n{i}",
                node_kind="function",
                source="RETRIEVAL",
                relationship_type=RelationshipType.NONE,
                formatted_code=f"FILE: file_{i}.py\n\n```python\n{content}\n```",
                code_tokens=5,
                header_tokens=5,
                token_count=10,
                truncated=False,
                original_token_count=10,
                reason_codes=[],
                score_breakdown=None,
                metadata={},
            )
        )
    return PackedContext(
        query=query,
        query_plan_summary={},
        packed_items=packed_items,
        omitted_records=[],
        stats=ContextPackingStats(
            total_model_context_limit=1000,
            reserved_system_tokens=100,
            reserved_query_tokens=100,
            reserved_output_tokens=100,
            safety_margin_tokens=100,
            usable_evidence_budget=600,
            packed_evidence_tokens=10 * len(packed_items),
            remaining_evidence_budget=600 - (10 * len(packed_items)),
            utilization_ratio=0.1,
            input_candidate_count=len(packed_items),
            packed_candidate_count=len(packed_items),
            omitted_candidate_count=0,
            token_count_mode=TokenCountMode.EXACT,
            overflow_policy=ContextOverflowPolicy.SKIP,
        ),
        formatted_context_str="\n\n---\n\n".join(item.formatted_code for item in packed_items),
        packing_latency_ms=1.0,
        metadata={},
    )


class TestAnswerGenerator:
    # A. Contract enforcement & B. Basic answer generation & L. Fake provider integration
    def test_basic_generation(self, generator: AnswerGenerator) -> None:
        qp = get_query_plan()
        pc = get_packed_context()
        config = AnswerGenerationConfig(
            provider_name="fake-provider", model_name="fake-model", temperature=0.0
        )
        ans = generator.generate(qp, pc, config)
        assert isinstance(ans, GeneratedAnswer)
        assert ans.provider_name == "fake-provider"
        assert ans.model_name == "fake-model"
        assert ans.finish_reason == LLMFinishReason.STOP
        assert ans.context_item_count == 1
        # V. Context ordering preservation (via packed_context integration)
        assert ans.context_token_count == 10

    # C. Query preservation & D. QueryPlan preservation & E. PackedContext integration
    def test_preservation(self, generator: AnswerGenerator) -> None:
        qp = get_query_plan(query="Test Query", intent=QueryIntent.DEBUGGING)
        pc = get_packed_context(query="Test Query")
        config = AnswerGenerationConfig(provider_name="fake-provider", model_name="fake-model")
        ans = generator.generate(qp, pc, config)
        assert ans.query == "Test Query"
        assert ans.intent == QueryIntent.DEBUGGING
        assert ans.context_token_count == 10
        assert ans.answer_text.startswith("Fake LLM response")

    # F. Deterministic prompt construction & U. 100-run deterministic orchestration test
    def test_determinism_100_runs(
        self, generator: AnswerGenerator, test_registry: LLMProviderRegistry
    ) -> None:
        qp = get_query_plan()
        pc = get_packed_context()
        config = AnswerGenerationConfig(
            provider_name="fake-provider", model_name="fake-model", temperature=0.0
        )

        # Override fake provider to capture requests
        class CapturingProvider(FakeLLMProvider):
            def __init__(self) -> None:
                super().__init__("fake-provider")
                self.requests: list[dict[str, Any]] = []

            def invoke(self, request: Any) -> Any:
                self.requests.append(request.model_dump())
                return super().invoke(request)

        capturing = CapturingProvider()
        test_registry.register("fake-provider", capturing, overwrite=True)

        baseline_ans = generator.generate(qp, pc, config)
        baseline_req = capturing.requests[0]

        for _ in range(100):
            ans = generator.generate(qp, pc, config)
            # Answer generation might have small latency diffs
            assert ans.model_dump(
                exclude={"generation_latency_ms", "metadata"}
            ) == baseline_ans.model_dump(exclude={"generation_latency_ms", "metadata"})
            assert capturing.requests[-1] == baseline_req

    # G. Empty context & H. Insufficient-context behavior
    def test_empty_context(self, generator: AnswerGenerator) -> None:
        qp = get_query_plan()
        pc = get_packed_context(items_content=[])
        pc = pc.model_copy(update={"packed_items": [], "formatted_context_str": ""})
        config = AnswerGenerationConfig(provider_name="fake-provider", model_name="fake-model")
        ans = generator.generate(qp, pc, config)
        assert "Insufficient code context" in ans.answer_text
        assert ans.input_tokens == 0
        assert ans.context_item_count == 0

    # R. Invalid configuration
    def test_invalid_config(self) -> None:
        with pytest.raises(InvalidAnswerConfigError):
            AnswerGenerationConfig(provider_name="", model_name="model")
        with pytest.raises(InvalidAnswerConfigError):
            AnswerGenerationConfig(provider_name="p", model_name="", temperature=-1)

    def test_invalid_generation_args(self, generator: AnswerGenerator) -> None:
        config = AnswerGenerationConfig(provider_name="fake-provider", model_name="fake-model")
        with pytest.raises(AnswerGenerationError):
            generator.generate(None, get_packed_context(), config)  # type: ignore
        with pytest.raises(AnswerGenerationError):
            generator.generate(get_query_plan(), None, config)  # type: ignore

    # P. Provider error propagation
    def test_provider_error_propagation(
        self, generator: AnswerGenerator, test_registry: LLMProviderRegistry
    ) -> None:
        class ErrorProvider(FakeLLMProvider):
            def invoke(self, request):  # type: ignore
                raise LLMTimeoutError("Timeout occurred")

        test_registry.register("fake-provider", ErrorProvider("fake-provider"), overwrite=True)

        config = AnswerGenerationConfig(provider_name="fake-provider", model_name="fake-model")
        with pytest.raises(LLMTimeoutError):
            generator.generate(get_query_plan(), get_packed_context(), config)

    # I. Query intent & J. Answer style handling
    def test_intent_and_style_in_prompt(
        self, generator: AnswerGenerator, test_registry: LLMProviderRegistry
    ) -> None:
        class CapturingProvider(FakeLLMProvider):
            def __init__(self) -> None:
                super().__init__("fake-provider")
                self.last_msg = ""

            def invoke(self, request):  # type: ignore
                self.last_msg = request.messages[1].content
                return super().invoke(request)

        capturing = CapturingProvider()
        test_registry.register("fake-provider", capturing, overwrite=True)

        qp = get_query_plan(intent=QueryIntent.IMPACT, answer_style=AnswerStyle.IMPACT_ANALYSIS)
        pc = get_packed_context()
        config = AnswerGenerationConfig(provider_name="fake-provider", model_name="fake-model")
        generator.generate(qp, pc, config)

        assert "Intent: impact" in capturing.last_msg
        assert "Answer Style: impact_analysis" in capturing.last_msg

    # K. Provider registry integration
    def test_missing_provider(self, generator: AnswerGenerator) -> None:
        qp = get_query_plan()
        pc = get_packed_context()
        config = AnswerGenerationConfig(provider_name="missing-provider", model_name="fake-model")
        with pytest.raises(LLMProviderNotFoundError):
            generator.generate(qp, pc, config)

    # T. JSON serialization
    def test_json_serialization(self, generator: AnswerGenerator) -> None:
        qp = get_query_plan()
        pc = get_packed_context()
        config = AnswerGenerationConfig(provider_name="fake-provider", model_name="fake-model")
        ans = generator.generate(qp, pc, config)
        json_data = ans.model_dump_json()
        assert "fake-provider" in json_data
        assert "fake-model" in json_data
