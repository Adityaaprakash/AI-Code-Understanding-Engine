"""Unit and integration tests for Phase 5 Vector Retrieval Service (VectorRetriever)."""

import time

import pytest

from code_analyzer.ir import SourceLocation
from code_analyzer.parsers.models import Language
from retrieval.contracts import VectorIndexContract, VectorRetrieverContract
from retrieval.embedding_pipeline import EmbeddingPipeline
from retrieval.enums import ChunkType
from retrieval.exceptions import EmbeddingDimensionError, VectorQueryError
from retrieval.identity import generate_chunk_id
from retrieval.models import CodeChunk, CodeChunkCollection
from retrieval.providers import DeterministicTestEmbeddingProvider
from retrieval.query_models import QueryKind
from retrieval.retrieval_models import RetrievalResultSet
from retrieval.vector_index import VectorIndex
from retrieval.vector_retriever import VectorRetriever


@pytest.fixture
def multi_language_corpus() -> CodeChunkCollection:
    """Fixture returning a multi-language (Java, Python, TypeScript) test corpus."""
    chunks: list[CodeChunk] = []

    loc_java_1 = SourceLocation(start_line=1, start_column=0, end_line=40, end_column=1)
    loc_java_2 = SourceLocation(start_line=15, start_column=4, end_line=25, end_column=5)
    loc_py_1 = SourceLocation(start_line=1, start_column=0, end_line=15, end_column=0)
    loc_py_2 = SourceLocation(start_line=1, start_column=0, end_line=30, end_column=0)
    loc_ts_1 = SourceLocation(start_line=1, start_column=0, end_line=50, end_column=1)

    # 1. Java PaymentService class and method
    chunks.append(
        CodeChunk(
            id=generate_chunk_id(
                "repo-test",
                "src/payment/PaymentService.java",
                ChunkType.CLASS_CONTEXT,
                "ent-java-1",
                loc_java_1,
            ),
            chunk_type=ChunkType.CLASS_CONTEXT,
            repository_id="repo-test",
            commit_sha="sha-v1",
            file_path="src/payment/PaymentService.java",
            language=Language.JAVA,
            entity_id="ent-java-1",
            name="PaymentService",
            qualified_name="com.example.payment.PaymentService",
            signature="public class PaymentService",
            doc_comment="Primary Java PaymentService handling financial transactions.",
            source_location=loc_java_1,
            content="package com.example.payment;\npublic class PaymentService {\n    public void processPayment() {}\n}",
        )
    )
    chunks.append(
        CodeChunk(
            id=generate_chunk_id(
                "repo-test",
                "src/payment/PaymentService.java",
                ChunkType.METHOD,
                "ent-java-2",
                loc_java_2,
            ),
            chunk_type=ChunkType.METHOD,
            repository_id="repo-test",
            commit_sha="sha-v1",
            file_path="src/payment/PaymentService.java",
            language=Language.JAVA,
            entity_id="ent-java-2",
            parent_entity_id="ent-java-1",
            name="processPayment",
            qualified_name="com.example.payment.PaymentService.processPayment",
            signature="public void processPayment(PaymentRequest req)",
            doc_comment="Processes credit card and bank transfer payments.",
            source_location=loc_java_2,
            content="public void processPayment(PaymentRequest req) {\n    validateTransaction(req);\n}",
        )
    )

    # 2. Python AuthService function & JWT filter
    chunks.append(
        CodeChunk(
            id=generate_chunk_id(
                "repo-test", "src/auth/service.py", ChunkType.FUNCTION, "ent-py-1", loc_py_1
            ),
            chunk_type=ChunkType.FUNCTION,
            repository_id="repo-test",
            commit_sha="sha-v1",
            file_path="src/auth/service.py",
            language=Language.PYTHON,
            entity_id="ent-py-1",
            name="get_user_by_id",
            qualified_name="auth.service.get_user_by_id",
            signature="def get_user_by_id(user_id: str) -> User:",
            doc_comment="Retrieve active user by unique identifier.",
            source_location=loc_py_1,
            content="def get_user_by_id(user_id: str) -> User:\n    return db.query(User).get(user_id)",
        )
    )
    chunks.append(
        CodeChunk(
            id=generate_chunk_id(
                "repo-test", "src/auth/jwt_filter.py", ChunkType.CLASS_CONTEXT, "ent-py-2", loc_py_2
            ),
            chunk_type=ChunkType.CLASS_CONTEXT,
            repository_id="repo-test",
            commit_sha="sha-v1",
            file_path="src/auth/jwt_filter.py",
            language=Language.PYTHON,
            entity_id="ent-py-2",
            name="JWTAuthenticationFilter",
            qualified_name="auth.jwt_filter.JWTAuthenticationFilter",
            signature="class JWTAuthenticationFilter(BaseFilter):",
            doc_comment="Authenticates HTTP requests using JWT tokens.",
            source_location=loc_py_2,
            content="class JWTAuthenticationFilter(BaseFilter):\n    def authenticate(self, request):\n        pass",
        )
    )

    # 3. TypeScript PaymentController
    chunks.append(
        CodeChunk(
            id=generate_chunk_id(
                "repo-test",
                "src/controllers/PaymentController.ts",
                ChunkType.CLASS_CONTEXT,
                "ent-ts-1",
                loc_ts_1,
            ),
            chunk_type=ChunkType.CLASS_CONTEXT,
            repository_id="repo-test",
            commit_sha="sha-v1",
            file_path="src/controllers/PaymentController.ts",
            language=Language.TYPESCRIPT,
            entity_id="ent-ts-1",
            name="PaymentController",
            qualified_name="PaymentController",
            signature="export class PaymentController",
            doc_comment="REST API controller for payment processing.",
            source_location=loc_ts_1,
            content="export class PaymentController {\n    async handlePayment(req: Request, res: Response) {}\n}",
        )
    )

    return CodeChunkCollection(repository_id="repo-test", commit_sha="sha-v1", chunks=chunks)


