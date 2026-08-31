"""Comprehensive test suite for TASK-4C — Embedding Pipeline."""

import pytest
from pydantic import ValidationError

from code_analyzer.ir import SourceLocation
from code_analyzer.parsers.models import Language
from retrieval.embedding_models import (
    EmbeddingBatchResult,
    EmbeddingInput,
    EmbeddingResult,
)
from retrieval.embedding_pipeline import EmbeddingPipeline
from retrieval.enums import ChunkType
from retrieval.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingDimensionError,
    EmbeddingInputError,
    EmbeddingProviderError,
)
from retrieval.models import CodeChunk
from retrieval.providers import DeterministicTestEmbeddingProvider
from retrieval.text_builder import EmbeddingTextBuilder


@pytest.fixture
def sample_location() -> SourceLocation:
    """Fixture providing a standard SourceLocation."""
    return SourceLocation(
        file_path="src/services/payment_service.py",
        start_line=10,
        start_column=4,
        end_line=25,
        end_column=20,
    )


@pytest.fixture
def sample_python_chunk(sample_location: SourceLocation) -> CodeChunk:
    """Fixture providing a Python CodeChunk."""
    return CodeChunk(
        id="chunk_py_001",
        chunk_type=ChunkType.METHOD,
        repository_id="repo_alpha",
        commit_id="commit_uuid_101",
        commit_sha="a1b2c3d4e5f67890123456789abcdef012345678",
        file_id="file_meta_001",
        file_path="src/services/payment_service.py",
        language=Language.PYTHON,
        entity_id="method_process_001",
        parent_entity_id="class_payment_001",
        name="process_payment",
        qualified_name="services.payment_service.PaymentService.process_payment",
        doc_comment="Process a payment transaction.",
        signature="def process_payment(self, amount: float) -> bool",
        content="def process_payment(self, amount: float) -> bool:\n    return True",
        source_location=sample_location,
    )


@pytest.fixture
def sample_java_chunk() -> CodeChunk:
    """Fixture providing a Java CodeChunk."""
    loc = SourceLocation(
        file_path="src/Payment.java", start_line=1, start_column=0, end_line=15, end_column=0
    )
    return CodeChunk(
        id="chunk_java_001",
        chunk_type=ChunkType.CLASS_CONTEXT,
        repository_id="repo_alpha",
        commit_id="commit_uuid_101",
        commit_sha="a1b2c3d4e5f67890123456789abcdef012345678",
        file_id="file_java_001",
        file_path="src/Payment.java",
        language=Language.JAVA,
        entity_id="class_payment_java",
        name="Payment",
        qualified_name="com.example.Payment",
        doc_comment="Java payment class",
        signature="public class Payment",
        content="public class Payment {\n    private double amount;\n}",
        source_location=loc,
    )


@pytest.fixture
def sample_ts_chunk() -> CodeChunk:
    """Fixture providing a TypeScript CodeChunk."""
    loc = SourceLocation(
        file_path="src/payment.ts", start_line=1, start_column=0, end_line=10, end_column=0
    )
    return CodeChunk(
        id="chunk_ts_001",
        chunk_type=ChunkType.FUNCTION,
        repository_id="repo_alpha",
        commit_id="commit_uuid_101",
        commit_sha="a1b2c3d4e5f67890123456789abcdef012345678",
        file_id="file_ts_001",
        file_path="src/payment.ts",
        language=Language.TYPESCRIPT,
        entity_id="func_pay_ts",
        name="pay",
        qualified_name="payment.pay",
        signature="export function pay(amount: number): boolean",
        content="export function pay(amount: number): boolean {\n    return true;\n}",
        source_location=loc,
    )


# ------------------------------------------------------------------------------
# 1. Embedding Text Builder Tests
# ------------------------------------------------------------------------------


