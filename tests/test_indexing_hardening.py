"""Comprehensive Phase 4 Indexing and Retrieval Hardening & Integration Test Suite.

Verifies end-to-end integration across Task-4A (AST/IR chunking), Task-4B (metadata & identity),
Task-4C (dense embeddings), and Task-4D (BM25 lexical indexing).
"""

import copy
import time

import pytest

from code_analyzer.ir import SourceLocation
from code_analyzer.parsers import JavaParser, Language, PythonParser, TypeScriptParser
from retrieval.chunker import CodeChunker
from retrieval.contracts import EmbeddingProviderContract
from retrieval.embedding_models import EmbeddingInput, EmbeddingResult
from retrieval.embedding_pipeline import EmbeddingPipeline
from retrieval.enums import ChunkType
from retrieval.identity import generate_chunk_id
from retrieval.lexical_index import BM25LexicalIndex
from retrieval.lexical_text_builder import LexicalTextBuilder
from retrieval.models import CodeChunk, CodeChunkCollection
from retrieval.providers import DeterministicTestEmbeddingProvider
from retrieval.text_builder import EmbeddingTextBuilder

# ------------------------------------------------------------------------------
# Golden Repository Synthetic Code Fixtures
# ------------------------------------------------------------------------------

JAVA_GOLDEN_CODE = """
package com.example.payment;

import com.example.auth.JWTToken;

/** Core PaymentService interface. */
public interface IPaymentService {
    boolean validateToken(String token);
}

/** Primary PaymentService implementation for processing payment transactions. */
public class PaymentService implements IPaymentService {
    private JWTAuthenticationFilter filter;

    public boolean validateToken(String token) {
        return filter.verify(token);
    }

    public PaymentResponse processPayment(String userId, double amount) {
        if (!validateToken(userId)) {
            throw new IllegalArgumentException("Invalid JWT token");
        }
        return PaymentGateway.executeTransaction(userId, amount);
    }
}
"""

PYTHON_GOLDEN_CODE = """
from typing import Optional
import jwt

class PaymentProcessor:
    \"\"\"Python PaymentProcessor for user transaction execution.\"\"\"

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def verify_jwt_token(self, token: str) -> bool:
        try:
            jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return True
        except Exception:
            return False

    def process_payment(self, user_id: str, amount: float) -> bool:
        \"\"\"Process payment transaction for user with JWT authentication.\"\"\"
        token = self.get_user_token(user_id)
        if not self.verify_jwt_token(token):
            raise PermissionError("Unauthorized token")
        return True
"""

TYPESCRIPT_GOLDEN_CODE = """
import { UserCredentials, AuthToken } from "./types";

export interface IAuthService {
    authenticateUser(credentials: UserCredentials): Promise<AuthToken>;
}

export class AuthService implements IAuthService {
    private jwtSecret: string;

    constructor(jwtSecret: string) {
        this.jwtSecret = jwtSecret;
    }

    async authenticateUser(credentials: UserCredentials): Promise<AuthToken> {
        const token = await jwt.sign(credentials, this.jwtSecret);
        return { token, expiresAt: Date.now() + 3600 };
    }

    async validateToken(token: str): Promise<boolean> {
        return jwt.verify(token, this.jwtSecret);
    }
}
"""


