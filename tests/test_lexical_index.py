"""Unit and integration tests for BM25 lexical code indexing."""

import pytest
from pydantic import ValidationError

from code_analyzer.ir import File, SourceLocation
from code_analyzer.normalization import NormalizationResult
from code_analyzer.parsers.models import Language
from retrieval.chunker import CodeChunker
from retrieval.enums import ChunkType
from retrieval.exceptions import LexicalConfigurationError, LexicalQueryError
from retrieval.lexical_index import BM25LexicalIndex
from retrieval.lexical_models import LexicalSearchResult
from retrieval.lexical_text_builder import LexicalTextBuilder
from retrieval.models import CodeChunk
from retrieval.tokenizer import CodeTokenizer, tokenize_code, tokenize_query

# ------------------------------------------------------------------------------
# Test Fixtures & Helpers
# ------------------------------------------------------------------------------


@pytest.fixture
def sample_python_chunk() -> CodeChunk:
    return CodeChunk(
        id="chunk-py-101",
        chunk_type=ChunkType.FUNCTION,
        repository_id="repo-python",
        file_path="backend/payment/processor.py",
        entity_id="func-py-101",
        name="process_payment",
        qualified_name="backend.payment.processor.process_payment",
        signature="def process_payment(user_id: str, amount: float) -> bool:",
        doc_comment="Process payment transaction for user with JWT token validation.",
        content=(
            "def process_payment(user_id: str, amount: float) -> bool:\n"
            "    token = get_jwt_token(user_id)\n"
            "    return PaymentGateway.execute(token, amount)\n"
        ),
        language=Language.PYTHON,
        source_location=SourceLocation(start_line=10, start_column=0, end_line=15, end_column=0),
    )


@pytest.fixture
def sample_java_chunk() -> CodeChunk:
    return CodeChunk(
        id="chunk-java-202",
        chunk_type=ChunkType.CLASS_CONTEXT,
        repository_id="repo-java",
        file_path="src/main/java/com/example/payment/PaymentService.java",
        entity_id="class-java-202",
        name="PaymentService",
        qualified_name="com.example.payment.PaymentService",
        signature="public class PaymentService implements IPaymentService",
        doc_comment="Core PaymentService handling credit card and JWT authentication.",
        content="public class PaymentService {\n    private JWTAuthenticationFilter filter;\n}",
        language=Language.JAVA,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=20, end_column=0),
    )


@pytest.fixture
def sample_ts_chunk() -> CodeChunk:
    return CodeChunk(
        id="chunk-ts-303",
        chunk_type=ChunkType.METHOD,
        repository_id="repo-ts",
        file_path="src/services/AuthService.ts",
        entity_id="method-ts-303",
        name="authenticateUser",
        qualified_name="AuthService.authenticateUser",
        signature="async authenticateUser(credentials: UserCredentials): Promise<AuthToken>",
        doc_comment="Authenticate user with JWT token credentials.",
        content=(
            "async authenticateUser(credentials: UserCredentials): Promise<AuthToken> {\n"
            "    const token = await jwt.sign(credentials);\n"
            "    return token;\n"
            "}"
        ),
        language=Language.TYPESCRIPT,
        source_location=SourceLocation(start_line=5, start_column=4, end_line=15, end_column=5),
    )


# ------------------------------------------------------------------------------
# 1. Code-Aware Tokenizer Tests
# ------------------------------------------------------------------------------


def test_tokenizer_camel_case() -> None:
    tokenizer = CodeTokenizer()
    tokens = tokenizer.tokenize("processPayment")

    assert "processpayment" in tokens
    assert "process" in tokens
    assert "payment" in tokens


def test_tokenizer_pascal_case() -> None:
    tokenizer = CodeTokenizer()
    tokens = tokenizer.tokenize("PaymentService")

    assert "paymentservice" in tokens
    assert "payment" in tokens
    assert "service" in tokens


def test_tokenizer_snake_case() -> None:
    tokenizer = CodeTokenizer()
    tokens = tokenizer.tokenize("get_user_by_id")

    assert "get_user_by_id" in tokens
    assert "get" in tokens
    assert "user" in tokens
    assert "by" in tokens
    assert "id" in tokens


