"""Comprehensive test suite for TASK-4B — Chunk Metadata & Indexing Identity."""

import pytest
from pydantic import ValidationError

from code_analyzer.ir import Class, File, Function, Method, SourceLocation
from code_analyzer.normalization import NormalizationResult
from code_analyzer.parsers.models import Language
from retrieval.chunker import CodeChunker
from retrieval.enums import ChunkType
from retrieval.models import CodeChunk


@pytest.fixture
def sample_file_ir() -> File:
    """Fixture providing a base File IR entity."""
    return File(
        id="file_meta_001",
        repository_id="repo_alpha",
        path="src/services/payment_service.py",
        language=Language.PYTHON,
        loc=50,
        location=SourceLocation(
            file_path="src/services/payment_service.py",
            start_line=1,
            start_column=0,
            end_line=50,
            end_column=0,
        ),
    )


@pytest.fixture
def sample_normalization_result(sample_file_ir: File) -> NormalizationResult:
    """Fixture providing a NormalizationResult with Class, Method, and Function."""
    cls_entity = Class(
        id="class_payment_001",
        file_id=sample_file_ir.id,
        name="PaymentService",
        qualified_name="services.payment_service.PaymentService",
        doc_comment="Service handling secure payment transactions.",
        parent_id=sample_file_ir.id,
        location=SourceLocation(
            file_path=sample_file_ir.path,
            start_line=5,
            start_column=0,
            end_line=45,
            end_column=0,
        ),
        method_ids=["method_process_001"],
    )

    method_entity = Method(
        id="method_process_001",
        file_id=sample_file_ir.id,
        name="process_payment",
        qualified_name="services.payment_service.PaymentService.process_payment",
        doc_comment="Process a payment transaction.",
        class_id=cls_entity.id,
        return_type="bool",
        location=SourceLocation(
            file_path=sample_file_ir.path,
            start_line=10,
            start_column=4,
            end_line=25,
            end_column=20,
        ),
    )

    func_entity = Function(
        id="func_validate_001",
        file_id=sample_file_ir.id,
        name="validate_card",
        qualified_name="services.payment_service.validate_card",
        doc_comment="Validate payment card format.",
        parent_id=sample_file_ir.id,
        return_type="bool",
        location=SourceLocation(
            file_path=sample_file_ir.path,
            start_line=47,
            start_column=0,
            end_line=50,
            end_column=0,
        ),
    )

    return NormalizationResult(
        file=sample_file_ir,
        classes=[cls_entity],
        methods=[method_entity],
        functions=[func_entity],
    )


def test_repository_and_commit_identity(sample_normalization_result: NormalizationResult) -> None:
    """Verify repository_id, commit_id, and commit_sha are preserved explicitly in chunks and collections."""
    chunker = CodeChunker()
    commit_id = "commit_uuid_12345"
    commit_sha = "a1b2c3d4e5f67890123456789abcdef012345678"

    collection = chunker.chunk_normalization_result(
        result=sample_normalization_result,
        commit_id=commit_id,
        commit_sha=commit_sha,
    )

    assert collection.repository_id == "repo_alpha"
    assert collection.commit_id == commit_id
    assert collection.commit_sha == commit_sha
    assert len(collection) > 0

    for chunk in collection.chunks:
        assert chunk.repository_id == "repo_alpha"
        assert chunk.commit_id == commit_id
        assert chunk.commit_sha == commit_sha


def test_file_path_normalization() -> None:
    """Verify file paths are normalized to use repository-relative forward slashes."""
    loc = SourceLocation(
        file_path="src\\utils\\formatter.ts",
        start_line=1,
        start_column=0,
        end_line=10,
        end_column=0,
    )
    chunk = CodeChunk(
        id="chunk_norm_01",
        chunk_type=ChunkType.FUNCTION,
        repository_id="repo_beta",
        file_id="file_01",
        file_path="src\\utils\\formatter.ts",
        language=Language.TYPESCRIPT,
        source_location=loc,
    )
    assert chunk.file_path == "src/utils/formatter.ts"


