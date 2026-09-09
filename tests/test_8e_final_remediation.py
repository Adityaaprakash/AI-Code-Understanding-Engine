"""Phase 8E Final Remediation Tests."""

from unittest.mock import Mock

import pytest

from code_analyzer.ir import SourceLocation
from code_analyzer.parsers.models import Language
from retrieval.enums import ChunkType
from retrieval.lexical_index import BM25LexicalIndex
from retrieval.models import CodeChunk
from retrieval.partial_reindexer import PartialReindexer, PartialReindexPlan
from retrieval.vector_index import VectorIndex


@pytest.fixture
def provider_mock():
    m = Mock()
    m.provider_name = "test"
    m.model_name = "test"
    m.embedding_version = "1"
    m.dimension = 2
    # mock embed returns empty for ease
    m.embed.return_value = []
    return m


@pytest.mark.asyncio
async def test_active_version_must_remain_intact(provider_mock):
    lexical = BM25LexicalIndex()
    vector = VectorIndex()

    docA = CodeChunk(
        id="chunk_x",
        repository_id="repo1",
        file_path="f",
        name="old",
        qualified_name="old",
        chunk_type=ChunkType.FILE_CONTEXT,
        language=Language.PYTHON,
        commit_sha="commit_A",
        source_location=SourceLocation(start_line=1, end_line=5, start_column=1, end_column=10),
        metadata={"tokens": ["old_marker"]},
    )
    lexical.add(docA)

    from retrieval.embedding_models import EmbeddingResult

    vector.add(
        EmbeddingResult(
            chunk_id="chunk_x",
            vector=[0.1, 0.2],
            dimension=2,
            provider_name="test",
            model_name="test",
            embedding_version="1",
            repository_id="repo1",
            commit_sha="commit_A",
        ),
        chunk=docA,
    )

    # Verify A has OLD_MARKER
    res_a = lexical.search("old", repository_id="repo1", commit_sha="commit_A")
    assert len(res_a) == 1

    # Begin applying B's partial reindex (which modifies chunk_x)
    docB = CodeChunk(
        id="chunk_y",
        repository_id="repo1",
        file_path="PaymentService.java",
        name="processPayment",
        qualified_name="PaymentService.processPayment",
        chunk_type=ChunkType.METHOD,
        language=Language.JAVA,
        commit_sha="commit_B",
        source_location=SourceLocation(start_line=1, end_line=5, start_column=1, end_column=10),
        content="new_marker",
    )

    plan = PartialReindexPlan(
        repository_id="repo1",
        base_commit="commit_A",
        target_commit="commit_B",
        chunks_to_add=[docB],
        chunks_to_remove=["chunk_x"],
        chunks_to_embed=[],
        embeddings_to_reuse=[],
    )

    reindexer = PartialReindexer(
        lexical_index=lexical, vector_index=vector, embedding_provider=provider_mock
    )
    reindexer.execute(plan)

    # B is BUILDING (execute finished). But BEFORE B becomes ACTIVE:
    # Query active version A
    res_a_after = lexical.search("old", repository_id="repo1", commit_sha="commit_A")
    assert len(res_a_after) == 1
    assert res_a_after[0].chunk_id == "chunk_x"

    # Query B (should have new marker, no old marker)
    res_b_old = lexical.search("old", repository_id="repo1", commit_sha="commit_B")
    assert len(res_b_old) == 0

    res_b_new = lexical.search("new_marker", repository_id="repo1", commit_sha="commit_B")
    assert len(res_b_new) == 1
    assert res_b_new[0].chunk_id == "chunk_y"


@pytest.mark.asyncio
async def test_deleted_data(provider_mock):
    lexical = BM25LexicalIndex()
    vector = VectorIndex()

    docA = CodeChunk(
        id="chunk_del",
        repository_id="repo1",
        file_path="f",
        name="oldpaymentservice",
        qualified_name="old",
        chunk_type=ChunkType.FILE_CONTEXT,
        language=Language.PYTHON,
        commit_sha="commit_A",
        source_location=SourceLocation(start_line=1, end_line=5, start_column=1, end_column=10),
        content="oldpaymentservice",
    )
    lexical.add(docA)

    plan = PartialReindexPlan(
        repository_id="repo1",
        base_commit="commit_A",
        target_commit="commit_B",
        chunks_to_add=[],
        chunks_to_remove=["chunk_del"],
        chunks_to_embed=[],
        embeddings_to_reuse=[],
    )

    reindexer = PartialReindexer(
        lexical_index=lexical, vector_index=vector, embedding_provider=provider_mock
    )
    reindexer.execute(plan)

    assert (
        len(lexical.search("oldpaymentservice", repository_id="repo1", commit_sha="commit_A")) == 1
    )
    assert (
        len(lexical.search("oldpaymentservice", repository_id="repo1", commit_sha="commit_B")) == 0
    )


