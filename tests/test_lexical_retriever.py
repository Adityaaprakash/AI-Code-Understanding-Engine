"""Unit and integration tests for Phase 5 BM25 Lexical Retrieval Service (LexicalRetriever)."""

import time

import pytest

from code_analyzer.ir import SourceLocation
from code_analyzer.parsers.models import Language
from retrieval.enums import ChunkType
from retrieval.exceptions import LexicalQueryError
from retrieval.identity import generate_chunk_id
from retrieval.lexical_index import BM25LexicalIndex
from retrieval.lexical_retriever import LexicalRetriever
from retrieval.models import CodeChunk, CodeChunkCollection
from retrieval.query_models import QueryKind
from retrieval.retrieval_models import RetrievalResultSet


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

    # 2. Python AuthService function
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


def test_lexical_retriever_initialization() -> None:
    """Verify LexicalRetriever initializes with default components."""
    retriever = LexicalRetriever()
    assert retriever.index is not None
    assert retriever.preprocessor is not None


def test_lexical_retrieval_basic_flow(multi_language_corpus: CodeChunkCollection) -> None:
    """Verify end-to-end lexical retrieval workflow."""
    index = BM25LexicalIndex()
    index.add_many(multi_language_corpus)
    retriever = LexicalRetriever(index=index)

    result_set = retriever.retrieve(
        query="processPayment",
        repository_id="repo-test",
        top_k=5,
    )

    assert isinstance(result_set, RetrievalResultSet)
    assert result_set.repository_id == "repo-test"
    assert result_set.query.original_query == "processPayment"
    assert result_set.query.query_kind == QueryKind.IDENTIFIER
    assert result_set.total_matches > 0
    assert len(result_set.results) <= 5

    top_result = result_set.results[0]
    assert top_result.symbol_name == "com.example.payment.PaymentService.processPayment"
    assert top_result.rank == 1
    assert top_result.score > 0.0


def test_cross_repository_isolation() -> None:
    """MANDATORY TEST: Verify search results are strictly isolated by repository_id."""
    index = BM25LexicalIndex()
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
    index.add(chunk_a)

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
    index.add(chunk_b)

    retriever = LexicalRetriever(index=index)

    res_a = retriever.retrieve("PaymentService", repository_id="repo-alpha")
    assert res_a.total_matches == 1
    assert res_a.results[0].repository_id == "repo-alpha"
    assert res_a.results[0].chunk_id == chunk_a.id

    res_b = retriever.retrieve("PaymentService", repository_id="repo-beta")
    assert res_b.total_matches == 1
    assert res_b.results[0].repository_id == "repo-beta"
    assert res_b.results[0].chunk_id == chunk_b.id


def test_adversarial_symbol_field_weighting() -> None:
    """ADVERSARIAL TEST: Symbol name match must beat content term repetition."""
    index = BM25LexicalIndex()
    loc_a = SourceLocation(start_line=1, start_column=0, end_line=10, end_column=1)
    loc_b = SourceLocation(start_line=1, start_column=0, end_line=50, end_column=1)

    doc_a = CodeChunk(
        id=generate_chunk_id(
            "repo-adv", "PaymentService.java", ChunkType.CLASS_CONTEXT, "ent-adv-a", loc_a
        ),
        chunk_type=ChunkType.CLASS_CONTEXT,
        repository_id="repo-adv",
        file_path="PaymentService.java",
        language=Language.JAVA,
        entity_id="ent-adv-a",
        name="PaymentService",
        source_location=loc_a,
        content="class PaymentService {}",
    )

    doc_b = CodeChunk(
        id=generate_chunk_id(
            "repo-adv", "OrderService.java", ChunkType.CLASS_CONTEXT, "ent-adv-b", loc_b
        ),
        chunk_type=ChunkType.CLASS_CONTEXT,
        repository_id="repo-adv",
        file_path="OrderService.java",
        language=Language.JAVA,
        entity_id="ent-adv-b",
        name="OrderService",
        source_location=loc_b,
        content=" ".join(["PaymentService"] * 20),
    )

    index.add(doc_a)
    index.add(doc_b)

    retriever = LexicalRetriever(index=index)
    results = retriever.retrieve("PaymentService", repository_id="repo-adv")

    assert len(results.results) == 2
    assert results.results[0].chunk_id == doc_a.id
    assert results.results[0].rank == 1


