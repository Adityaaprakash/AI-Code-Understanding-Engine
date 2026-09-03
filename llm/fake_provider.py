"""Deterministic Fake LLM Provider implementation for TASK-6F unit & integration testing."""

from llm.enums import LLMFinishReason
from llm.exceptions import LLMTimeoutError
from llm.provider_contracts import LLMProviderContract
from llm.provider_models import (
    LLMProviderCapabilities,
    LLMRequest,
    LLMResponse,
)


class FakeLLMProvider(LLMProviderContract):
    """Deterministic fake LLM provider implementation for offline testing without network calls."""

    def __init__(
        self,
        provider_name: str = "fake_provider",
        canned_response: str = "Fake LLM response generated successfully.",
        capabilities: LLMProviderCapabilities | None = None,
        simulated_latency_ms: float = 1.0,
    ) -> None:
        self._provider_name = provider_name.strip().lower()
        self._canned_response = canned_response
        self._capabilities = capabilities or LLMProviderCapabilities(
            supports_streaming=True,
            supports_structured_output=True,
            supports_tool_calling=True,
            max_context_window=128000,
            max_output_tokens=4096,
            reports_token_usage=True,
            supported_models=["fake-model", "fake-model-v2", "gpt-4o", "claude-3-5-sonnet"],
        )
        self._simulated_latency_ms = max(0.0, simulated_latency_ms)
        self._response_map: dict[str, str] = {}
        self._forced_exception: Exception | None = None
        self._call_history: list[LLMRequest] = []

    @property
    def provider_name(self) -> str:
        """Return the unique provider name."""
        return self._provider_name

    @property
    def capabilities(self) -> LLMProviderCapabilities:
        """Return provider capabilities."""
        return self._capabilities

    @property
    def call_history(self) -> list[LLMRequest]:
        """Return recorded call history list."""
        return list(self._call_history)

    @property
    def call_count(self) -> int:
        """Return total number of invocations recorded."""
        return len(self._call_history)

    def set_canned_response(self, text: str) -> None:
        """Set default canned response text."""
        self._canned_response = text

    def set_response_mapping(self, key: str, response_text: str) -> None:
        """Map a specific keyword or request_id to a custom canned response text."""
        self._response_map[key.strip()] = response_text

    def set_forced_exception(self, exc: Exception | None) -> None:
        """Set a forced exception to raise on next invocation (e.g. LLMTimeoutError)."""
        self._forced_exception = exc

    def set_simulated_latency(self, latency_ms: float) -> None:
        """Set simulated latency in milliseconds."""
        self._simulated_latency_ms = max(0.0, latency_ms)

    def clear_history(self) -> None:
        """Clear recorded call history."""
        self._call_history.clear()

    def invoke(self, request: LLMRequest) -> LLMResponse:
        """Execute deterministic fake LLM invocation."""
        self._call_history.append(request)

        # Check timeout constraint against simulated latency
        if request.timeout is not None:
            timeout_ms = request.timeout * 1000.0
            if self._simulated_latency_ms > timeout_ms:
                raise LLMTimeoutError(
                    f"Invocation timeout of {request.timeout}s ({timeout_ms:.1f}ms) exceeded "
                    f"by simulated latency {self._simulated_latency_ms:.1f}ms.",
                    provider_name=self._provider_name,
                    details={
                        "timeout_seconds": request.timeout,
                        "simulated_latency_ms": self._simulated_latency_ms,
                    },
                )

        # If forced exception is configured, raise it
        if self._forced_exception is not None:
            raise self._forced_exception

        # Determine response text content
        content = self._canned_response
        if request.request_id and request.request_id in self._response_map:
            content = self._response_map[request.request_id]
        else:
            for msg in request.messages:
                for key, val in self._response_map.items():
                    if key in msg.content:
                        content = val
                        break

        # Calculate deterministic token usage
        if request.packed_context:
            in_tokens = request.packed_context.stats.packed_evidence_tokens
        else:
            in_tokens = sum(len(m.content.split()) for m in request.messages)

        out_tokens = len(content.split())
        total_tokens = in_tokens + out_tokens

        return LLMResponse(
            content=content,
            provider_name=self._provider_name,
            model_name=request.model,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            total_tokens=total_tokens,
            finish_reason=LLMFinishReason.STOP,
            latency_ms=self._simulated_latency_ms,
            request_id=request.request_id,
            metadata={"fake_provider": True, "call_index": len(self._call_history)},
        )