@pytest.fixture
def populated_vector_index(multi_language_corpus: CodeChunkCollection) -> VectorIndexContract:
    """Fixture returning a VectorIndex populated with embeddings for multi_language_corpus."""
    provider = DeterministicTestEmbeddingProvider()
    pipeline = EmbeddingPipeline(provider=provider)
    batch_res = pipeline.embed_chunks(multi_language_corpus)

    index = VectorIndex()
    index.add_many(batch_res.results, chunks={c.id: c for c in multi_language_corpus.chunks})
    return index


def test_vector_retriever_initialization() -> None:
    """Verify VectorRetriever initializes with default components and contracts."""
    retriever = VectorRetriever()
    assert isinstance(retriever, VectorRetrieverContract)
    assert retriever.index is not None
    assert retriever.provider is not None
    assert retriever.preprocessor is not None


def test_vector_retrieval_basic_flow(populated_vector_index: VectorIndexContract) -> None:
    """Verify end-to-end vector retrieval workflow."""
    retriever = VectorRetriever(index=populated_vector_index)

    result_set = retriever.retrieve(
        query="How does PaymentService process payments?",
        repository_id="repo-test",
        top_k=5,
    )

    assert isinstance(result_set, RetrievalResultSet)
    assert result_set.repository_id == "repo-test"
    assert result_set.query.original_query == "How does PaymentService process payments?"
    assert result_set.total_matches > 0
    assert len(result_set.results) <= 5

    top_result = result_set.results[0]
    assert top_result.rank == 1
    assert -1.0 <= top_result.score <= 1.0