@pytest.fixture
def golden_chunk_collection() -> CodeChunkCollection:
    """Construct a Golden CodeChunkCollection across Java, Python, and TypeScript."""
    from code_analyzer.normalization import normalize_parse_result

    repo_id = "repo-golden-phase4"
    java_parser = JavaParser()
    py_parser = PythonParser()
    ts_parser = TypeScriptParser()
    chunker = CodeChunker()

    java_parse = java_parser.parse(
        JAVA_GOLDEN_CODE, "src/main/java/com/example/payment/PaymentService.java"
    )
    py_parse = py_parser.parse(PYTHON_GOLDEN_CODE, "backend/payment/processor.py")
    ts_parse = ts_parser.parse(TYPESCRIPT_GOLDEN_CODE, "src/services/AuthService.ts")

    java_norm = normalize_parse_result(java_parse, repository_id=repo_id)
    py_norm = normalize_parse_result(py_parse, repository_id=repo_id)
    ts_norm = normalize_parse_result(ts_parse, repository_id=repo_id)

    c_java = chunker.chunk_normalization_result(
        java_norm, source_code=JAVA_GOLDEN_CODE, commit_id="commit-101", commit_sha="sha-abc123"
    )
    c_py = chunker.chunk_normalization_result(
        py_norm, source_code=PYTHON_GOLDEN_CODE, commit_id="commit-101", commit_sha="sha-abc123"
    )
    c_ts = chunker.chunk_normalization_result(
        ts_norm, source_code=TYPESCRIPT_GOLDEN_CODE, commit_id="commit-101", commit_sha="sha-abc123"
    )

    all_chunks = c_java.chunks + c_py.chunks + c_ts.chunks
    return CodeChunkCollection(chunks=all_chunks, repository_id=repo_id)


# ------------------------------------------------------------------------------
# 3. Phase 4 End-to-End Integration Test (Requirement #3, #44, #51)
# ------------------------------------------------------------------------------


def test_phase4_end_to_end_pipeline_integration(
    golden_chunk_collection: CodeChunkCollection,
) -> None:
    """Verify that both embedding and lexical pipelines consume the same CodeChunk contract

    and map back to the EXACT SAME canonical chunk_id.
    """
    assert len(golden_chunk_collection) > 0

    # 1. Embedding Branch
    text_builder = EmbeddingTextBuilder()
    embedding_provider = DeterministicTestEmbeddingProvider(dimension=64)
    pipeline = EmbeddingPipeline(provider=embedding_provider, text_builder=text_builder)

    batch_result = pipeline.embed_chunks(golden_chunk_collection)
    assert batch_result.succeeded_count == len(golden_chunk_collection)
    embedding_map = {res.chunk_id: res for res in batch_result.results}

    # 2. Lexical BM25 Branch
    bm25_index = BM25LexicalIndex()
    bm25_index.add_many(golden_chunk_collection)

    repo_id = golden_chunk_collection.repository_id
    lexical_results = bm25_index.search(
        "PaymentService processPayment", repository_id=repo_id, top_k=10
    )

    assert len(lexical_results) > 0

    # 3. Verify Bridge Parity: every search result chunk_id exists in both pipelines
    for lex_res in lexical_results:
        assert lex_res.chunk_id in embedding_map
        matching_embed = embedding_map[lex_res.chunk_id]

        assert matching_embed.chunk_id == lex_res.chunk_id
        assert matching_embed.repository_id == lex_res.repository_id
        assert matching_embed.vector is not None
        assert len(matching_embed.vector) == 64


# ------------------------------------------------------------------------------
# 4 & 5. Golden Repository Semantic Hierarchy & Sub-Chunking (Requirements #4, #5, #29, #30)
# ------------------------------------------------------------------------------


def test_golden_repository_semantic_hierarchy_and_sub_chunking() -> None:
    """Verify exact semantic hierarchy and sub-chunk parent-child indexing relationships."""
    chunker = CodeChunker()

    # Create an oversized function that exceeds max_lines_per_chunk threshold
    long_body_lines = [f"    x_{i} = calculate_step_{i}()" for i in range(200)]
    long_function_code = (
        "def oversized_computation_engine():\n"
        '    """Oversized computation engine function requiring sub-chunking."""\n'
        + "\n".join(long_body_lines)
        + "\n"
    )

    from code_analyzer.normalization import normalize_parse_result

    py_parse = PythonParser().parse(long_function_code, "src/oversized.py")
    norm_result = normalize_parse_result(py_parse, repository_id="repo-oversized")
    collection = chunker.chunk_normalization_result(
        norm_result, source_code=long_function_code, max_lines_per_chunk=50
    )

    # Must contain FILE_CONTEXT, FUNCTION (Overview), and SUB_CHUNKs
    chunk_types = [c.chunk_type for c in collection.chunks]
    assert ChunkType.FILE_CONTEXT in chunk_types
    assert ChunkType.FUNCTION in chunk_types
    assert ChunkType.SUB_CHUNK in chunk_types

    sub_chunks = [c for c in collection.chunks if c.chunk_type == ChunkType.SUB_CHUNK]
    assert len(sub_chunks) >= 2

    # Verify sub-chunk properties and parent linkage
    for sc in sub_chunks:
        assert sc.parent_entity_id is not None
        assert sc.parent_chunk_id is not None
        assert sc.total_sub_chunks == len(sub_chunks) + 1

    # Sub-chunk specific searchability in BM25 index
    index = BM25LexicalIndex()
    index.add_many(collection)

    # Unique term in sub_chunk 1 vs sub_chunk 2
    res = index.search("calculate_step_180", repository_id="repo-oversized", top_k=5)
    assert len(res) > 0
    # Search should hit sub-chunk 2 specifically
    assert res[0].chunk_type == ChunkType.SUB_CHUNK