def test_tokenizer_screaming_snake_case() -> None:
    tokenizer = CodeTokenizer()
    tokens = tokenizer.tokenize("MAX_RETRY_COUNT")

    assert "max_retry_count" in tokens
    assert "max" in tokens
    assert "retry" in tokens
    assert "count" in tokens


def test_tokenizer_acronyms() -> None:
    tokenizer = CodeTokenizer()
    tokens = tokenizer.tokenize("JWTAuthenticationFilter")

    assert "jwtauthenticationfilter" in tokens
    assert "jwt" in tokens
    assert "authentication" in tokens
    assert "filter" in tokens


def test_tokenizer_qualified_names() -> None:
    tokenizer = CodeTokenizer()
    tokens = tokenizer.tokenize("com.example.payment.PaymentService.processPayment")

    assert "com.example.payment.paymentservice.processpayment" in tokens
    assert "com" in tokens
    assert "example" in tokens
    assert "payment" in tokens
    assert "paymentservice" in tokens
    assert "processpayment" in tokens
    assert "process" in tokens


def test_tokenizer_file_paths() -> None:
    tokenizer = CodeTokenizer()
    tokens = tokenizer.tokenize("src/auth/AuthService.java")

    assert "src/auth/authservice.java" in tokens
    assert "src" in tokens
    assert "auth" in tokens
    assert "authservice" in tokens
    assert "java" in tokens


def test_tokenizer_empty_and_whitespace() -> None:
    tokenizer = CodeTokenizer()
    assert tokenizer.tokenize("") == []
    assert tokenizer.tokenize("   \n\t ") == []


def test_query_tokenizer_parity() -> None:
    t_code = tokenize_code("PaymentService.processPayment")
    t_query = tokenize_query("PaymentService.processPayment")

    assert t_code == t_query


# ------------------------------------------------------------------------------
# 2. Lexical Models Validation Tests
# ------------------------------------------------------------------------------


def test_lexical_document_validation(sample_python_chunk: CodeChunk) -> None:
    builder = LexicalTextBuilder()
    doc = builder.build_document(sample_python_chunk)

    assert doc.chunk_id == "chunk-py-101"
    assert doc.repository_id == "repo-python"
    assert doc.file_path == "backend/payment/processor.py"
    assert doc.symbol_name == "backend.payment.processor.process_payment"
    assert doc.doc_len > 0
    assert "process_payment" in doc.all_tokens

    # Verify immutability
    with pytest.raises(ValidationError):
        doc.chunk_id = "modified-id"


def test_lexical_search_result_validation() -> None:
    res = LexicalSearchResult(
        chunk_id="chunk-1",
        score=2.5,
        rank=1,
        repository_id="repo-1",
        file_path="src/main.py",
        chunk_type=ChunkType.FUNCTION,
        language=Language.PYTHON,
    )

    assert res.score == 2.5
    assert res.rank == 1

    with pytest.raises(ValidationError):
        LexicalSearchResult(
            chunk_id="chunk-1",
            score=float("nan"),
            rank=1,
            repository_id="repo-1",
            file_path="src/main.py",
            chunk_type=ChunkType.FUNCTION,
            language=Language.PYTHON,
        )

    with pytest.raises(ValidationError):
        LexicalSearchResult(
            chunk_id="chunk-1",
            score=1.0,
            rank=0,  # Must be >= 1
            repository_id="repo-1",
            file_path="src/main.py",
            chunk_type=ChunkType.FUNCTION,
            language=Language.PYTHON,
        )


# ------------------------------------------------------------------------------
# 3. Exact Identifier Matching & Search Ranking Tests
# ------------------------------------------------------------------------------