def test_cross_repository_isolation() -> None:
    """MANDATORY TEST: Verify vector search results are strictly isolated by repository_id."""
    provider = DeterministicTestEmbeddingProvider()
    pipeline = EmbeddingPipeline(provider=provider)
    index = VectorIndex()

    loc = SourceLocation(start_line=1, start_column=0, end_line=20, end_column=1)

    chunk_a = CodeChunk(
        id=generate_chunk_id(
            "repo-alpha", "PaymentService.java", ChunkType.CLASS_CONTEXT, "ent-a", loc
        ),
        chunk_type=ChunkType.CLASS_CONTEXT,
        repository_id="repo-alpha",
        file_path="PaymentService.java",
        language=Language.JAVA,
        entity_id="ent-a",
        name="PaymentService",
        source_location=loc,
        content="class PaymentService {}",
    )
    res_a = pipeline.embed_chunk(chunk_a)
    index.add(res_a, chunk=chunk_a)

    chunk_b = CodeChunk(
        id=generate_chunk_id(
            "repo-beta", "PaymentService.java", ChunkType.CLASS_CONTEXT, "ent-b", loc
        ),
        chunk_type=ChunkType.CLASS_CONTEXT,
        repository_id="repo-beta",
        file_path="PaymentService.java",
        language=Language.JAVA,
        entity_id="ent-b",
        name="PaymentService",
        source_location=loc,
        content="class PaymentService {}",
    )
    res_b = pipeline.embed_chunk(chunk_b)
    index.add(res_b, chunk=chunk_b)

    retriever = VectorRetriever(index=index, provider=provider)

    ret_a = retriever.retrieve("PaymentService", repository_id="repo-alpha")
    assert ret_a.total_matches == 1
    assert ret_a.results[0].repository_id == "repo-alpha"
    assert ret_a.results[0].chunk_id == chunk_a.id

    ret_b = retriever.retrieve("PaymentService", repository_id="repo-beta")
    assert ret_b.total_matches == 1
    assert ret_b.results[0].repository_id == "repo-beta"
    assert ret_b.results[0].chunk_id == chunk_b.id


def test_semantic_queries(populated_vector_index: VectorIndexContract) -> None:
    """Verify semantic queries return non-empty candidate sets."""
    retriever = VectorRetriever(index=populated_vector_index)

    queries = [
        "How are users authenticated?",
        "Where is financial transaction processing handled?",
        "REST API controller endpoints",
    ]

    for q in queries:
        res = retriever.retrieve(q, repository_id="repo-test", top_k=3)
        assert res.total_matches > 0
        assert len(res.results) <= 3
        assert isinstance(res.query.query_kind, QueryKind)


def test_identifier_and_mixed_queries(populated_vector_index: VectorIndexContract) -> None:
    """Verify identifier and mixed queries execute successfully."""
    retriever = VectorRetriever(index=populated_vector_index)

    id_res = retriever.retrieve("JWTAuthenticationFilter", repository_id="repo-test")
    assert id_res.total_matches > 0
    assert id_res.query.query_kind == QueryKind.IDENTIFIER

    mix_res = retriever.retrieve(
        "How does PaymentService process payments?", repository_id="repo-test"
    )
    assert mix_res.total_matches > 0


def test_filtering_capabilities(
    multi_language_corpus: CodeChunkCollection,
    populated_vector_index: VectorIndexContract,
) -> None:
    """Verify filtering by language, chunk_type, file_path, and commit_sha."""
    retriever = VectorRetriever(index=populated_vector_index)

    # Filter by Language
    py_results = retriever.retrieve(
        query="user authentication",
        repository_id="repo-test",
        language=Language.PYTHON,
    )
    assert all(r.language == Language.PYTHON for r in py_results.results)

    # Filter by ChunkType
    method_results = retriever.retrieve(
        query="payment",
        repository_id="repo-test",
        chunk_type=ChunkType.METHOD,
    )
    assert all(r.chunk_type == ChunkType.METHOD for r in method_results.results)

    # Filter by file_path
    path_results = retriever.retrieve(
        query="Payment",
        repository_id="repo-test",
        file_path="src/payment/PaymentService.java",
    )
    assert all(r.file_path == "src/payment/PaymentService.java" for r in path_results.results)

    # Filter by commit_sha
    sha_results = retriever.retrieve(
        query="Payment",
        repository_id="repo-test",
        commit_sha="sha-v1",
    )
    assert all(r.commit_sha == "sha-v1" for r in sha_results.results)