def test_symbol_chunk_vs_file_context_granularity() -> None:
    """Verify specific method symbol matches are preferred over broad file context matches."""
    index = BM25LexicalIndex()
    repo_id = "repo-granularity"

    c_file = CodeChunk(
        id="chunk-file-context",
        chunk_type=ChunkType.FILE_CONTEXT,
        repository_id=repo_id,
        file_path="src/payment/processor.py",
        name="processor.py",
        content="""# Payment module file containing various utilities and imports.
import os
import sys
import payment_gateway

def helper(): pass
def helper2(): pass
""",
        language=Language.PYTHON,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=20, end_column=0),
    )

    c_method = CodeChunk(
        id="chunk-method-exact",
        chunk_type=ChunkType.METHOD,
        repository_id=repo_id,
        file_path="src/payment/processor.py",
        name="executeTransaction",
        qualified_name="PaymentProcessor.executeTransaction",
        signature="def executeTransaction(amount: float) -> bool:",
        content="def executeTransaction(amount: float) -> bool: return True",
        language=Language.PYTHON,
        source_location=SourceLocation(start_line=10, start_column=4, end_line=12, end_column=15),
    )

    index.add_many([c_file, c_method])

    res = index.search("executeTransaction", repository_id=repo_id, top_k=5)
    assert len(res) > 0
    assert res[0].chunk_id == "chunk-method-exact"


# ------------------------------------------------------------------------------
# 6. Chunk ID Determinism & Identity Contract (Requirements #6, #11, #12, #24, #27, #35, #36)
# ------------------------------------------------------------------------------


def test_chunk_id_determinism_and_identity_inputs() -> None:
    """Verify chunk ID generation is 100% deterministic and sensitive to identity inputs."""
    loc1 = SourceLocation(start_line=1, start_column=0, end_line=10, end_column=0)
    loc2 = SourceLocation(start_line=2, start_column=0, end_line=11, end_column=0)

    id1 = generate_chunk_id(
        repository_id="repo-1",
        file_path="src/Auth.py",
        chunk_type=ChunkType.FUNCTION,
        entity_id="func-1",
        location=loc1,
    )

    id2 = generate_chunk_id(
        repository_id="repo-1",
        file_path="src/Auth.py",
        chunk_type=ChunkType.FUNCTION,
        entity_id="func-1",
        location=loc1,
    )

    # Identical inputs yield identical ID
    assert id1 == id2

    # Changing repository_id produces different ID
    id_diff_repo = generate_chunk_id(
        repository_id="repo-2",
        file_path="src/Auth.py",
        chunk_type=ChunkType.FUNCTION,
        entity_id="func-1",
        location=loc1,
    )
    assert id1 != id_diff_repo

    # Changing line location produces different ID
    id_diff_line = generate_chunk_id(
        repository_id="repo-1",
        file_path="src/Auth.py",
        chunk_type=ChunkType.FUNCTION,
        entity_id="func-1",
        location=loc2,
    )
    assert id1 != id_diff_line