def test_symbol_identity_and_property_aliases(
    sample_normalization_result: NormalizationResult,
) -> None:
    """Verify entity_id/symbol_id and name/symbol_name property aliases work identically."""
    chunker = CodeChunker()
    collection = chunker.chunk_normalization_result(sample_normalization_result)

    method_chunks = [c for c in collection.chunks if c.chunk_type == ChunkType.METHOD]
    assert len(method_chunks) == 1
    method_chunk = method_chunks[0]

    assert method_chunk.entity_id == "method_process_001"
    assert method_chunk.symbol_id == "method_process_001"
    assert method_chunk.name == "process_payment"
    assert method_chunk.symbol_name == "process_payment"
    assert method_chunk.qualified_name == "services.payment_service.PaymentService.process_payment"


def test_parent_hierarchy_linkages(sample_normalization_result: NormalizationResult) -> None:
    """Verify parent_entity_id links methods to class and functions to file."""
    chunker = CodeChunker()
    collection = chunker.chunk_normalization_result(sample_normalization_result)

    cls_chunk = next(c for c in collection.chunks if c.chunk_type == ChunkType.CLASS_CONTEXT)
    method_chunk = next(c for c in collection.chunks if c.chunk_type == ChunkType.METHOD)
    func_chunk = next(c for c in collection.chunks if c.chunk_type == ChunkType.FUNCTION)

    assert cls_chunk.parent_entity_id == "file_meta_001"
    assert method_chunk.parent_entity_id == "class_payment_001"
    assert func_chunk.parent_entity_id == "file_meta_001"


def test_oversized_sub_chunk_metadata_linkage() -> None:
    """Verify oversized sub-chunks maintain parent chunk identity and correct sub_chunk_index."""
    file_entity = File(
        id="file_large_01",
        repository_id="repo_gamma",
        path="src/LargeClass.java",
        language=Language.JAVA,
        loc=400,
        location=SourceLocation(
            file_path="src/LargeClass.java",
            start_line=1,
            start_column=0,
            end_line=400,
            end_column=0,
        ),
    )
    cls_entity = Class(
        id="class_large_01",
        file_id=file_entity.id,
        name="LargeClass",
        qualified_name="com.example.LargeClass",
        parent_id=file_entity.id,
        location=SourceLocation(
            file_path="src/LargeClass.java",
            start_line=1,
            start_column=0,
            end_line=400,
            end_column=0,
        ),
    )
    norm_res = NormalizationResult(file=file_entity, classes=[cls_entity])
    chunker = CodeChunker()

    collection = chunker.chunk_normalization_result(norm_res, max_lines_per_chunk=150)
    cls_chunks = [c for c in collection.chunks if c.entity_id == "class_large_01"]

    assert len(cls_chunks) == 3  # Header (0), Sub1 (1), Sub2 (2)
    header_chunk = cls_chunks[0]
    sub1_chunk = cls_chunks[1]
    sub2_chunk = cls_chunks[2]

    assert header_chunk.chunk_type == ChunkType.CLASS_CONTEXT
    assert header_chunk.sub_chunk_index == 0
    assert header_chunk.total_sub_chunks == 3
    assert header_chunk.parent_chunk_id is None

    assert sub1_chunk.chunk_type == ChunkType.SUB_CHUNK
    assert sub1_chunk.sub_chunk_index == 1
    assert sub1_chunk.total_sub_chunks == 3
    assert sub1_chunk.parent_chunk_id == header_chunk.id
    assert sub1_chunk.parent_entity_id == "class_large_01"

    assert sub2_chunk.chunk_type == ChunkType.SUB_CHUNK
    assert sub2_chunk.sub_chunk_index == 2
    assert sub2_chunk.total_sub_chunks == 3
    assert sub2_chunk.parent_chunk_id == header_chunk.id


def test_optional_metadata_handling_without_placeholders() -> None:
    """Verify absent metadata fields remain None rather than injecting fake string placeholders."""
    loc = SourceLocation(
        file_path="main.py", start_line=1, start_column=0, end_line=5, end_column=0
    )
    chunk = CodeChunk(
        id="chunk_opt_01",
        chunk_type=ChunkType.FILE_CONTEXT,
        repository_id="repo_delta",
        file_id="file_main",
        file_path="main.py",
        language=Language.PYTHON,
        source_location=loc,
    )

    assert chunk.entity_id is None
    assert chunk.parent_entity_id is None
    assert chunk.parent_chunk_id is None
    assert chunk.commit_id is None
    assert chunk.commit_sha is None
    assert chunk.doc_comment is None
    assert chunk.signature is None


