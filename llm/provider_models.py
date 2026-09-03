"""Data models for TASK-6F LLM Provider Abstraction."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm.budget_models import PackedContext
from llm.enums import LLMFinishReason, LLMMessageRole


class LLMMessage(BaseModel):
    """Immutable single message object in an LLM request payload."""

    model_config = ConfigDict(frozen=True)

    role: LLMMessageRole = Field(description="Role of message sender (SYSTEM, USER, ASSISTANT).")
    content: str = Field(description="Non-empty text content of message.")

    @model_validator(mode="after")
    def validate_content(self) -> "LLMMessage":
        """Ensure content is not empty or whitespace-only."""
        if not self.content or not self.content.strip():
            raise ValueError("LLMMessage content cannot be empty or whitespace-only.")
        return self


class LLMProviderCapabilities(BaseModel):
    """Immutable provider capabilities declaration model."""

    model_config = ConfigDict(frozen=True)

    supports_streaming: bool = Field(
        default=False, description="Flag indicating if provider supports streaming responses."
    )
    supports_structured_output: bool = Field(
        default=False, description="Flag indicating if provider supports JSON/structured output."
    )
    supports_tool_calling: bool = Field(
        default=False, description="Flag indicating if provider supports native tool calling."
    )
    max_context_window: int | None = Field(
        default=None, description="Maximum total context window token capacity if known."
    )
    max_output_tokens: int | None = Field(
        default=None, description="Maximum completion output token capacity if known."
    )
    reports_token_usage: bool = Field(
        default=True, description="Flag indicating if provider returns exact token usage counts."
    )
    supported_models: list[str] = Field(
        default_factory=list, description="List of supported model identifiers."
    )


class LLMRequest(BaseModel):
    """Immutable provider-independent request payload for LLM invocation."""

    model_config = ConfigDict(frozen=True)

    messages: list[LLMMessage] = Field(
        default_factory=list, description="Ordered list of request conversation messages."
    )
    model: str = Field(
        description="Target model identifier (e.g., gpt-4o, claude-3-5-sonnet, fake-model)."
    )
    temperature: float = Field(
        default=0.0, description="Sampling temperature parameter between 0.0 and 2.0."
    )
    max_tokens: int | None = Field(
        default=None, description="Maximum generation completion tokens if restricted."
    )
    top_p: float | None = Field(
        default=None, description="Nucleus sampling probability threshold between 0.0 and 1.0."
    )
    stop_sequences: list[str] = Field(
        default_factory=list, description="Optional stop sequences for completion termination."
    )
    timeout: float | None = Field(
        default=None, description="Per-request execution timeout limit in seconds."
    )
    packed_context: PackedContext | None = Field(
        default=None, description="Optional Phase 6E PackedContext container crossing boundary."
    )
    request_id: str | None = Field(
        default=None, description="Optional correlation tracking request identifier."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible request-level metadata."
    )

    @model_validator(mode="after")
    def validate_request(self) -> "LLMRequest":
        """Validate LLM request configuration invariants."""
        if not self.model or not self.model.strip():
            raise ValueError("Target model identifier cannot be empty or whitespace-only.")
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {self.temperature}.")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive if specified, got {self.max_tokens}.")
        if self.top_p is not None and not (0.0 <= self.top_p <= 1.0):
            raise ValueError(f"top_p must be between 0.0 and 1.0 if specified, got {self.top_p}.")
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError(f"timeout must be positive if specified, got {self.timeout}.")
        if not self.messages and self.packed_context is None:
            raise ValueError("LLMRequest must contain at least one message or a PackedContext.")
        return self

    @classmethod
    def from_packed_context(
        cls,
        packed_context: PackedContext,
        model: str,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop_sequences: list[str] | None = None,
        timeout: float | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "LLMRequest":
        """Construct a provider-independent LLMRequest from a Phase 6E PackedContext."""
        messages: list[LLMMessage] = []
        sys_content = (
            system_instruction.strip()
            if system_instruction and system_instruction.strip()
            else (
                "You are an AI code understanding engine assistant. "
                "Answer questions strictly based on the provided context."
            )
        )
        messages.append(LLMMessage(role=LLMMessageRole.SYSTEM, content=sys_content))

        user_content = (
            f"Query: {packed_context.query}\n\nContext:\n{packed_context.formatted_context_str}"
        )
        messages.append(LLMMessage(role=LLMMessageRole.USER, content=user_content))

        return cls(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop_sequences=stop_sequences or [],
            timeout=timeout,
            packed_context=packed_context,
            request_id=request_id,
            metadata=metadata or {},
        )


class LLMResponse(BaseModel):
    """Immutable provider-independent normalized response model for LLM completion."""

    model_config = ConfigDict(frozen=True)

    content: str = Field(description="Generated raw text response content.")
    provider_name: str = Field(description="Name of provider handling the request.")
    model_name: str = Field(description="Model identifier that produced response.")
    input_tokens: int | None = Field(
        default=None, description="Input/prompt token count if reported."
    )
    output_tokens: int | None = Field(
        default=None, description="Output/completion token count if reported."
    )
    total_tokens: int | None = Field(default=None, description="Total tokens consumed if reported.")
    finish_reason: LLMFinishReason = Field(
        default=LLMFinishReason.STOP, description="Normalized completion finish reason."
    )
    latency_ms: float = Field(
        default=0.0, description="Provider execution latency in milliseconds."
    )
    request_id: str | None = Field(
        default=None, description="Associated request identifier if present."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible safe metadata (guaranteed free of secrets).",
    )

    @model_validator(mode="after")
    def validate_response(self) -> "LLMResponse":
        """Validate LLM response data invariants."""
        if not self.provider_name or not self.provider_name.strip():
            raise ValueError("Provider name cannot be empty.")
        if not self.model_name or not self.model_name.strip():
            raise ValueError("Model name cannot be empty.")
        if self.input_tokens is not None and self.input_tokens < 0:
            raise ValueError(f"input_tokens cannot be negative, got {self.input_tokens}.")
        if self.output_tokens is not None and self.output_tokens < 0:
            raise ValueError(f"output_tokens cannot be negative, got {self.output_tokens}.")
        if self.total_tokens is not None and self.total_tokens < 0:
            raise ValueError(f"total_tokens cannot be negative, got {self.total_tokens}.")
        if self.latency_ms < 0.0:
            raise ValueError(f"latency_ms cannot be negative, got {self.latency_ms}.")
        return self