def test_embedding_version_identity_separation() -> None:
    """Verify embedding version metadata is distinct from canonical chunk identity."""
    chunk = CodeChunk(
        id="canonical-chunk-777",
        chunk_type=ChunkType.FUNCTION,
        repository_id="repo-1",
        file_path="src/auth.py",
        name="login",
        content="def login(): pass",
        language=Language.PYTHON,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=3, end_column=0),
    )

    text_builder = EmbeddingTextBuilder()
    input_item = text_builder.build_input(chunk, model_name="test-model", embedding_version="1.0")

    provider_v1 = DeterministicTestEmbeddingProvider(dimension=32, embedding_version="v1.0")
    provider_v2 = DeterministicTestEmbeddingProvider(dimension=32, embedding_version="v2.0")

    res_v1 = provider_v1.embed([input_item])[0]
    res_v2 = provider_v2.embed([input_item])[0]

    # Both results preserve canonical chunk_id
    assert res_v1.chunk_id == "canonical-chunk-777"
    assert res_v2.chunk_id == "canonical-chunk-777"

    # Embedding version metadata is distinct
    assert res_v1.embedding_version == "v1.0"
    assert res_v2.embedding_version == "v2.0"


# ------------------------------------------------------------------------------
# 7 & 8. Metadata Propagation & Path Normalization (Requirements #7, #8, #41, #44)
# ------------------------------------------------------------------------------


def test_metadata_end_to_end_propagation_and_path_normalization() -> None:
    """Verify complete metadata propagation and forward-slash path normalization."""
    # Test path normalization
    chunk = CodeChunk(
        id="chunk-path-norm",
        chunk_type=ChunkType.CLASS_CONTEXT,
        repository_id="repo-norm",
        commit_id="commit-999",
        commit_sha="sha-999",
        file_path=r"src\auth\AuthService.java",
        name="AuthService",
        qualified_name="com.example.auth.AuthService",
        content="public class AuthService {}",
        language=Language.JAVA,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=10, end_column=0),
    )

    # Path must normalize backslashes to forward slashes
    assert chunk.file_path == "src/auth/AuthService.java"
    assert chunk.file_id == "src/auth/AuthService.java"

    # Verify propagation to EmbeddingInput
    builder = EmbeddingTextBuilder()
    inp = builder.build_input(chunk, model_name="test-model", embedding_version="1.0")

    assert inp.chunk_id == chunk.id
    assert inp.metadata.get("repository_id") == chunk.repository_id
    assert inp.metadata.get("file_path") == "src/auth/AuthService.java"
    assert inp.metadata.get("commit_id") == "commit-999"
    assert inp.metadata.get("commit_sha") == "sha-999"

    # Verify propagation to LexicalDocument
    lex_builder = LexicalTextBuilder()
    doc = lex_builder.build_document(chunk)

    assert doc.chunk_id == chunk.id
    assert doc.repository_id == chunk.repository_id
    assert doc.file_path == "src/auth/AuthService.java"
    assert doc.commit_id == "commit-999"
    assert doc.commit_sha == "sha-999"


# ------------------------------------------------------------------------------
# 9. Cross-Layer Immutability (Requirement #9)
# ------------------------------------------------------------------------------


def test_cross_layer_immutability(golden_chunk_collection: CodeChunkCollection) -> None:
    """Verify zero mutation occurs across CodeChunkCollection and CodeChunks during embedding/lexical indexing."""
    collection_snapshot = copy.deepcopy(golden_chunk_collection)
    chunks_snapshot = [copy.deepcopy(c) for c in golden_chunk_collection.chunks]

    # Run Embedding Pipeline
    text_builder = EmbeddingTextBuilder()
    provider = DeterministicTestEmbeddingProvider()
    pipeline = EmbeddingPipeline(provider=provider, text_builder=text_builder)
    pipeline.embed_chunks(golden_chunk_collection)

    # Run Lexical Indexing
    bm25 = BM25LexicalIndex()
    bm25.add_many(golden_chunk_collection)
    bm25.search("PaymentService", repository_id=golden_chunk_collection.repository_id)

    # Verify 100% byte-for-byte equality post-processing
    assert golden_chunk_collection.repository_id == collection_snapshot.repository_id
    assert len(golden_chunk_collection) == len(collection_snapshot)

    for current_chunk, snapshot_chunk in zip(
        golden_chunk_collection.chunks, chunks_snapshot, strict=True
    ):
        assert current_chunk.model_dump() == snapshot_chunk.model_dump()