def test_exact_identifier_ranking() -> None:
    index = BM25LexicalIndex()
    repo_id = "repo-exact"

    c1 = CodeChunk(
        id="chunk-1",
        chunk_type=ChunkType.CLASS_CONTEXT,
        repository_id=repo_id,
        file_path="src/PaymentService.java",
        name="PaymentService",
        qualified_name="PaymentService",
        content="public class PaymentService {}",
        language=Language.JAVA,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=5, end_column=0),
    )

    c2 = CodeChunk(
        id="chunk-2",
        chunk_type=ChunkType.CLASS_CONTEXT,
        repository_id=repo_id,
        file_path="src/PaymentRepository.java",
        name="PaymentRepository",
        qualified_name="PaymentRepository",
        content="public class PaymentRepository {}",
        language=Language.JAVA,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=5, end_column=0),
    )

    c3 = CodeChunk(
        id="chunk-3",
        chunk_type=ChunkType.CLASS_CONTEXT,
        repository_id=repo_id,
        file_path="src/OrderService.java",
        name="OrderService",
        qualified_name="OrderService",
        content="public class OrderService { private PaymentService service; }",
        language=Language.JAVA,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=5, end_column=0),
    )

    index.add_many([c1, c2, c3])

    results = index.search(query="PaymentService", repository_id=repo_id, top_k=10)

    assert len(results) >= 2
    # chunk-1 (whose symbol is PaymentService) must rank #1
    assert results[0].chunk_id == "chunk-1"
    assert results[0].rank == 1
    assert results[0].score > results[1].score


def test_field_weighting_symbol_boost() -> None:
    index = BM25LexicalIndex()
    repo_id = "repo-weight"

    # Chunk with symbol_name = "AuthService"
    c_symbol = CodeChunk(
        id="chunk-symbol",
        chunk_type=ChunkType.CLASS_CONTEXT,
        repository_id=repo_id,
        file_path="src/AuthService.java",
        name="AuthService",
        qualified_name="AuthService",
        content="public class AuthService {}",
        language=Language.JAVA,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=5, end_column=0),
    )

    # Huge chunk mentioning AuthService deep inside body
    c_body = CodeChunk(
        id="chunk-body",
        chunk_type=ChunkType.FUNCTION,
        repository_id=repo_id,
        file_path="src/UnrelatedLogger.java",
        name="logSystemEvent",
        content="void logSystemEvent() { log('Calling AuthService for user validation'); }",
        language=Language.JAVA,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=10, end_column=0),
    )

    index.add_many([c_symbol, c_body])
    results = index.search("AuthService", repository_id=repo_id, top_k=10)

    assert len(results) == 2
    assert results[0].chunk_id == "chunk-symbol"


# ------------------------------------------------------------------------------
# 4. Repository Isolation Suite
# ------------------------------------------------------------------------------


def test_repository_isolation() -> None:
    index = BM25LexicalIndex()

    c_repo_a = CodeChunk(
        id="chunk-a",
        chunk_type=ChunkType.FUNCTION,
        repository_id="repo-A",
        file_path="src/payment.py",
        name="process_payment",
        content="def process_payment(): pass",
        language=Language.PYTHON,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=2, end_column=0),
    )

    c_repo_b = CodeChunk(
        id="chunk-b",
        chunk_type=ChunkType.FUNCTION,
        repository_id="repo-B",
        file_path="src/payment.py",
        name="process_payment",
        content="def process_payment(): pass",
        language=Language.PYTHON,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=2, end_column=0),
    )

    index.add_many([c_repo_a, c_repo_b])

    # Search in Repo A must NEVER return chunk-b from Repo B
    res_a = index.search("process_payment", repository_id="repo-A", top_k=10)
    assert len(res_a) == 1
    assert res_a[0].chunk_id == "chunk-a"
    assert res_a[0].repository_id == "repo-A"

    # Search in Repo B must NEVER return chunk-a from Repo A
    res_b = index.search("process_payment", repository_id="repo-B", top_k=10)
    assert len(res_b) == 1
    assert res_b[0].chunk_id == "chunk-b"
    assert res_b[0].repository_id == "repo-B"


# ------------------------------------------------------------------------------
# 5. Index Lifecycle Suite (add, add_many, remove, clear, replacement)
# ------------------------------------------------------------------------------


def test_index_lifecycle(sample_python_chunk: CodeChunk, sample_java_chunk: CodeChunk) -> None:
    index = BM25LexicalIndex()
    repo_id = sample_python_chunk.repository_id

    # 1. Add single chunk
    index.add(sample_python_chunk)
    assert index.document_count(repo_id) == 1

    # 2. Search chunk
    res = index.search("process_payment", repository_id=repo_id)
    assert len(res) == 1
    assert res[0].chunk_id == sample_python_chunk.id

    # 3. Remove chunk
    removed = index.remove(sample_python_chunk.id, repository_id=repo_id)
    assert removed is True
    assert index.document_count(repo_id) == 0

    res_after_remove = index.search("process_payment", repository_id=repo_id)
    assert res_after_remove == []

    # 4. Re-add and clear
    index.add(sample_python_chunk)
    assert index.document_count(repo_id) == 1
    index.clear(repo_id)
    assert index.document_count(repo_id) == 0