def test_validation_empty_identity_strings() -> None:
    """Verify validation errors when id, repository_id, or file_id are empty."""
    loc = SourceLocation(file_path="a.py", start_line=1, start_column=0, end_line=5, end_column=0)
    with pytest.raises(ValidationError):
        CodeChunk(
            id="   ",
            chunk_type=ChunkType.FUNCTION,
            repository_id="repo1",
            file_id="f1",
            file_path="a.py",
            language=Language.PYTHON,
            source_location=loc,
        )

    with pytest.raises(ValidationError):
        CodeChunk(
            id="c1",
            chunk_type=ChunkType.FUNCTION,
            repository_id="",
            file_id="f1",
            file_path="a.py",
            language=Language.PYTHON,
            source_location=loc,
        )


def test_validation_invalid_source_location() -> None:
    """Verify validation error when end_line < start_line in CodeChunk."""
    bad_loc = SourceLocation.model_construct(
        file_path="a.py", start_line=10, start_column=0, end_line=5, end_column=0
    )
    with pytest.raises(ValidationError):
        CodeChunk(
            id="c1",
            chunk_type=ChunkType.FUNCTION,
            repository_id="repo1",
            file_id="f1",
            file_path="a.py",
            language=Language.PYTHON,
            source_location=bad_loc,
        )


def test_validation_sub_chunk_index_bounds() -> None:
    """Verify validation error when sub_chunk_index >= total_sub_chunks or negative."""
    loc = SourceLocation(file_path="a.py", start_line=1, start_column=0, end_line=5, end_column=0)
    with pytest.raises(ValidationError):
        CodeChunk(
            id="c1",
            chunk_type=ChunkType.FUNCTION,
            repository_id="repo1",
            file_id="f1",
            file_path="a.py",
            language=Language.PYTHON,
            source_location=loc,
            sub_chunk_index=2,
            total_sub_chunks=2,
        )


def test_immutability_and_determinism(sample_normalization_result: NormalizationResult) -> None:
    """Verify frozen model immutability and deterministic JSON serialization."""
    chunker = CodeChunker()
    coll1 = chunker.chunk_normalization_result(
        sample_normalization_result, commit_sha="abc123456789"
    )
    coll2 = chunker.chunk_normalization_result(
        sample_normalization_result, commit_sha="abc123456789"
    )

    # Immutability check
    chunk = coll1.chunks[0]
    with pytest.raises(ValidationError):
        chunk.content = "mutated content"

    # Determinism check
    json1 = coll1.model_dump_json()
    json2 = coll2.model_dump_json()
    assert json1 == json2


def test_index_consumer_readiness_to_index_dict(
    sample_normalization_result: NormalizationResult,
) -> None:
    """Verify to_index_dict provides complete metadata payload for Phase 4C (Embeddings) & 4D (BM25)."""
    chunker = CodeChunker()
    coll = chunker.chunk_normalization_result(
        sample_normalization_result,
        source_code="class PaymentService:\n    def process_payment(self):\n        return True\n",
        commit_id="commit_uuid_99",
        commit_sha="fedcba9876543210123456789abcdef012345678",
    )

    method_chunk = next(c for c in coll.chunks if c.chunk_type == ChunkType.METHOD)
    index_dict = method_chunk.to_index_dict()

    # Index consumer contract requirements verification
    assert index_dict["chunk_id"] == method_chunk.id
    assert index_dict["chunk_type"] == "method"
    assert index_dict["repository_id"] == "repo_alpha"
    assert index_dict["commit_id"] == "commit_uuid_99"
    assert index_dict["commit_sha"] == "fedcba9876543210123456789abcdef012345678"
    assert index_dict["file_id"] == "file_meta_001"
    assert index_dict["file_path"] == "src/services/payment_service.py"
    assert index_dict["language"] == "python"
    assert index_dict["entity_id"] == "method_process_001"
    assert index_dict["symbol_id"] == "method_process_001"
    assert index_dict["symbol_name"] == "process_payment"
    assert index_dict["qualified_name"] == "services.payment_service.PaymentService.process_payment"
    assert index_dict["parent_entity_id"] == "class_payment_001"
    assert index_dict["start_line"] == 10
    assert index_dict["end_line"] == 25
    assert index_dict["start_column"] == 4
    assert index_dict["end_column"] == 20
    assert "def process_payment" in index_dict["signature"]
    assert "Process a payment transaction." in index_dict["doc_comment"]