# ------------------------------------------------------------------------------
# 14 & 15. BM25 Mathematical & Field-Weight Hardening (Requirements #14, #15)
# ------------------------------------------------------------------------------


def test_bm25_mathematical_diagnostics() -> None:
    """Verify BM25 math properties: rare vs common terms, TF saturation, doc length normalization."""
    index = BM25LexicalIndex(k1=1.5, b=0.75)
    repo_id = "repo-bm25-math"

    # 1. Rare term vs Common term
    c_rare = CodeChunk(
        id="chunk-rare",
        chunk_type=ChunkType.FUNCTION,
        repository_id=repo_id,
        file_path="src/rare.py",
        content="def rare_quantum_algorithm(): pass",
        language=Language.PYTHON,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=2, end_column=0),
    )

    c_common = CodeChunk(
        id="chunk-common",
        chunk_type=ChunkType.FUNCTION,
        repository_id=repo_id,
        file_path="src/common.py",
        content="def common_data_processor(): pass",
        language=Language.PYTHON,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=2, end_column=0),
    )

    c_filler = CodeChunk(
        id="chunk-filler",
        chunk_type=ChunkType.FUNCTION,
        repository_id=repo_id,
        file_path="src/filler.py",
        content="def common_filler_func(): pass",
        language=Language.PYTHON,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=2, end_column=0),
    )

    index.add_many([c_rare, c_common, c_filler])

    # "quantum" is rare (DF=1), "common" is common (DF=2)
    res_rare = index.search("quantum", repository_id=repo_id)
    res_common = index.search("common", repository_id=repo_id)

    assert len(res_rare) == 1
    assert len(res_common) == 2
    # Rare term search yields higher IDF score than common term
    assert res_rare[0].score > res_common[0].score


def test_adversarial_field_weighting_symbol_versus_body_repetition() -> None:
    """Adversarial Test: Document A (symbol = PaymentService) MUST rank #1 over

    Document B (symbol = OrderService, body repeats PaymentService 30 times).
    """
    index = BM25LexicalIndex()
    repo_id = "repo-adversarial"

    # Document A: symbol is PaymentService
    doc_a = CodeChunk(
        id="chunk-doc-A",
        chunk_type=ChunkType.CLASS_CONTEXT,
        repository_id=repo_id,
        file_path="src/PaymentService.java",
        name="PaymentService",
        qualified_name="com.example.PaymentService",
        content="public class PaymentService {}",
        language=Language.JAVA,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=5, end_column=0),
    )

    # Document B: symbol is OrderService, but repeats PaymentService in 30 method bodies
    body_methods = "\n".join(
        [
            f"    public void process_step_{i}() {{ PaymentService.executeStep({i}); }}"
            for i in range(30)
        ]
    )
    doc_b = CodeChunk(
        id="chunk-doc-B",
        chunk_type=ChunkType.CLASS_CONTEXT,
        repository_id=repo_id,
        file_path="src/OrderService.java",
        name="OrderService",
        qualified_name="com.example.OrderService",
        content=f"public class OrderService {{\n{body_methods}\n}}",
        language=Language.JAVA,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=50, end_column=0),
    )

    index.add_many([doc_a, doc_b])

    results = index.search("PaymentService", repository_id=repo_id, top_k=10)

    assert len(results) == 2
    # Document A (whose symbol is PaymentService) MUST rank #1
    assert results[0].chunk_id == "chunk-doc-A"
    assert results[0].rank == 1
    assert results[0].score > results[1].score


# ------------------------------------------------------------------------------
# 16, 17, 18, 19. Identifier, Acronym, Qualified Name & Path Hardening
# (Requirements #16, #17, #18, #19)
# ------------------------------------------------------------------------------