def test_text_builder_formatting(sample_python_chunk: CodeChunk) -> None:
    """Verify EmbeddingTextBuilder formats source code, symbol, signature, and doc comment."""
    builder = EmbeddingTextBuilder()
    text = builder.build_text(sample_python_chunk)

    assert "[Language: python]" in text
    assert "[Path: src/services/payment_service.py]" in text
    assert "[ChunkType: method]" in text
    assert "[Symbol: services.payment_service.PaymentService.process_payment]" in text
    assert "[Signature: def process_payment(self, amount: float) -> bool]" in text
    assert "[Parent: class_payment_001]" in text
    assert "[Doc: Process a payment transaction.]" in text
    assert "def process_payment(self, amount: float) -> bool:" in text


def test_text_builder_empty_content_fallback(sample_location: SourceLocation) -> None:
    """Verify chunks with empty source content get contextual header plus fallback content."""
    empty_chunk = CodeChunk(
        id="chunk_empty_001",
        chunk_type=ChunkType.FILE_CONTEXT,
        repository_id="repo_a",
        file_id="file_01",
        file_path="empty.py",
        language=Language.PYTHON,
        content="",
        source_location=sample_location,
    )
    builder = EmbeddingTextBuilder()
    text = builder.build_text(empty_chunk)

    assert "[Language: python]" in text
    assert "[Path: empty.py]" in text
    assert "[Content: (Empty implementation)]" in text
    assert text.strip() != ""


def test_text_builder_determinism(sample_python_chunk: CodeChunk) -> None:
    """Verify repeated build_text calls produce 100% identical outputs."""
    builder = EmbeddingTextBuilder()
    text1 = builder.build_text(sample_python_chunk)
    text2 = builder.build_text(sample_python_chunk)
    assert text1 == text2


# ------------------------------------------------------------------------------
# 2. Deterministic Test Embedding Provider Tests
# ------------------------------------------------------------------------------


def test_deterministic_provider_vector_generation() -> None:
    """Verify DeterministicTestEmbeddingProvider outputs reproducible vectors of correct dimension."""
    provider = DeterministicTestEmbeddingProvider(dimension=128)
    inp1 = EmbeddingInput(
        chunk_id="c1",
        text="def foo(): pass",
        model_name="test-model",
        embedding_version="v1.0",
        metadata={"repository_id": "repo_x"},
    )
    inp2 = EmbeddingInput(
        chunk_id="c2",
        text="def foo(): pass",
        model_name="test-model",
        embedding_version="v1.0",
        metadata={"repository_id": "repo_x"},
    )

    results1 = provider.embed([inp1])
    results2 = provider.embed([inp2])

    assert len(results1) == 1
    res1 = results1[0]
    res2 = results2[0]

    assert res1.dimension == 128
    assert len(res1.vector) == 128
    assert res1.vector == res2.vector  # Same text -> exact same vector


def test_deterministic_provider_distinct_vectors() -> None:
    """Verify different input texts produce distinct vectors."""
    provider = DeterministicTestEmbeddingProvider(dimension=64)
    inp1 = EmbeddingInput(
        chunk_id="c1", text="class Alpha: pass", model_name="m", embedding_version="v1"
    )
    inp2 = EmbeddingInput(
        chunk_id="c2", text="class Beta: pass", model_name="m", embedding_version="v1"
    )

    res = provider.embed([inp1, inp2])
    assert res[0].vector != res[1].vector


def test_deterministic_provider_invalid_dimension() -> None:
    """Verify provider raises EmbeddingConfigurationError for dimension <= 0."""
    with pytest.raises(EmbeddingConfigurationError):
        DeterministicTestEmbeddingProvider(dimension=0)


# ------------------------------------------------------------------------------
# 3. Pipeline Orchestration & Batching Tests
# ------------------------------------------------------------------------------


def test_pipeline_single_chunk(sample_python_chunk: CodeChunk) -> None:
    """Verify embed_chunk embeds a single chunk and preserves metadata."""
    pipeline = EmbeddingPipeline()
    result = pipeline.embed_chunk(sample_python_chunk)

    assert isinstance(result, EmbeddingResult)
    assert result.chunk_id == "chunk_py_001"
    assert result.repository_id == "repo_alpha"
    assert result.commit_id == "commit_uuid_101"
    assert result.commit_sha == "a1b2c3d4e5f67890123456789abcdef012345678"
    assert result.provider_name == "test"
    assert result.model_name == "test-embed-v1"
    assert result.embedding_version == "v1.0"
    assert len(result.vector) == 384