def test_referential_integrity_and_metadata_preservation(
    multi_language_corpus: CodeChunkCollection,
    populated_vector_index: VectorIndexContract,
) -> None:
    """Verify RetrievalResult preserves canonical chunk identity and source location metadata."""
    retriever = VectorRetriever(index=populated_vector_index)

    res = retriever.retrieve("get_user_by_id", repository_id="repo-test")
    assert len(res.results) > 0
    top = res.results[0]

    chunk = multi_language_corpus.get_chunk_by_id(top.chunk_id)
    assert chunk is not None
    assert top.chunk_id == chunk.id
    assert top.file_path == chunk.file_path
    assert top.language == chunk.language
    assert top.start_line == chunk.source_location.start_line
    assert top.end_line == chunk.source_location.end_line


def test_invalid_and_empty_queries() -> None:
    """Verify validation errors for empty query, missing repository_id, and invalid top_k."""
    retriever = VectorRetriever()

    with pytest.raises(VectorQueryError, match="cannot be empty"):
        retriever.retrieve("", repository_id="repo-test")

    with pytest.raises(VectorQueryError, match="repository_id cannot be empty"):
        retriever.retrieve("PaymentService", repository_id="")

    with pytest.raises(VectorQueryError, match="top_k must be > 0"):
        retriever.retrieve("PaymentService", repository_id="repo-test", top_k=0)


def test_zero_result_query() -> None:
    """Verify non-matching query or empty repository index returns zero results without exception."""
    retriever = VectorRetriever()

    res = retriever.retrieve("authentication", repository_id="repo-empty")
    assert res.total_matches == 0
    assert len(res.results) == 0


def test_top_k_limiting(populated_vector_index: VectorIndexContract) -> None:
    """Verify top_k parameter strictly limits result set length."""
    retriever = VectorRetriever(index=populated_vector_index)

    for k in (1, 3, 5):
        res = retriever.retrieve("payment processing", repository_id="repo-test", top_k=k)
        assert len(res.results) <= k


def test_deterministic_ordering_and_repeated_query(
    populated_vector_index: VectorIndexContract,
) -> None:
    """Verify repeated retrieval queries produce 100% identical ranks, scores, and chunk ordering."""
    retriever = VectorRetriever(index=populated_vector_index)

    query_str = "How are payments validated and processed?"
    run_1 = retriever.retrieve(query_str, repository_id="repo-test", top_k=5)
    run_2 = retriever.retrieve(query_str, repository_id="repo-test", top_k=5)

    assert run_1.results == run_2.results
    for r1, r2 in zip(run_1.results, run_2.results, strict=True):
        assert r1.chunk_id == r2.chunk_id
        assert r1.rank == r2.rank
        assert r1.score == r2.score


def test_index_immutability_during_search(
    multi_language_corpus: CodeChunkCollection,
    populated_vector_index: VectorIndexContract,
) -> None:
    """Verify vector search execution does not mutate index document count or stored vectors."""
    count_before = populated_vector_index.document_count("repo-test")

    retriever = VectorRetriever(index=populated_vector_index)
    retriever.retrieve("PaymentService", repository_id="repo-test")
    retriever.retrieve("JWT authentication filter", repository_id="repo-test")

    count_after = populated_vector_index.document_count("repo-test")
    assert count_before == count_after == 5