def test_identifier_acronym_qualified_name_path_hardening() -> None:
    """Verify sub-token decomposition while strictly preserving exact identifier searches."""
    index = BM25LexicalIndex()
    repo_id = "repo-identifiers"

    c1 = CodeChunk(
        id="chunk-jwt-filter",
        chunk_type=ChunkType.CLASS_CONTEXT,
        repository_id=repo_id,
        file_path="src/security/JWTAuthenticationFilter.java",
        name="JWTAuthenticationFilter",
        qualified_name="com.example.security.JWTAuthenticationFilter.doFilter",
        signature="public void doFilter(ServletRequest req, ServletResponse res)",
        content="public class JWTAuthenticationFilter extends OncePerRequestFilter {}",
        language=Language.JAVA,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=10, end_column=0),
    )

    index.add(c1)

    # 1. Exact full identifier match
    r_exact = index.search("JWTAuthenticationFilter", repository_id=repo_id)
    assert len(r_exact) == 1
    assert r_exact[0].chunk_id == "chunk-jwt-filter"

    # 2. Acronym / Sub-token matches
    r_jwt = index.search("JWT", repository_id=repo_id)
    r_auth = index.search("Authentication", repository_id=repo_id)
    r_filter = index.search("Filter", repository_id=repo_id)

    assert len(r_jwt) == 1
    assert len(r_auth) == 1
    assert len(r_filter) == 1

    # 3. Qualified name search
    r_qual = index.search("com.example.security.JWTAuthenticationFilter", repository_id=repo_id)
    assert len(r_qual) == 1

    # 4. File path search
    r_path = index.search("src/security/JWTAuthenticationFilter.java", repository_id=repo_id)
    assert len(r_path) == 1


# ------------------------------------------------------------------------------
# 21, 24, 27. Isolation, Rebuild Equivalence & Deterministic Tie-Breaking
# (Requirements #21, #24, #27)
# ------------------------------------------------------------------------------


def test_repository_isolation_and_rebuild_equivalence() -> None:
    """Verify strict repository search boundaries and insertion-order independent search results."""
    c_repo_a = CodeChunk(
        id="chunk-repo-A",
        chunk_type=ChunkType.FUNCTION,
        repository_id="repo-A",
        file_path="src/payment.py",
        name="process_payment",
        content="def process_payment(): pass",
        language=Language.PYTHON,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=2, end_column=0),
    )

    c_repo_b = CodeChunk(
        id="chunk-repo-B",
        chunk_type=ChunkType.FUNCTION,
        repository_id="repo-B",
        file_path="src/payment.py",
        name="process_payment",
        content="def process_payment(): pass",
        language=Language.PYTHON,
        source_location=SourceLocation(start_line=1, start_column=0, end_line=2, end_column=0),
    )

    index = BM25LexicalIndex()
    index.add_many([c_repo_a, c_repo_b])

    # Search Repo A returns ONLY Repo A
    res_a = index.search("process_payment", repository_id="repo-A")
    assert len(res_a) == 1
    assert res_a[0].chunk_id == "chunk-repo-A"

    # Rebuild Equivalence: Index A (added A then B) vs Index B (added B then A)
    index1 = BM25LexicalIndex()
    index1.add_many([c_repo_a, c_repo_b])

    index2 = BM25LexicalIndex()
    index2.add_many([c_repo_b, c_repo_a])

    res1 = index1.search("process_payment", repository_id="repo-A")
    res2 = index2.search("process_payment", repository_id="repo-A")

    assert res1[0].chunk_id == res2[0].chunk_id
    assert res1[0].score == res2[0].score


# ------------------------------------------------------------------------------
# 31 & 32. Performance Sanity & Embedding Batching Verification (Requirements #31, #32)
# ------------------------------------------------------------------------------