def test_pipeline_batching_boundaries(sample_location: SourceLocation) -> None:
    """Verify pipeline correctly batches inputs across configured batch_size boundaries."""
    chunks = [
        CodeChunk(
            id=f"chunk_batch_{i}",
            chunk_type=ChunkType.FUNCTION,
            repository_id="repo_batch",
            file_id=f"file_{i}",
            file_path=f"src/file_{i}.py",
            language=Language.PYTHON,
            content=f"def func_{i}(): return {i}",
            source_location=sample_location,
        )
        for i in range(7)
    ]

    pipeline = EmbeddingPipeline(batch_size=3)
    batch_res = pipeline.embed_chunks(chunks)

    assert isinstance(batch_res, EmbeddingBatchResult)
    assert batch_res.total_chunks == 7
    assert batch_res.succeeded_count == 7
    assert batch_res.failed_count == 0
    assert len(batch_res.results) == 7
    # Verify ordering preserved
    for i in range(7):
        assert batch_res.results[i].chunk_id == f"chunk_batch_{i}"


def test_pipeline_empty_collection() -> None:
    """Verify embedding an empty collection returns an empty EmbeddingBatchResult without error."""
    pipeline = EmbeddingPipeline()
    res = pipeline.embed_chunks([])

    assert res.total_chunks == 0
    assert len(res.results) == 0
    assert len(res.failures) == 0


def test_pipeline_duplicate_chunk_ids(sample_python_chunk: CodeChunk) -> None:
    """Verify pipeline raises EmbeddingInputError if duplicate chunk IDs are present."""
    pipeline = EmbeddingPipeline()
    with pytest.raises(EmbeddingInputError):
        pipeline.embed_chunks([sample_python_chunk, sample_python_chunk])


def test_pipeline_invalid_batch_size() -> None:
    """Verify pipeline raises EmbeddingConfigurationError for invalid batch_size."""
    with pytest.raises(EmbeddingConfigurationError):
        EmbeddingPipeline(batch_size=0)


def test_pipeline_result_immutability(sample_python_chunk: CodeChunk) -> None:
    """Verify EmbeddingResult is immutable (frozen model)."""
    pipeline = EmbeddingPipeline()
    res = pipeline.embed_chunk(sample_python_chunk)

    with pytest.raises(ValidationError):
        res.vector = [0.0] * 384


# ------------------------------------------------------------------------------
# 4. Mock & Error Injection Tests
# ------------------------------------------------------------------------------


class FaultyEmbeddingProvider(DeterministicTestEmbeddingProvider):
    """Test provider mock that simulates transient network errors or dimension mismatches."""

    def __init__(self, fail_count: int = 1, wrong_dim: bool = False) -> None:
        super().__init__()
        self.fail_count = fail_count
        self.calls = 0
        self.wrong_dim = wrong_dim

    def embed(self, inputs: list[EmbeddingInput]) -> list[EmbeddingResult]:
        self.calls += 1
        if self.calls <= self.fail_count:
            raise EmbeddingProviderError(
                f"Simulated network error attempt {self.calls}", retryable=True
            )

        results = super().embed(inputs)
        if self.wrong_dim:
            # Return incorrect vector dimension
            bad_results: list[EmbeddingResult] = []
            for r in results:
                bad_results.append(
                    EmbeddingResult(
                        chunk_id=r.chunk_id,
                        vector=[0.1, 0.2],  # Length 2 instead of 384
                        dimension=2,  # Declared 2 instead of 384
                        provider_name=r.provider_name,
                        model_name=r.model_name,
                        embedding_version=r.embedding_version,
                        repository_id=r.repository_id,
                    )
                )
            return bad_results
        return results


