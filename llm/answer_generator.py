"""Implementation of TASK-6G Grounded Answer Generation."""

import time

from llm.answer_config import AnswerGenerationConfig
from llm.answer_contracts import AnswerGeneratorContract
from llm.answer_models import GeneratedAnswer
from llm.budget_models import PackedContext
from llm.enums import LLMFinishReason
from llm.exceptions import AnswerGenerationError, LLMProviderError
from llm.planner_models import QueryPlan
from llm.provider_models import LLMMessage, LLMMessageRole, LLMRequest
from llm.provider_registry import LLMProviderRegistry, provider_registry


class AnswerGenerator(AnswerGeneratorContract):
    """Deterministic orchestration of grounded answer generation."""

    def __init__(self, registry: LLMProviderRegistry | None = None) -> None:
        self._registry = registry or provider_registry

    def generate(
        self,
        query_plan: QueryPlan,
        packed_context: PackedContext,
        config: AnswerGenerationConfig,
    ) -> GeneratedAnswer:
        start_time = time.perf_counter()

        if not isinstance(query_plan, QueryPlan):
            raise AnswerGenerationError("Invalid or missing QueryPlan.")
        if not isinstance(packed_context, PackedContext):
            raise AnswerGenerationError("Invalid or missing PackedContext.")
        if not isinstance(config, AnswerGenerationConfig):
            raise AnswerGenerationError("Invalid or missing AnswerGenerationConfig.")

        # Resolve provider
        try:
            provider = self._registry.resolve(config.provider_name)
        except Exception as e:
            if isinstance(e, LLMProviderError):
                raise
            raise AnswerGenerationError(f"Failed to resolve provider: {e}") from e

        # Handle empty context behavior
        if not packed_context.packed_items and not packed_context.formatted_context_str:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return GeneratedAnswer(
                answer_text="Insufficient code context available to answer this query.",
                query=query_plan.query,
                intent=query_plan.primary_intent,
                provider_name=config.provider_name,
                model_name=config.model_name,
                finish_reason=LLMFinishReason.STOP,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                generation_latency_ms=latency_ms,
                context_item_count=0,
                context_token_count=0,
                metadata={"reason": "empty_context"},
            )

        # Build prompt
        system_instruction = self._build_system_instruction(query_plan)
        user_content = self._build_user_message(query_plan, packed_context)

        messages = [
            LLMMessage(role=LLMMessageRole.SYSTEM, content=system_instruction),
            LLMMessage(role=LLMMessageRole.USER, content=user_content),
        ]

        request = LLMRequest(
            messages=messages,
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            timeout=config.timeout,
            packed_context=packed_context,
            metadata={"source": "AnswerGenerator"},
        )

        try:
            response = provider.invoke(request)
        except LLMProviderError:
            raise
        except Exception as e:
            raise AnswerGenerationError(f"Unexpected error during provider invocation: {e}") from e

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return GeneratedAnswer(
            answer_text=response.content,
            query=query_plan.query,
            intent=query_plan.primary_intent,
            provider_name=response.provider_name,
            model_name=response.model_name,
            finish_reason=response.finish_reason,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            total_tokens=response.total_tokens,
            generation_latency_ms=latency_ms,
            context_item_count=len(packed_context.packed_items),
            context_token_count=packed_context.stats.packed_evidence_tokens,
            metadata={"request_latency_ms": response.latency_ms, **response.metadata},
        )

    def _build_system_instruction(self, query_plan: QueryPlan) -> str:
        """Deterministically build the grounding-oriented system prompt."""
        return (
            "You are answering questions about a software repository.\n\n"
            "The supplied code context is the authoritative evidence available for answering the query.\n\n"
            "RULES:\n"
            "1. Answer using the supplied context.\n"
            "2. Do not invent files, symbols, functions, classes, relationships, behavior, or implementation details.\n"
            "3. If the supplied context is insufficient, explicitly say so.\n"
            "4. Distinguish facts supported by the supplied code from uncertainty.\n"
            "5. Do not claim that code exists if it is not present in the supplied context.\n"
            "6. Do not infer unsupported implementation details as facts.\n"
            "7. Keep the answer focused on the user's question.\n"
            "8. Preserve relevant technical names exactly.\n"
            "9. Do not fabricate citations."
        )

    def _build_user_message(self, query_plan: QueryPlan, packed_context: PackedContext) -> str:
        """Deterministically format query plan and packed context into user message."""
        # Build query plan summary strings for deterministic output
        entities_str = (
            ", ".join(sorted(query_plan.target_entities)) if query_plan.target_entities else "None"
        )

        answer_style = getattr(query_plan.answer_style, "value", str(query_plan.answer_style))

        prompt = (
            f"USER QUERY\n"
            f"{query_plan.query}\n\n"
            f"QUERY PLAN SUMMARY\n"
            f"Intent: {query_plan.primary_intent.value}\n"
            f"Target Entities: {entities_str}\n"
            f"Answer Style: {answer_style}\n\n"
            f"CODE CONTEXT\n"
            f"-------------------------\n"
            f"{packed_context.formatted_context_str}\n"
            f"-------------------------\n\n"
            f"ANSWER REQUIREMENTS\n"
            f"Respond directly to the query above using only the code context provided."
        )
        return prompt
