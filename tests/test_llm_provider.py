"""Comprehensive test suite for TASK-6F LLM Provider Abstraction."""

import pytest
from pydantic import SecretStr, ValidationError

from llm.budget_models import (
    ContextPackingStats,
    PackedContext,
    PackedContextItem,
)
from llm.enums import (
    ContextOverflowPolicy,
    LLMFinishReason,
    LLMMessageRole,
    TokenCountMode,
)
from llm.exceptions import (
    InvalidLLMConfigError,
    LLMAuthenticationError,
    LLMProviderNotFoundError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from llm.fake_provider import FakeLLMProvider
from llm.provider_config import LLMProviderConfig
from llm.provider_contracts import LLMProviderContract
from llm.provider_models import (
    LLMMessage,
    LLMProviderCapabilities,
    LLMRequest,
    LLMResponse,
)
from llm.provider_registry import LLMProviderRegistry


class TestLLMProviderAbstraction:
    """Test suite covering all requirements of TASK-6F."""

    def test_contract_existence(self) -> None:
        """Verify LLMProviderContract exists as an abstract base class."""
        assert issubclass(LLMProviderContract, object)
        with pytest.raises(TypeError):
            LLMProviderContract()  # type: ignore[abstract]

    def test_request_model_validation(self) -> None:
        """Verify LLMRequest model validation rules."""
        msg = LLMMessage(role=LLMMessageRole.USER, content="Explain main function.")
        req = LLMRequest(messages=[msg], model="gpt-4o", temperature=0.5, max_tokens=100)
        assert req.model == "gpt-4o"
        assert req.temperature == 0.5
        assert req.max_tokens == 100

        # Invalid model name
        with pytest.raises(ValidationError):
            LLMRequest(messages=[msg], model="   ")

        # Invalid temperature
        with pytest.raises(ValidationError):
            LLMRequest(messages=[msg], model="gpt-4o", temperature=2.5)

        # Invalid max_tokens
        with pytest.raises(ValidationError):
            LLMRequest(messages=[msg], model="gpt-4o", max_tokens=0)

        # Invalid top_p
        with pytest.raises(ValidationError):
            LLMRequest(messages=[msg], model="gpt-4o", top_p=1.5)

        # Invalid timeout
        with pytest.raises(ValidationError):
            LLMRequest(messages=[msg], model="gpt-4o", timeout=-1.0)

        # Missing messages and missing packed_context
        with pytest.raises(ValidationError):
            LLMRequest(messages=[], model="gpt-4o")

    def test_request_model_from_packed_context(self) -> None:
        """Verify LLMRequest construction from Phase 6E PackedContext."""
        stats = ContextPackingStats(
            total_model_context_limit=4096,
            usable_evidence_budget=3000,
            packed_evidence_tokens=150,
            token_count_mode=TokenCountMode.ESTIMATED,
            overflow_policy=ContextOverflowPolicy.SKIP,
        )
        item = PackedContextItem(
            candidate_id="cand-1",
            rank=1,
            final_score=0.95,
            formatted_code="def main(): pass",
            code_tokens=4,
            header_tokens=2,
            token_count=6,
        )
        packed = PackedContext(
            query="What does main do?",
            packed_items=[item],
            stats=stats,
            formatted_context_str="=== Code Evidence ===\ndef main(): pass",
        )

        req = LLMRequest.from_packed_context(
            packed_context=packed,
            model="claude-3-5-sonnet",
            system_instruction="Analyze code accurately.",
            temperature=0.2,
        )

        assert req.model == "claude-3-5-sonnet"
        assert req.temperature == 0.2
        assert req.packed_context is packed
        assert len(req.messages) == 2
        assert req.messages[0].role == LLMMessageRole.SYSTEM
        assert req.messages[0].content == "Analyze code accurately."
        assert req.messages[1].role == LLMMessageRole.USER
        assert "Query: What does main do?" in req.messages[1].content
        assert "def main(): pass" in req.messages[1].content

    def test_response_model_validation(self) -> None:
        """Verify LLMResponse model validation rules."""
        resp = LLMResponse(
            content="Answer text",
            provider_name="fake_provider",
            model_name="fake-model",
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            finish_reason=LLMFinishReason.STOP,
            latency_ms=12.5,
        )
        assert resp.content == "Answer text"
        assert resp.finish_reason == LLMFinishReason.STOP
        assert resp.latency_ms == 12.5

        # Empty provider name
        with pytest.raises(ValidationError):
            LLMResponse(content="x", provider_name="", model_name="m")

        # Empty model name
        with pytest.raises(ValidationError):
            LLMResponse(content="x", provider_name="p", model_name="")

        # Negative token count
        with pytest.raises(ValidationError):
            LLMResponse(content="x", provider_name="p", model_name="m", input_tokens=-1)

        # Negative latency
        with pytest.raises(ValidationError):
            LLMResponse(content="x", provider_name="p", model_name="m", latency_ms=-5.0)

    def test_immutability(self) -> None:
        """Verify frozen immutability across models."""
        msg = LLMMessage(role=LLMMessageRole.USER, content="Hello")
        with pytest.raises(ValidationError):
            msg.content = "New text"

        caps = LLMProviderCapabilities(supports_streaming=True)
        with pytest.raises(ValidationError):
            caps.supports_streaming = False

        req = LLMRequest(messages=[msg], model="fake-model")
        with pytest.raises(ValidationError):
            req.temperature = 0.9

        resp = LLMResponse(content="ans", provider_name="fake", model_name="fake-model")
        with pytest.raises(ValidationError):
            resp.content = "modified"

        cfg = LLMProviderConfig(provider_name="fake", model_name="m")
        with pytest.raises(ValidationError):
            cfg.timeout = 10.0

    def test_provider_config_secret_protection(self) -> None:
        """Verify LLMProviderConfig masks API secrets in string/repr output."""
        cfg = LLMProviderConfig(
            provider_name="openai",
            model_name="gpt-4o",
            api_key=SecretStr("sk-secret-key-12345"),
            timeout=15.0,
        )

        assert "sk-secret-key-12345" not in repr(cfg)
        assert "sk-secret-key-12345" not in str(cfg)
        assert cfg.api_key is not None
        assert cfg.api_key.get_secret_value() == "sk-secret-key-12345"

        # Invalid timeout
        with pytest.raises(ValidationError):
            LLMProviderConfig(provider_name="fake", model_name="m", timeout=0.0)

        # Invalid max_retries
        with pytest.raises(ValidationError):
            LLMProviderConfig(provider_name="fake", model_name="m", max_retries=-1)

    def test_provider_registration_and_resolution(self) -> None:
        """Verify LLMProviderRegistry registration, listing, and resolution."""
        registry = LLMProviderRegistry()
        fake_a = FakeLLMProvider(provider_name="provider_a")
        fake_b = FakeLLMProvider(provider_name="provider_b")

        registry.register("provider_a", fake_a)
        registry.register("provider_b", fake_b)

        assert registry.list_providers() == ["provider_a", "provider_b"]
        assert registry.resolve("provider_a") is fake_a
        assert registry.resolve("PROVIDER_B") is fake_b  # Case insensitive

        assert registry.unregister("provider_a") is True
        assert registry.list_providers() == ["provider_b"]

    def test_unknown_provider_handling(self) -> None:
        """Verify resolving an unregistered provider name raises LLMProviderNotFoundError."""
        registry = LLMProviderRegistry()
        with pytest.raises(LLMProviderNotFoundError) as exc_info:
            registry.resolve("non_existent_provider")
        assert "non_existent_provider" in str(exc_info.value)
        assert exc_info.value.category == "configuration"

    def test_duplicate_provider_registration(self) -> None:
        """Verify registering duplicate provider name fails unless overwrite=True."""
        registry = LLMProviderRegistry()
        p1 = FakeLLMProvider(provider_name="custom")
        p2 = FakeLLMProvider(provider_name="custom", canned_response="v2")

        registry.register("custom", p1)

        with pytest.raises(InvalidLLMConfigError):
            registry.register("custom", p2, overwrite=False)

        # Overwrite succeeds
        registry.register("custom", p2, overwrite=True)
        assert registry.resolve("custom") is p2

    def test_fake_provider_invocation(self) -> None:
        """Verify FakeLLMProvider execution and custom responses."""
        provider = FakeLLMProvider(provider_name="test_fake")
        assert provider.provider_name == "test_fake"
        assert provider.call_count == 0

        msg = LLMMessage(role=LLMMessageRole.USER, content="What does foo do?")
        req = LLMRequest(messages=[msg], model="fake-model", request_id="req-101")

        resp = provider.invoke(req)
        assert resp.provider_name == "test_fake"
        assert resp.model_name == "fake-model"
        assert resp.content == "Fake LLM response generated successfully."
        assert resp.finish_reason == LLMFinishReason.STOP
        assert provider.call_count == 1
        assert provider.call_history[0] is req

        # Custom response map
        provider.set_response_mapping("req-101", "foo executes business logic.")
        resp2 = provider.invoke(req)
        assert resp2.content == "foo executes business logic."

    def test_token_usage_normalization(self) -> None:
        """Verify token counts are normalized on response."""
        provider = FakeLLMProvider(canned_response="One two three four five.")
        msg = LLMMessage(role=LLMMessageRole.USER, content="Hello world from user.")
        req = LLMRequest(messages=[msg], model="fake-model")

        resp = provider.invoke(req)
        assert resp.input_tokens == 4  # "Hello world from user."
        assert resp.output_tokens == 5  # "One two three four five."
        assert resp.total_tokens == 9

    def test_finish_reason_normalization(self) -> None:
        """Verify finish reason enumeration values."""
        resp = LLMResponse(
            content="Done",
            provider_name="fake",
            model_name="m",
            finish_reason=LLMFinishReason.MAX_TOKENS,
        )
        assert resp.finish_reason == LLMFinishReason.MAX_TOKENS
        assert resp.finish_reason == "max_tokens"

    def test_timeout_normalization(self) -> None:
        """Verify invocation timeout raises normalized LLMTimeoutError."""
        provider = FakeLLMProvider(simulated_latency_ms=500.0)  # 0.5s latency
        msg = LLMMessage(role=LLMMessageRole.USER, content="Quick query")
        req = LLMRequest(messages=[msg], model="fake-model", timeout=0.1)  # 0.1s timeout limit

        with pytest.raises(LLMTimeoutError) as exc_info:
            provider.invoke(req)

        assert exc_info.value.category == "timeout"
        assert exc_info.value.provider_name == "fake_provider"

    def test_provider_execution_failure_normalization(self) -> None:
        """Verify forced provider exceptions raise normalized errors."""
        provider = FakeLLMProvider()

        # Auth failure
        provider.set_forced_exception(
            LLMAuthenticationError("Invalid API key", provider_name="fake")
        )
        msg = LLMMessage(role=LLMMessageRole.USER, content="test")
        req = LLMRequest(messages=[msg], model="fake-model")

        with pytest.raises(LLMAuthenticationError) as exc_auth:
            provider.invoke(req)
        assert exc_auth.value.category == "authentication"

        # Rate limit failure
        provider.set_forced_exception(LLMRateLimitError("Quota exceeded", provider_name="fake"))
        with pytest.raises(LLMRateLimitError) as exc_rate:
            provider.invoke(req)
        assert exc_rate.value.category == "rate_limit"

        # Provider unavailable
        provider.set_forced_exception(
            LLMProviderUnavailableError("503 Service Unavailable", provider_name="fake")
        )
        with pytest.raises(LLMProviderUnavailableError) as exc_unavail:
            provider.invoke(req)
        assert exc_unavail.value.category == "unavailable"

    def test_provider_capabilities_reporting(self) -> None:
        """Verify provider capability reporting."""
        caps = LLMProviderCapabilities(
            supports_streaming=True,
            supports_structured_output=True,
            supports_tool_calling=False,
            max_context_window=64000,
            max_output_tokens=2048,
            reports_token_usage=True,
            supported_models=["model-a", "model-b"],
        )
        provider = FakeLLMProvider(capabilities=caps)
        assert provider.capabilities.supports_streaming is True
        assert provider.capabilities.supports_tool_calling is False
        assert provider.capabilities.max_context_window == 64000
        assert provider.capabilities.supported_models == ["model-a", "model-b"]

    def test_secret_non_leakage(self) -> None:
        """Verify secrets do not leak in exception messages or responses."""
        secret_key = "sk-proj-super-secret-key-9999"
        config = LLMProviderConfig(
            provider_name="secret_provider",
            model_name="model-x",
            api_key=SecretStr(secret_key),
        )

        exc = LLMAuthenticationError("Authentication failed", provider_name=config.provider_name)
        assert secret_key not in str(exc)
        assert secret_key not in repr(exc)

    def test_provider_independence(self) -> None:
        """Verify core abstraction imports zero vendor SDKs."""
        import llm.provider_contracts
        import llm.provider_models

        # Inspect module globals/imports
        modules = [llm.provider_contracts, llm.provider_models]
        for mod in modules:
            mod_str = str(dir(mod))
            assert "openai" not in mod_str.lower()
            assert "anthropic" not in mod_str.lower()
            assert "google" not in mod_str.lower()

    def test_deterministic_repeated_invocation(self) -> None:
        """Verify repeated invocations on FakeLLMProvider produce identical responses."""
        provider = FakeLLMProvider(canned_response="Deterministic output text")
        msg = LLMMessage(role=LLMMessageRole.USER, content="Repeat request test")
        req = LLMRequest(messages=[msg], model="fake-model")

        responses = [provider.invoke(req) for _ in range(100)]
        first = responses[0]

        for resp in responses[1:]:
            assert resp.content == first.content
            assert resp.provider_name == first.provider_name
            assert resp.model_name == first.model_name
            assert resp.input_tokens == first.input_tokens
            assert resp.output_tokens == first.output_tokens
            assert resp.total_tokens == first.total_tokens
            assert resp.finish_reason == first.finish_reason

    def test_json_roundtrip_serialization(self) -> None:
        """Verify LLMRequest and LLMResponse Pydantic JSON round-trip serialization."""
        msg = LLMMessage(role=LLMMessageRole.USER, content="Serialized question")
        req = LLMRequest(messages=[msg], model="gpt-4o", temperature=0.1, request_id="r-999")

        req_json = req.model_dump_json()
        req_restored = LLMRequest.model_validate_json(req_json)
        assert req_restored == req

        resp = LLMResponse(
            content="Answer text",
            provider_name="fake",
            model_name="gpt-4o",
            input_tokens=12,
            output_tokens=4,
            total_tokens=16,
            finish_reason=LLMFinishReason.STOP,
            request_id="r-999",
        )
        resp_json = resp.model_dump_json()
        resp_restored = LLMResponse.model_validate_json(resp_json)
        assert resp_restored == resp

    def test_registry_isolation(self) -> None:
        """Verify new LLMProviderRegistry instances are isolated."""
        r1 = LLMProviderRegistry()
        r2 = LLMProviderRegistry()

        p1 = FakeLLMProvider(provider_name="p1")
        r1.register("p1", p1)

        assert r1.list_providers() == ["p1"]
        assert r2.list_providers() == []

        with pytest.raises(LLMProviderNotFoundError):
            r2.resolve("p1")

    def test_packed_context_6e_to_6f_boundary_integration(self) -> None:
        """Integration test verifying 6E PackedContext crosses 6F boundary untampered."""
        stats = ContextPackingStats(
            total_model_context_limit=8192,
            usable_evidence_budget=6000,
            packed_evidence_tokens=250,
            input_candidate_count=5,
            packed_candidate_count=2,
            omitted_candidate_count=3,
        )
        item1 = PackedContextItem(
            candidate_id="cand-101",
            rank=1,
            final_score=0.98,
            file_path="src/main.py",
            symbol_name="process_data",
            formatted_code="def process_data(items):\n    return [x * 2 for x in items]",
            code_tokens=15,
            header_tokens=5,
            token_count=20,
        )
        item2 = PackedContextItem(
            candidate_id="cand-102",
            rank=2,
            final_score=0.91,
            file_path="src/utils.py",
            symbol_name="transform",
            formatted_code="def transform(x):\n    return x * 2",
            code_tokens=8,
            header_tokens=4,
            token_count=12,
        )
        packed_context = PackedContext(
            query="How does data processing work?",
            packed_items=[item1, item2],
            stats=stats,
            formatted_context_str=(
                "=== File: src/main.py | Symbol: process_data ===\n"
                "def process_data(items):\n    return [x * 2 for x in items]\n\n"
                "=== File: src/utils.py | Symbol: transform ===\n"
                "def transform(x):\n    return x * 2"
            ),
            packing_latency_ms=1.5,
        )

        # Construct request boundary object
        req = LLMRequest.from_packed_context(
            packed_context=packed_context,
            model="gpt-4o",
            system_instruction="You are a code understanding assistant.",
        )

        # Verify PackedContext was NOT modified, pruned, or reordered
        assert req.packed_context is not None
        assert req.packed_context.query == "How does data processing work?"
        assert len(req.packed_context.packed_items) == 2
        assert req.packed_context.packed_items[0].candidate_id == "cand-101"
        assert req.packed_context.packed_items[1].candidate_id == "cand-102"
        assert req.packed_context.stats.packed_candidate_count == 2

        # Invoke fake provider
        provider = FakeLLMProvider(canned_response="Data processing doubles items in a list.")
        resp = provider.invoke(req)

        assert resp.content == "Data processing doubles items in a list."
        assert resp.model_name == "gpt-4o"
        assert resp.input_tokens == 250  # Uses packed evidence token count from PackedContext
        assert resp.output_tokens == 7

    def test_negative_boundary_invariants(self) -> None:
        """Negative boundary verification that 6F does not expose retrieval, ranking, or answer generation methods."""
        import llm.fake_provider as p_fake
        import llm.provider_contracts as p_contracts
        import llm.provider_models as p_models

        # Ensure no retrieval / graph / pruning / citation methods exist on 6F classes
        for obj in [
            p_models.LLMRequest,
            p_models.LLMResponse,
            p_contracts.LLMProviderContract,
            p_fake.FakeLLMProvider,
        ]:
            dir_list = dir(obj)
            for forbidden in [
                "retrieve",
                "bm25",
                "vector_search",
                "graph_expand",
                "rank_candidates",
                "deduplicate",
                "prune",
                "format_citations",
                "compute_grounding_score",
            ]:
                assert forbidden not in dir_list, (
                    f"Forbidden method '{forbidden}' found on 6F class {obj.__name__}"
                )