def test_pipeline_retry_success(sample_python_chunk: CodeChunk) -> None:
    """Verify pipeline retries transient provider errors up to max_retries and succeeds."""
    provider = FaultyEmbeddingProvider(fail_count=2)
    pipeline = EmbeddingPipeline(provider=provider, max_retries=3)

    res = pipeline.embed_chunk(sample_python_chunk)
    assert res.chunk_id == sample_python_chunk.id
    assert provider.calls == 3


def test_pipeline_dimension_mismatch_rejection(sample_python_chunk: CodeChunk) -> None:
    """Verify pipeline rejects vectors with dimension mismatch against provider declaration."""
    provider = FaultyEmbeddingProvider(fail_count=0, wrong_dim=True)
    pipeline = EmbeddingPipeline(provider=provider)

    with pytest.raises(EmbeddingDimensionError):
        pipeline.embed_chunk(sample_python_chunk)


# ------------------------------------------------------------------------------
# 5. Cross-Language Integration Tests
# ------------------------------------------------------------------------------


def test_cross_language_parity(
    sample_python_chunk: CodeChunk,
    sample_java_chunk: CodeChunk,
    sample_ts_chunk: CodeChunk,
) -> None:
    """Verify Java, Python, and TypeScript chunks all flow seamlessly through the same embedding pipeline."""
    pipeline = EmbeddingPipeline(batch_size=10)
    batch_res = pipeline.embed_chunks([sample_python_chunk, sample_java_chunk, sample_ts_chunk])

    assert batch_res.total_chunks == 3
    assert batch_res.succeeded_count == 3
    assert len(batch_res.results) == 3

    res_py = batch_res.results[0]
    res_java = batch_res.results[1]
    res_ts = batch_res.results[2]

    assert res_py.chunk_id == "chunk_py_001"
    assert res_java.chunk_id == "chunk_java_001"
    assert res_ts.chunk_id == "chunk_ts_001"

    # All vectors must be valid 384-dim non-empty floats
    for res in (res_py, res_java, res_ts):
        assert len(res.vector) == 384
        assert res.repository_id == "repo_alpha"
        assert res.commit_id == "commit_uuid_101"


# ------------------------------------------------------------------------------
# 6. Performance Sanity / Batch Call Ratio Test
# ------------------------------------------------------------------------------


class CallCountingProvider(DeterministicTestEmbeddingProvider):
    """Test provider that records number of embed calls."""

    def __init__(self, dimension: int = 384) -> None:
        super().__init__(dimension=dimension)
        self.call_count = 0

    def embed(self, inputs: list[EmbeddingInput]) -> list[EmbeddingResult]:
        self.call_count += 1
        return super().embed(inputs)


def test_performance_batch_ratio(sample_location: SourceLocation) -> None:
    """Verify N chunks are processed through exactly ceil(N / batch_size) provider calls."""
    chunks = [
        CodeChunk(
            id=f"chunk_perf_{i}",
            chunk_type=ChunkType.FUNCTION,
            repository_id="repo_perf",
            file_id="file_perf",
            file_path="src/perf.py",
            language=Language.PYTHON,
            content=f"def func_{i}(): return {i}",
            source_location=sample_location,
        )
        for i in range(25)
    ]

    provider = CallCountingProvider()
    pipeline = EmbeddingPipeline(provider=provider, batch_size=10)
    batch_res = pipeline.embed_chunks(chunks)

    assert batch_res.succeeded_count == 25
    # 25 chunks with batch_size=10 -> 3 batches (10, 10, 5)
    assert provider.call_count == 3


# ------------------------------------------------------------------------------
# 7. 4A / 4B Regression Protection Test
# ------------------------------------------------------------------------------


def test_ir_and_chunk_immutability(sample_python_chunk: CodeChunk) -> None:
    """Verify running chunks through embedding pipeline does NOT mutate original CodeChunk or IR objects."""
    chunk_before_dict = sample_python_chunk.model_dump()

    pipeline = EmbeddingPipeline()
    _ = pipeline.embed_chunk(sample_python_chunk)

    chunk_after_dict = sample_python_chunk.model_dump()
    assert chunk_before_dict == chunk_after_dict
