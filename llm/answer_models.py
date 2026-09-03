"""Data models for TASK-6G Grounded Answer Generation."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from llm.enums import LLMFinishReason, QueryIntent


class GeneratedAnswer(BaseModel):
    """Immutable structured result representing a generated answer."""

    model_config = ConfigDict(frozen=True)

    answer_text: str = Field(
        description="Generated text answer focused on query and supplied context."
    )
    query: str = Field(description="Original resolved query.")
    intent: QueryIntent = Field(description="Primary intent used for generation.")
    provider_name: str = Field(description="Name of the LLM provider used.")
    model_name: str = Field(description="Model identifier used for generation.")
    finish_reason: LLMFinishReason = Field(description="Normalized completion finish reason.")
    input_tokens: int | None = Field(
        default=None, description="Input/prompt token count if reported."
    )
    output_tokens: int | None = Field(default=None, description="Output token count if reported.")
    total_tokens: int | None = Field(default=None, description="Total tokens consumed if reported.")
    generation_latency_ms: float = Field(
        default=0.0, description="End-to-end local latency for generation orchestration."
    )
    context_item_count: int = Field(
        default=0, description="Number of context items supplied in prompt."
    )
    context_token_count: int = Field(
        default=0, description="Number of context tokens packed in prompt."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible generation metadata."
    )