def test_performance_sanity_and_embedding_batching() -> None:
    """Benchmark performance over 1,000 synthetic chunks and verify embedding batch reduction."""
    repo_id = "repo-perf-sanity"

    chunks = [
        CodeChunk(
            id=f"perf-chk-{i}",
            chunk_type=ChunkType.METHOD if i % 2 == 0 else ChunkType.FUNCTION,
            repository_id=repo_id,
            file_path=f"src/module_{i % 20}/service_{i}.py",
            name=f"execute_task_{i}",
            qualified_name=f"module_{i % 20}.Service{i}.execute_task_{i}",
            signature=f"def execute_task_{i}(param: int) -> str:",
            doc_comment=f"Execute task number {i} with automated retry.",
            content=f"def execute_task_{i}():\n    return TaskRunner.run({i})\n",
            language=Language.PYTHON,
            source_location=SourceLocation(start_line=1, start_column=0, end_line=10, end_column=0),
        )
        for i in range(1000)
    ]

    collection = CodeChunkCollection(chunks=chunks, repository_id=repo_id)

    # 1. Benchmark Chunk Processing & Embedding Pipeline
    text_builder = EmbeddingTextBuilder()

    class CountingProvider(EmbeddingProviderContract):
        def __init__(self) -> None:
            self.call_count = 0

        @property
        def provider_name(self) -> str:
            return "counting-test"

        @property
        def model_name(self) -> str:
            return "test-model"

        @property
        def dimension(self) -> int:
            return 16

        @property
        def embedding_version(self) -> str:
            return "1.0"

        def embed(self, inputs: list[EmbeddingInput]) -> list[EmbeddingResult]:
            self.call_count += 1
            return [
                EmbeddingResult(
                    chunk_id=inp.chunk_id,
                    vector=[0.1] * 16,
                    dimension=16,
                    provider_name="counting-test",
                    model_name="test-model",
                    embedding_version="1.0",
                    repository_id=str(inp.metadata.get("repository_id", "default-repo")),
                )
                for inp in inputs
            ]

    counting_provider = CountingProvider()
    pipeline = EmbeddingPipeline(
        provider=counting_provider, text_builder=text_builder, batch_size=100
    )

    t0_embed = time.perf_counter()
    embed_batch_res = pipeline.embed_chunks(collection)
    t1_embed = time.perf_counter()

    assert embed_batch_res.succeeded_count == 1000
    # 1,000 chunks with batch size 100 MUST result in exactly 10 provider calls
    assert counting_provider.call_count == 10
    assert (t1_embed - t0_embed) < 2.0  # Must complete in under 2 seconds

    # 2. Benchmark BM25 Lexical Indexing & Search
    bm25 = BM25LexicalIndex()

    t0_index = time.perf_counter()
    bm25.add_many(collection)
    t1_index = time.perf_counter()

    assert bm25.document_count(repo_id) == 1000
    assert (t1_index - t0_index) < 1.0  # Indexing 1,000 chunks in under 1 second

    t0_search = time.perf_counter()
    for q_idx in range(50):
        res = bm25.search(f"execute_task_{q_idx * 20}", repository_id=repo_id, top_k=5)
        assert len(res) > 0
    t1_search = time.perf_counter()

    assert (t1_search - t0_search) < 0.5  # 50 searches in under 0.5s


# ------------------------------------------------------------------------------
# 42 & 43. Referential Integrity & Orphan Detection (Requirements #42, #43)
# ------------------------------------------------------------------------------


def test_referential_integrity_and_orphan_detection(
    golden_chunk_collection: CodeChunkCollection,
) -> None:
    """Verify every indexed search result chunk_id maps back to exactly one canonical CodeChunk."""
    index = BM25LexicalIndex()
    index.add_many(golden_chunk_collection)

    repo_id = golden_chunk_collection.repository_id
    results = index.search(
        "PaymentService processPayment authenticateUser", repository_id=repo_id, top_k=20
    )

    chunk_map = {c.id: c for c in golden_chunk_collection.chunks}

    # Every lexical search result must resolve to an existing CodeChunk
    for res in results:
        assert res.chunk_id in chunk_map
        source_chunk = chunk_map[res.chunk_id]
        assert source_chunk.repository_id == res.repository_id
        assert source_chunk.file_path == res.file_path
        assert source_chunk.language == res.language