def test_no_chunk_reembedding_during_search(
    multi_language_corpus: CodeChunkCollection,
    populated_vector_index: VectorIndexContract,
) -> None:
    """Verify query search only generates 1 query embedding and does not re-embed indexed chunks."""

    class CountingEmbeddingProvider(DeterministicTestEmbeddingProvider):
        def __init__(self) -> None:
            super().__init__()
            self.call_count = 0
            self.embedded_input_count = 0

        def embed(self, inputs: list) -> list:
            self.call_count += 1
            self.embedded_input_count += len(inputs)
            return super().embed(inputs)

    counting_provider = CountingEmbeddingProvider()
    retriever = VectorRetriever(index=populated_vector_index, provider=counting_provider)

    assert counting_provider.call_count == 0
    res = retriever.retrieve("How does authentication work?", repository_id="repo-test")

    assert res.total_matches > 0
    # Exactly 1 embed call with exactly 1 query input
    assert counting_provider.call_count == 1
    assert counting_provider.embedded_input_count == 1


def test_dimension_mismatch(populated_vector_index: VectorIndexContract) -> None:
    """Verify search with query vector of mismatched dimension raises EmbeddingDimensionError."""
    # Index was populated with dimension 384 vectors
    wrong_dim_vector = [0.1] * 768

    with pytest.raises(EmbeddingDimensionError, match="dimension"):
        populated_vector_index.search(query_vector=wrong_dim_vector, repository_id="repo-test")


def test_latency_observability(populated_vector_index: VectorIndexContract) -> None:
    """Verify latency metrics are captured and non-negative."""
    retriever = VectorRetriever(index=populated_vector_index)

    res = retriever.retrieve("PaymentService", repository_id="repo-test")
    assert res.preprocessing_latency_ms >= 0.0
    assert res.retrieval_latency_ms >= 0.0
    assert res.total_latency_ms >= 0.0


def test_performance_scale_1000_chunks() -> None:
    """PERFORMANCE TEST: Scale test on 1,000 synthetic chunks measuring sub-second retrieval latency."""
    provider = DeterministicTestEmbeddingProvider()
    pipeline = EmbeddingPipeline(provider=provider)

    chunks: list[CodeChunk] = []
    loc = SourceLocation(start_line=1, start_column=0, end_line=20, end_column=0)

    for idx in range(1000):
        chunks.append(
            CodeChunk(
                id=generate_chunk_id(
                    "repo-perf", f"src/service_{idx}.py", ChunkType.FUNCTION, f"ent-{idx}", loc
                ),
                chunk_type=ChunkType.FUNCTION,
                repository_id="repo-perf",
                file_path=f"src/service_{idx}.py",
                language=Language.PYTHON,
                entity_id=f"ent-{idx}",
                name=f"process_order_{idx}",
                source_location=loc,
                content=f"def process_order_{idx}(): pass",
            )
        )

    chunk_coll = CodeChunkCollection(repository_id="repo-perf", chunks=chunks)
    batch_res = pipeline.embed_chunks(chunk_coll)

    index = VectorIndex()
    index.add_many(batch_res.results, chunks={c.id: c for c in chunk_coll.chunks})

    retriever = VectorRetriever(index=index, provider=provider)

    t0 = time.perf_counter()
    res = retriever.retrieve("process_order_500", repository_id="repo-perf", top_k=10)
    elapsed = time.perf_counter() - t0

    assert res.total_matches > 0
    assert elapsed < 1.0  # Sub-second execution threshold


def test_result_set_json_serialization(populated_vector_index: VectorIndexContract) -> None:
    """Verify RetrievalResultSet object -> JSON -> object lossless round-trip."""
    retriever = VectorRetriever(index=populated_vector_index)

    result_set = retriever.retrieve("PaymentService", repository_id="repo-test")
    json_str = result_set.model_dump_json()

    deserialized = RetrievalResultSet.model_validate_json(json_str)
    assert deserialized == result_set


def test_no_duplicate_chunk_ids(populated_vector_index: VectorIndexContract) -> None:
    """Verify vector retrieval result set contains no duplicate chunk IDs."""
    retriever = VectorRetriever(index=populated_vector_index)

    res = retriever.retrieve("payment processing", repository_id="repo-test", top_k=10)
    seen_ids = set()
    for item in res.results:
        assert item.chunk_id not in seen_ids, f"Duplicate chunk_id found: {item.chunk_id}"
        seen_ids.add(item.chunk_id)