def test_deterministic_chunk_replacement(sample_python_chunk: CodeChunk) -> None:
    index = BM25LexicalIndex()
    repo_id = sample_python_chunk.repository_id

    # Initial chunk
    index.add(sample_python_chunk)
    assert index.document_count(repo_id) == 1

    res1 = index.search("JWT", repository_id=repo_id)
    assert len(res1) == 1

    # Updated chunk with same chunk_id but new content
    updated_chunk = CodeChunk(
        id=sample_python_chunk.id,
        chunk_type=sample_python_chunk.chunk_type,
        repository_id=sample_python_chunk.repository_id,
        file_path=sample_python_chunk.file_path,
        name=sample_python_chunk.name,
        content="def process_payment(): return OAuth2Gateway.execute()",
        language=sample_python_chunk.language,
        source_location=sample_python_chunk.source_location,
    )

    index.add(updated_chunk)

    # Document count must remain 1 (no duplicate document created)
    assert index.document_count(repo_id) == 1

    # Old term "JWT" should no longer match
    res_jwt = index.search("JWT", repository_id=repo_id)
    assert len(res_jwt) == 0

    # New term "OAuth2Gateway" should match
    res_oauth = index.search("OAuth2Gateway", repository_id=repo_id)
    assert len(res_oauth) == 1
    assert res_oauth[0].chunk_id == sample_python_chunk.id


# ------------------------------------------------------------------------------
# 6. Edge Cases & Validation Tests
# ------------------------------------------------------------------------------


def test_empty_index_and_empty_query() -> None:
    index = BM25LexicalIndex()

    # Search empty index
    assert index.search("processPayment", repository_id="non-existent") == []

    # Search with empty query
    index.add(
        CodeChunk(
            id="c1",
            chunk_type=ChunkType.FUNCTION,
            repository_id="repo-1",
            file_path="test.py",
            content="def test(): pass",
            language=Language.PYTHON,
            source_location=SourceLocation(start_line=1, start_column=0, end_line=2, end_column=0),
        )
    )

    assert index.search("", repository_id="repo-1") == []
    assert index.search("   \n\t  ", repository_id="repo-1") == []


def test_invalid_query_parameters() -> None:
    index = BM25LexicalIndex()

    with pytest.raises(LexicalQueryError):
        index.search("query", repository_id="repo-1", top_k=0)

    with pytest.raises(LexicalQueryError):
        index.search("query", repository_id="repo-1", top_k=-5)

    with pytest.raises(LexicalConfigurationError):
        BM25LexicalIndex(k1=-1.0)

    with pytest.raises(LexicalConfigurationError):
        BM25LexicalIndex(b=1.5)


def test_top_k_truncation() -> None:
    index = BM25LexicalIndex()
    repo_id = "repo-topk"

    chunks = [
        CodeChunk(
            id=f"chunk-{i}",
            chunk_type=ChunkType.FUNCTION,
            repository_id=repo_id,
            file_path=f"src/file{i}.py",
            name="common_function",
            content=f"def common_function(): # iteration {i}\n pass",
            language=Language.PYTHON,
            source_location=SourceLocation(start_line=1, start_column=0, end_line=3, end_column=0),
        )
        for i in range(20)
    ]

    index.add_many(chunks)

    res5 = index.search("common_function", repository_id=repo_id, top_k=5)
    assert len(res5) == 5

    res3 = index.search("common_function", repository_id=repo_id, top_k=3)
    assert len(res3) == 3