@pytest.mark.asyncio
async def test_new_data(provider_mock):
    lexical = BM25LexicalIndex()
    vector = VectorIndex()

    docB = CodeChunk(
        id="chunk_new",
        repository_id="repo1",
        file_path="f",
        name="new_marker",
        qualified_name="new",
        chunk_type=ChunkType.FILE_CONTEXT,
        language=Language.PYTHON,
        commit_sha="commit_B",
        source_location=SourceLocation(start_line=1, end_line=5, start_column=1, end_column=10),
        content="new_marker",
    )
    plan = PartialReindexPlan(
        repository_id="repo1",
        base_commit="commit_A",
        target_commit="commit_B",
        chunks_to_add=[docB],
        chunks_to_remove=[],
        chunks_to_embed=[],
        embeddings_to_reuse=[],
    )

    reindexer = PartialReindexer(
        lexical_index=lexical, vector_index=vector, embedding_provider=provider_mock
    )
    reindexer.execute(plan)

    assert len(lexical.search("new_marker", repository_id="repo1", commit_sha="commit_A")) == 0
    assert len(lexical.search("new_marker", repository_id="repo1", commit_sha="commit_B")) == 1


@pytest.mark.asyncio
async def test_failure(provider_mock):
    lexical = BM25LexicalIndex()
    vector = VectorIndex()

    docA = CodeChunk(
        id="chunk_del",
        repository_id="repo1",
        file_path="f",
        name="old_marker",
        qualified_name="old",
        chunk_type=ChunkType.FILE_CONTEXT,
        language=Language.PYTHON,
        commit_sha="commit_A",
        source_location=SourceLocation(start_line=1, end_line=5, start_column=1, end_column=10),
        content="old_marker",
    )
    lexical.add(docA)

    # We add chunks_to_embed to force the provider mock to be invoked and trigger the side-effect Exception
    docB = CodeChunk(
        id="chunk_new",
        repository_id="repo1",
        file_path="f",
        name="new_marker",
        qualified_name="new",
        chunk_type=ChunkType.FILE_CONTEXT,
        language=Language.PYTHON,
        commit_sha="commit_B",
        source_location=SourceLocation(start_line=1, end_line=5, start_column=1, end_column=10),
        content="new_marker",
    )

    plan = PartialReindexPlan(
        repository_id="repo1",
        base_commit="commit_A",
        target_commit="commit_B",
        chunks_to_add=[docB],
        chunks_to_remove=["chunk_del"],
        chunks_to_embed=[docB],
        embeddings_to_reuse=[],
    )

    provider_mock.embed.side_effect = Exception("Build failure")
    reindexer = PartialReindexer(
        lexical_index=lexical, vector_index=vector, embedding_provider=provider_mock
    )
    with pytest.raises(Exception, match="Build failure"):
        reindexer.execute(plan)

    # A MUST BE INTACT
    assert len(lexical.search("old_marker", repository_id="repo1", commit_sha="commit_A")) == 1


@pytest.mark.asyncio
async def test_partial_reindex_removal_isolated(provider_mock):
    lexical = BM25LexicalIndex()
    vector = VectorIndex()
    docA = CodeChunk(
        id="chunk_x",
        repository_id="repo1",
        file_path="f",
        name="target",
        qualified_name="target",
        chunk_type=ChunkType.FILE_CONTEXT,
        language=Language.PYTHON,
        commit_sha="commit_A",
        source_location=SourceLocation(start_line=1, end_line=5, start_column=1, end_column=10),
        content="target",
    )
    lexical.add(docA)

    plan = PartialReindexPlan(
        repository_id="repo1",
        base_commit="commit_A",
        target_commit="commit_B",
        chunks_to_add=[],
        chunks_to_remove=["chunk_x"],
        chunks_to_embed=[],
        embeddings_to_reuse=[],
    )

    reindexer = PartialReindexer(
        lexical_index=lexical, vector_index=vector, embedding_provider=provider_mock
    )
    reindexer.execute(plan)

    assert len(lexical.search("target", repository_id="repo1", commit_sha="commit_A")) == 1