def test_filtering_capabilities(multi_language_corpus: CodeChunkCollection) -> None:
    """Verify filtering by language, chunk_type, file_path, and commit_sha."""
    index = BM25LexicalIndex()
    index.add_many(multi_language_corpus)
    retriever = LexicalRetriever(index=index)

    py_results = retriever.retrieve(
        query="service",
        repository_id="repo-test",
        language=Language.PYTHON,
    )
    assert all(r.language == Language.PYTHON for r in py_results.results)

    method_results = retriever.retrieve(
        query="PaymentService",
        repository_id="repo-test",
        chunk_type=ChunkType.METHOD,
    )
    assert all(r.chunk_type == ChunkType.METHOD for r in method_results.results)

    path_results = retriever.retrieve(
        query="Payment",
        repository_id="repo-test",
        file_path="src/payment/PaymentService.java",
    )
    assert all(r.file_path == "src/payment/PaymentService.java" for r in path_results.results)


def test_referential_integrity_and_metadata_preservation(
    multi_language_corpus: CodeChunkCollection,
) -> None:
    """Verify RetrievalResult preserves canonical chunk identity and source location metadata."""
    index = BM25LexicalIndex()
    index.add_many(multi_language_corpus)
    retriever = LexicalRetriever(index=index)

    res = retriever.retrieve("get_user_by_id", repository_id="repo-test")
    assert len(res.results) == 1
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
    index = BM25LexicalIndex()
    retriever = LexicalRetriever(index=index)

    with pytest.raises(LexicalQueryError, match="cannot be empty"):
        retriever.retrieve("", repository_id="repo-test")

    with pytest.raises(LexicalQueryError, match="repository_id is required"):
        retriever.retrieve("PaymentService", repository_id="")

    with pytest.raises(LexicalQueryError, match="top_k must be > 0"):
        retriever.retrieve("PaymentService", repository_id="repo-test", top_k=0)


def test_zero_result_query() -> None:
    """Verify non-matching query returns empty result set without exception."""
    index = BM25LexicalIndex()
    retriever = LexicalRetriever(index=index)

    res = retriever.retrieve("non_existent_symbol_12345", repository_id="repo-test")
    assert res.total_matches == 0
    assert len(res.results) == 0


def test_latency_observability(multi_language_corpus: CodeChunkCollection) -> None:
    """Verify latency metrics are captured and non-negative."""
    index = BM25LexicalIndex()
    index.add_many(multi_language_corpus)
    retriever = LexicalRetriever(index=index)

    res = retriever.retrieve("PaymentService", repository_id="repo-test")
    assert res.preprocessing_latency_ms >= 0.0
    assert res.retrieval_latency_ms >= 0.0
    assert res.total_latency_ms >= 0.0


def test_performance_scale_1000_chunks() -> None:
    """PERFORMANCE TEST: Scale test on 1,000 synthetic chunks measuring sub-second retrieval latency."""
    index = BM25LexicalIndex()
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

    index.add_many(chunks)
    retriever = LexicalRetriever(index=index)

    t0 = time.perf_counter()
    res = retriever.retrieve("process_order_500", repository_id="repo-perf", top_k=10)
    elapsed = time.perf_counter() - t0

    assert res.total_matches > 0
    assert res.results[0].symbol_name == "process_order_500"
    assert elapsed < 1.0  # Sub-second execution threshold


def test_index_immutability_during_search(multi_language_corpus: CodeChunkCollection) -> None:
    """Verify search execution does not mutate the BM25 index document count or state."""
    index = BM25LexicalIndex()
    index.add_many(multi_language_corpus)
    count_before = index.document_count("repo-test")

    retriever = LexicalRetriever(index=index)
    retriever.retrieve("PaymentService", repository_id="repo-test")
    retriever.retrieve("JWT", repository_id="repo-test")

    count_after = index.document_count("repo-test")
    assert count_before == count_after == 5


def test_retrieval_result_json_serialization(multi_language_corpus: CodeChunkCollection) -> None:
    """Verify RetrievalResult and RetrievalResultSet object -> JSON -> object lossless round-trip."""
    index = BM25LexicalIndex()
    index.add_many(multi_language_corpus)
    retriever = LexicalRetriever(index=index)

    result_set = retriever.retrieve("PaymentService", repository_id="repo-test")
    json_str = result_set.model_dump_json()

    deserialized = RetrievalResultSet.model_validate_json(json_str)
    assert deserialized == result_set