def test_deterministic_tie_breaking() -> None:
    index = BM25LexicalIndex()
    repo_id = "repo-tie"

    # Chunks with identical content and scores
    c_b = CodeChunk(
        id="chunk-B",
        chunk_type=ChunkType.FUNCTION,
        repository_id=repo_id,
        file_path="src/file.py",
        name="do_work",
        content="def do_work(): pass",
        language=Language.PYTHON,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=2, end_column=0),
    )

    c_a = CodeChunk(
        id="chunk-A",
        chunk_type=ChunkType.FUNCTION,
        repository_id=repo_id,
        file_path="src/file.py",
        name="do_work",
        content="def do_work(): pass",
        language=Language.PYTHON,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=2, end_column=0),
    )

    index.add_many([c_b, c_a])
    res = index.search("do_work", repository_id=repo_id, top_k=10)

    assert len(res) == 2
    # Scores are identical, tie-breaker orders chunk-A before chunk-B alphabetically
    assert res[0].chunk_id == "chunk-A"
    assert res[1].chunk_id == "chunk-B"


# ------------------------------------------------------------------------------
# 7. Cross-Language Parity Suite (Java, Python, TypeScript)
# ------------------------------------------------------------------------------


def test_cross_language_parity(
    sample_python_chunk: CodeChunk, sample_java_chunk: CodeChunk, sample_ts_chunk: CodeChunk
) -> None:
    index = BM25LexicalIndex()
    repo_id = "repo-multi-lang"

    # Normalize repo_id to group in single repository for cross-language testing
    ch_py = sample_python_chunk.model_copy(update={"repository_id": repo_id})
    ch_java = sample_java_chunk.model_copy(update={"repository_id": repo_id})
    ch_ts = sample_ts_chunk.model_copy(update={"repository_id": repo_id})

    index.add_many([ch_py, ch_java, ch_ts])

    assert index.document_count(repo_id) == 3

    # All three chunks contain JWT authentication / token references
    results = index.search("JWT token", repository_id=repo_id, top_k=10)

    assert len(results) == 3
    found_languages = {r.language for r in results}
    assert found_languages == {Language.PYTHON, Language.JAVA, Language.TYPESCRIPT}


# ------------------------------------------------------------------------------
# 8. Performance & Synthetic Scale Sanity
# ------------------------------------------------------------------------------


def test_synthetic_scale_performance() -> None:
    index = BM25LexicalIndex()
    repo_id = "repo-perf"

    chunks = [
        CodeChunk(
            id=f"perf-chunk-{i}",
            chunk_type=ChunkType.METHOD if i % 2 == 0 else ChunkType.FUNCTION,
            repository_id=repo_id,
            file_path=f"src/module_{i % 50}/service_{i}.py",
            name=f"execute_task_{i}",
            qualified_name=f"module_{i % 50}.Service{i}.execute_task_{i}",
            signature=f"def execute_task_{i}(param_{i}: int) -> str:",
            doc_comment=f"Execute automated batch task number {i} with error handling.",
            content=f"def execute_task_{i}():\n    return TaskRunner.process({i})\n",
            language=Language.PYTHON,
            source_location=SourceLocation(start_line=1, start_column=0, end_line=10, end_column=0),
        )
        for i in range(1000)
    ]

    # Index 1,000 synthetic chunks
    index.add_many(chunks)
    assert index.document_count(repo_id) == 1000

    # Execute search queries
    res = index.search("execute_task_500", repository_id=repo_id, top_k=5)
    assert len(res) > 0
    assert res[0].chunk_id == "perf-chunk-500"


# ------------------------------------------------------------------------------
# 9. Immutability & Canonical IR Integrity Suite
# ------------------------------------------------------------------------------


def test_chunk_and_ir_immutability(sample_python_chunk: CodeChunk) -> None:
    chunker = CodeChunker()
    file_entity = File(
        id="file-sample",
        repository_id="repo-sample",
        path="src/sample.py",
        name="sample.py",
        language=Language.PYTHON,
        loc=3,
    )
    norm_result = NormalizationResult(file=file_entity)

    chunks = chunker.chunk_normalization_result(norm_result, source_code="def sample_func(): pass")
    chunk_before = chunks.chunks[0].model_dump()

    index = BM25LexicalIndex()
    index.add_many(chunks)
    index.search("sample_func", repository_id=chunks.chunks[0].repository_id)

    chunk_after = chunks.chunks[0].model_dump()

    # CodeChunk must be byte-for-byte unchanged after lexical indexing
    assert chunk_before == chunk_after
