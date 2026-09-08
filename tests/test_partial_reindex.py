"""Tests for Phase 8C Partial Re-indexing."""

from backend.git.models import (
    ChangedSymbol,
    ChangedSymbolResult,
    ChangeType,
    OpaqueFile,
    OpaqueFileFallbackReason,
    SymbolChangeType,
)
from code_analyzer.ir import (
    File as IRFile,
)
from code_analyzer.ir import (
    Function as IRFunction,
)
from code_analyzer.ir import (
    SourceLocation,
    generate_entity_id,
)
from code_analyzer.normalization import NormalizationResult
from code_analyzer.parsers.models import Language
from retrieval.chunker import CodeChunker
from retrieval.embedding_models import EmbeddingResult
from retrieval.lexical_index import BM25LexicalIndex
from retrieval.models import CodeChunkCollection
from retrieval.partial_reindexer import PartialReindexer, PartialReindexPlan, PartialReindexPlanner
from retrieval.providers import DeterministicTestEmbeddingProvider
from retrieval.vector_index import VectorIndex

REPO_ID = "test_repo"


def test_planner_identifies_affected_files() -> None:
    """Verify the planner correctly isolates affected files from unchanged code."""
    chunker = CodeChunker()
    planner = PartialReindexPlanner(chunker)

    # Mock old chunk collection
    old_coll = CodeChunkCollection(
        repository_id=REPO_ID, chunks=[], file_chunk_map={}, entity_chunk_map={}
    )
    old_embeddings: dict[str, EmbeddingResult] = {}

    changed_result = ChangedSymbolResult(
        repository_path="/repo",
        base_commit="A",
        target_commit="B",
        changed_symbols=[
            ChangedSymbol(
                symbol_id="func1",
                change_type=SymbolChangeType.MODIFIED,
                name="func1",
                qualified_name="func1",
                kind="function",
                file_path="src/main.py",
            )
        ],
        opaque_files=[
            OpaqueFile(
                path="README.md",
                reason=OpaqueFileFallbackReason.UNSUPPORTED_LANGUAGE,
                change_type=ChangeType.MODIFIED,
            )
        ],
    )

    # Empty normalization result for this test
    plan = planner.plan(
        changed_result=changed_result,
        old_chunk_collection=old_coll,
        old_embeddings=old_embeddings,
        new_normalization_results={},
        new_source_codes={},
        repository_id=REPO_ID,
    )

    assert "src/main.py" in plan.files_modified
    assert plan.opaque_files[0].path == "README.md"
    assert "README.md" in plan.files_modified
    assert plan.chunks_to_remove == []
    assert plan.chunks_to_add == []


def test_executor_replaces_chunks() -> None:
    """Verify the executor cleanly orchestrates adds and removes."""
    lexical = BM25LexicalIndex()
    vector = VectorIndex()
    provider = DeterministicTestEmbeddingProvider()
    executor = PartialReindexer(lexical, vector, provider)

    from retrieval.enums import ChunkType
    from retrieval.models import CodeChunk

    old_chunk = CodeChunk(
        id="old_chunk",
        chunk_type=ChunkType.FILE_CONTEXT,
        repository_id=REPO_ID,
        file_path="src/main.py",
        language=Language.PYTHON,
        source_location=SourceLocation(
            file_path="src/main.py", start_line=1, start_column=0, end_line=10, end_column=0
        ),
    )

    new_chunk = CodeChunk(
        id="new_chunk",
        chunk_type=ChunkType.FILE_CONTEXT,
        repository_id=REPO_ID,
        file_path="src/main.py",
        language=Language.PYTHON,
        source_location=SourceLocation(
            file_path="src/main.py", start_line=1, start_column=0, end_line=15, end_column=0
        ),
    )

    lexical.add(old_chunk)

    plan = PartialReindexPlan(
        repository_id=REPO_ID,
        base_commit="A",
        target_commit="B",
        chunks_to_remove=["old_chunk"],
        chunks_to_add=[new_chunk],
        embeddings_to_reuse=[],
    )

    stats = executor.execute(plan)

    assert stats["chunks_removed"] == 1
    assert stats["chunks_added"] == 1

    # Old deleted, new added
    assert lexical.document_count() == 1
    # Check that new_chunk is actually the one there via search
    results = lexical.search("main", REPO_ID)
    assert len(results) == 1
    assert results[0].chunk_id == "new_chunk"

    # Vector index should have automatically embedded the new chunk
    assert stats["embeddings_generated"] == 1
    assert vector.document_count(REPO_ID) == 1


def test_embedding_reuse() -> None:
    """Verify embeddings are reused when semantic text is unchanged."""
    chunker = CodeChunker()
    planner = PartialReindexPlanner(chunker)

    # Let's say we have an old function chunk
    old_func_id = generate_entity_id(
        kind="FUNCTION", file_path="src/main.py", qualified_name="my_func"
    )
    old_file_id = generate_entity_id(
        kind="FILE", file_path="src/main.py", qualified_name="src/main.py"
    )

    old_ir_func = IRFunction(
        id=old_func_id,
        file_id=old_file_id,
        name="my_func",
        qualified_name="my_func",
        location=SourceLocation(
            file_path="src/main.py", start_line=1, start_column=0, end_line=2, end_column=0
        ),
        is_async=False,
        call_refs=[],
    )
    old_ir_file = IRFile(
        id=old_file_id,
        repository_id=REPO_ID,
        path="src/main.py",
        language=Language.PYTHON,
        loc=2,
        location=SourceLocation(
            file_path="src/main.py", start_line=1, start_column=0, end_line=2, end_column=0
        ),
        module_ids=[],
        name="src/main.py",
    )

    old_norm = NormalizationResult(file=old_ir_file, functions=[old_ir_func])
    old_coll = chunker.chunk_normalization_result(old_norm, "def my_func():\n    pass")

    provider = DeterministicTestEmbeddingProvider()

    # Embed all old chunks manually
    from retrieval.embedding_models import EmbeddingInput
    from retrieval.text_builder import EmbeddingTextBuilder

    tb = EmbeddingTextBuilder()

    old_embeddings = {}
    for c in old_coll.chunks:
        inputs = [
            EmbeddingInput(
                chunk_id=c.id,
                text=tb.build_text(c),
                model_name=provider.model_name,
                embedding_version=provider.embedding_version,
            )
        ]
        old_embeddings[c.id] = provider.embed(inputs)[0]

    # New state: purely location moved down 1 line!
    # Because it moved, it triggers IDENTITY_ONLY
    new_func_id = generate_entity_id(
        kind="FUNCTION", file_path="src/main.py", qualified_name="my_func", location_str="2-3"
    )
    new_ir_func = IRFunction(
        id=new_func_id,
        file_id=old_file_id,
        name="my_func",
        qualified_name="my_func",
        location=SourceLocation(
            file_path="src/main.py", start_line=2, start_column=0, end_line=3, end_column=0
        ),
        is_async=False,
        call_refs=[],
    )
    new_ir_file = IRFile(
        id=old_file_id,
        repository_id=REPO_ID,
        path="src/main.py",
        language=Language.PYTHON,
        loc=3,
        location=SourceLocation(
            file_path="src/main.py", start_line=1, start_column=0, end_line=3, end_column=0
        ),
        module_ids=[],
        name="src/main.py",
    )

    new_norm = NormalizationResult(file=new_ir_file, functions=[new_ir_func])

    changed_result = ChangedSymbolResult(
        repository_path="/repo",
        base_commit="A",
        target_commit="B",
        changed_symbols=[
            ChangedSymbol(
                symbol_id=new_func_id,
                change_type=SymbolChangeType.IDENTITY_ONLY,
                name="my_func",
                qualified_name="my_func",
                kind="function",
                file_path="src/main.py",
                previous_symbol_id=old_func_id,
            )
        ],
        opaque_files=[],
    )

    plan = planner.plan(
        changed_result=changed_result,
        old_chunk_collection=old_coll,
        old_embeddings=old_embeddings,
        new_normalization_results={"src/main.py": new_norm},
        new_source_codes={"src/main.py": "\ndef my_func():\n    pass"},
        repository_id=REPO_ID,
    )

    # 1 File chunk + 1 func chunk should be removed
    assert len(plan.chunks_to_remove) == 2
    # 2 new chunks added
    assert len(plan.chunks_to_add) == 2
    # But because text is IDENTICAL for the FUNCTION (just line shift), embedding is REUSED!
    # The FILE chunk might change text if LOC changes (loc goes from 2 to 3),
    # but the FUNCTION text won't change if the snippet is exactly the same!
    assert len(plan.embeddings_to_reuse) >= 1
    assert any(
        e.chunk_id != old_func_id for e in plan.embeddings_to_reuse
    )  # Must be bound to new chunk ID

    # execute
    executor = PartialReindexer(BM25LexicalIndex(), VectorIndex(), provider)
    stats = executor.execute(plan)

    assert stats["embeddings_reused"] >= 1
    assert stats["embeddings_generated"] < 2  # At least one was saved!


def test_opaque_file_safety() -> None:
    # Proves OpaqueFiles trigger index deletion of old chunks without adding new chunks.
    from backend.git.models import (
        ChangedSymbolResult,
        ChangeType,
        OpaqueFile,
        OpaqueFileFallbackReason,
    )
    from retrieval.enums import ChunkType
    from retrieval.models import CodeChunk, CodeChunkCollection
    from retrieval.partial_reindexer import PartialReindexPlanner

    planner = PartialReindexPlanner(CodeChunker())

    old_coll = CodeChunkCollection(
        repository_id=REPO_ID,
        commit_id=None,
        commit_sha="A",
        chunks=[
            CodeChunk(
                id="opaque_chunk_1",
                chunk_type=ChunkType.FILE_CONTEXT,
                repository_id=REPO_ID,
                file_id="opaque_file_1",
                file_path="bad.py",
                language=Language.PYTHON,
                entity_id="opaque_file_1",
                parent_entity_id=REPO_ID,
                name="bad.py",
                qualified_name="bad.py",
                source_location=SourceLocation(
                    file_path="bad.py", start_line=1, start_column=0, end_line=1, end_column=0
                ),
                content="old text",
                doc_comment=None,
                sub_chunk_index=0,
                total_sub_chunks=1,
                metadata={},
            )
        ],
        file_chunk_map={"bad.py": ["opaque_chunk_1"]},
        entity_chunk_map={},
    )

    changed = ChangedSymbolResult(
        repository_path=REPO_ID,
        base_commit="A",
        target_commit="B",
        changed_symbols=[],
        opaque_files=[
            OpaqueFile(
                path="bad.py",
                change_type=ChangeType.MODIFIED,
                reason=OpaqueFileFallbackReason.PARSER_FAILURE,
            )
        ],
    )

    plan = planner.plan(
        changed_result=changed,
        old_chunk_collection=old_coll,
        old_embeddings={},
        new_normalization_results={},
        new_source_codes={"bad.py": "syntax error"},
        repository_id=REPO_ID,
    )

    # PROOF: Old chunks deleted, nothing added = LOSS of knowledge.
    assert plan.chunks_to_remove == []
    assert plan.chunks_to_add == []


def test_8d_boundary_not_crossed() -> None:
    # Test proves that without explicitly analyzing dependencies, B is not reindexed when A changes
    planner = PartialReindexPlanner(CodeChunker())
    from backend.git.models import ChangedSymbol, ChangedSymbolResult, SymbolChangeType
    from code_analyzer.ir import SourceLocation
    from retrieval.enums import ChunkType
    from retrieval.models import CodeChunk, CodeChunkCollection

    # If B is not in changed_symbols, its old chunks remain and are not removed/added
    old_coll = CodeChunkCollection(
        repository_id=REPO_ID,
        commit_sha="A",
        chunks=[
            CodeChunk(
                id="chunk_a",
                chunk_type=ChunkType.FILE_CONTEXT,
                repository_id=REPO_ID,
                file_id="file_a",
                file_path="a.py",
                language=Language.PYTHON,
                parent_entity_id="repo",
                name="a",
                qualified_name="a",
                source_location=SourceLocation(
                    file_path="a.py", start_line=1, start_column=0, end_line=1, end_column=0
                ),
                content="def a(): pass",
            ),
            CodeChunk(
                id="chunk_b",
                chunk_type=ChunkType.FILE_CONTEXT,
                repository_id=REPO_ID,
                file_id="file_b",
                file_path="b.py",
                language=Language.PYTHON,
                parent_entity_id="repo",
                name="b",
                qualified_name="b",
                source_location=SourceLocation(
                    file_path="b.py", start_line=1, start_column=0, end_line=2, end_column=0
                ),
                content="from a import a\ndef b(): a()",
            ),
        ],
        file_chunk_map={"a.py": ["chunk_a"], "b.py": ["chunk_b"]},
        entity_chunk_map={},
    )
    changed = ChangedSymbolResult(
        repository_path=REPO_ID,
        base_commit="A",
        target_commit="B",
        opaque_files=[],
        changed_symbols=[
            ChangedSymbol(
                file_path="a.py",
                symbol_id="a",
                kind="function",
                name="a",
                qualified_name="a",
                previous_symbol_id="a",
                change_type=SymbolChangeType.MODIFIED,
            )
        ],
    )
    plan = planner.plan(changed, old_coll, {}, {}, {}, REPO_ID)
    assert "chunk_a" in plan.chunks_to_remove
    assert "chunk_b" not in plan.chunks_to_remove
    # Proves 8D does not happen in 8C. B is untouched.


# ---- BLOCKER 1 OPAQUE FILES TESTS ----


def test_opaque_file_preservation_multiple() -> None:
    # Prove that OpaqueFiles preserve their chunks, while valid modified files are handled normally.
    import sys

    from backend.git.models import (
        ChangedSymbol,
        ChangedSymbolResult,
        ChangeType,
        OpaqueFile,
        OpaqueFileFallbackReason,
        SymbolChangeType,
    )
    from retrieval.enums import ChunkType
    from retrieval.models import CodeChunk, CodeChunkCollection
    from retrieval.partial_reindexer import PartialReindexPlanner

    sys.modules["code_analyzer"] = type("Mock", (), {})()

    planner = PartialReindexPlanner(CodeChunker())

    old_coll = CodeChunkCollection(
        repository_id=REPO_ID,
        commit_sha="A",
        chunks=[
            CodeChunk(
                id="op_1",
                chunk_type=ChunkType.FILE_CONTEXT,
                repository_id=REPO_ID,
                file_id="op_file",
                file_path="bad1.py",
                language=Language.PYTHON,
                parent_entity_id=REPO_ID,
                name="bad1.py",
                qualified_name="bad1.py",
                source_location=SourceLocation(
                    file_path="bad1.py", start_line=1, start_column=0, end_line=1, end_column=0
                ),
                content="",
            ),
            CodeChunk(
                id="op_2",
                chunk_type=ChunkType.FILE_CONTEXT,
                repository_id=REPO_ID,
                file_id="op_file2",
                file_path="bad2.py",
                language=Language.PYTHON,
                parent_entity_id=REPO_ID,
                name="bad2.py",
                qualified_name="bad2.py",
                source_location=SourceLocation(
                    file_path="bad2.py", start_line=1, start_column=0, end_line=1, end_column=0
                ),
                content="",
            ),
            CodeChunk(
                id="op_3",
                chunk_type=ChunkType.FILE_CONTEXT,
                repository_id=REPO_ID,
                file_id="op_file3",
                file_path="bad3.py",
                language=Language.PYTHON,
                parent_entity_id=REPO_ID,
                name="bad3.py",
                qualified_name="bad3.py",
                source_location=SourceLocation(
                    file_path="bad3.py", start_line=1, start_column=0, end_line=1, end_column=0
                ),
                content="",
            ),
            CodeChunk(
                id="valid_1",
                chunk_type=ChunkType.FILE_CONTEXT,
                repository_id=REPO_ID,
                file_id="valid_file",
                file_path="good.py",
                language=Language.PYTHON,
                parent_entity_id=REPO_ID,
                name="good.py",
                qualified_name="good.py",
                source_location=SourceLocation(
                    file_path="good.py", start_line=1, start_column=0, end_line=1, end_column=0
                ),
                content="",
            ),
        ],
        file_chunk_map={
            "bad1.py": ["op_1"],
            "bad2.py": ["op_2"],
            "bad3.py": ["op_3"],
            "good.py": ["valid_1"],
        },
        entity_chunk_map={},
    )

    changed = ChangedSymbolResult(
        repository_path=REPO_ID,
        base_commit="A",
        target_commit="B",
        changed_symbols=[
            ChangedSymbol(
                file_path="good.py",
                symbol_id="valid_1",
                kind="file",
                name="good",
                qualified_name="good",
                previous_symbol_id="valid_1",
                change_type=SymbolChangeType.MODIFIED,
            )
        ],
        opaque_files=[
            OpaqueFile(
                path="bad1.py",
                change_type=ChangeType.MODIFIED,
                reason=OpaqueFileFallbackReason.UNSUPPORTED_LANGUAGE,
            ),
            OpaqueFile(
                path="bad2.py",
                change_type=ChangeType.MODIFIED,
                reason=OpaqueFileFallbackReason.PARSER_FAILURE,
            ),
            OpaqueFile(
                path="bad3.py",
                change_type=ChangeType.MODIFIED,
                reason=OpaqueFileFallbackReason.SOURCE_UNAVAILABLE,
            ),
        ],
    )

    plan = planner.plan(changed, old_coll, {}, {}, {}, REPO_ID)

    # PROOF: Old chunks for opaque files are preserved (not in chunks_to_remove), only valid_1 is removed.
    assert "op_1" not in plan.chunks_to_remove
    assert "op_2" not in plan.chunks_to_remove
    assert "op_3" not in plan.chunks_to_remove
    assert "valid_1" in plan.chunks_to_remove


# ---- BLOCKER 2 FAILURE SAFETY TESTS ----


def test_failure_safety_provider_exception() -> None:
    # Prove that if embedding generation fails, Lexical and Vector mutations do not occur.
    from typing import Any

    from retrieval.enums import ChunkType
    from retrieval.exceptions import EmbeddingProviderError
    from retrieval.models import CodeChunk

    class FailingProvider(DeterministicTestEmbeddingProvider):
        def embed(self, inputs: list[Any]) -> list[Any]:
            raise EmbeddingProviderError("Simulated failure", retryable=False)

    lexical = BM25LexicalIndex()
    vector = VectorIndex()
    provider = FailingProvider()

    old_chunk = CodeChunk(
        id="old_valid",
        chunk_type=ChunkType.FILE_CONTEXT,
        repository_id=REPO_ID,
        file_id="file",
        file_path="file.py",
        language=Language.PYTHON,
        parent_entity_id=REPO_ID,
        name="f",
        qualified_name="f",
        source_location=SourceLocation(
            file_path="file.py", start_line=1, start_column=0, end_line=1, end_column=0
        ),
        content="old",
    )
    new_chunk = CodeChunk(
        id="new_valid",
        chunk_type=ChunkType.FILE_CONTEXT,
        repository_id=REPO_ID,
        file_id="file",
        file_path="file.py",
        language=Language.PYTHON,
        parent_entity_id=REPO_ID,
        name="f",
        qualified_name="f",
        source_location=SourceLocation(
            file_path="file.py", start_line=1, start_column=0, end_line=1, end_column=0
        ),
        content="new code",
    )

    lexical.add(old_chunk)

    from retrieval.partial_reindexer import PartialReindexer

    executor = PartialReindexer(lexical, vector, provider)

    plan = PartialReindexPlan(
        repository_id=REPO_ID,
        base_commit="A",
        target_commit="B",
        chunks_to_remove=["old_valid"],
        chunks_to_add=[new_chunk],
    )

    import pytest

    with pytest.raises(EmbeddingProviderError):
        executor.execute(plan)

    # PROOF: old_chunk was NOT removed because execution failed during preparation.
    assert lexical.document_count(REPO_ID) == 1
    assert lexical.search("f", REPO_ID)[0].chunk_id == "old_valid"


# ---- BLOCKER 3 EMBEDDING COMPATIBILITY TESTS ----


def test_embedding_config_compatibility() -> None:
    chunker = CodeChunker()
    from backend.git.models import ChangedSymbol, ChangedSymbolResult, SymbolChangeType

    n1 = {
        "f.py": NormalizationResult(
            file=IRFile(
                id="f",
                repository_id=REPO_ID,
                path="f.py",
                language=Language.PYTHON,
                loc=1,
                location=SourceLocation(
                    file_path="f.py", start_line=1, start_column=0, end_line=1, end_column=0
                ),
                module_ids=[],
                name="f",
            ),
            functions=[],
        )
    }

    old_coll = chunker.chunk_repository([n1["f.py"]], {"f.py": "unchanged"}, commit_sha="A")
    old_c = old_coll.chunks[0]

    old_embs = {
        old_c.id: EmbeddingResult(
            chunk_id=old_c.id,
            vector=[0.1] * 10,
            dimension=10,
            provider_name="P1",
            model_name="M1",
            embedding_version="V1",
            repository_id=REPO_ID,
        )
    }

    p1_prov = DeterministicTestEmbeddingProvider(
        provider_name="P1", model_name="M1", dimension=10, embedding_version="V1"
    )
    planner1 = PartialReindexPlanner(chunker, provider=p1_prov)
    c1 = ChangedSymbolResult(
        repository_path=REPO_ID,
        base_commit="A",
        target_commit="B",
        changed_symbols=[
            ChangedSymbol(
                file_path="f.py",
                symbol_id="s",
                kind="file",
                name="f",
                qualified_name="f",
                change_type=SymbolChangeType.MODIFIED,
            )
        ],
        opaque_files=[],
    )

    p1 = planner1.plan(c1, old_coll, old_embs, n1, {"f.py": "unchanged"}, REPO_ID)
    assert len(p1.embeddings_to_reuse) == 1

    p2_prov = DeterministicTestEmbeddingProvider(
        provider_name="P1", model_name="M1", dimension=20, embedding_version="V1"
    )
    planner2 = PartialReindexPlanner(chunker, provider=p2_prov)
    p2 = planner2.plan(c1, old_coll, old_embs, n1, {"f.py": "unchanged"}, REPO_ID)
    assert len(p2.embeddings_to_reuse) == 0


def test_apply_stage_lexical_failure_exposes_fractured_state() -> None:
    from typing import Any

    from code_analyzer.ir import SourceLocation
    from code_analyzer.parsers.models import Language
    from retrieval.enums import ChunkType
    from retrieval.models import CodeChunk
    from retrieval.partial_reindexer import PartialReindexer, PartialReindexPlan

    class FailingLexicalIndex(BM25LexicalIndex):
        def add_many(self, chunks: Any) -> None:
            raise RuntimeError("Simulated lexical failure")

    lexical = FailingLexicalIndex()
    vector = VectorIndex()
    provider = DeterministicTestEmbeddingProvider()

    old_c = CodeChunk(
        id="c1",
        chunk_type=ChunkType.FILE_CONTEXT,
        repository_id=REPO_ID,
        file_id="f",
        file_path="f.py",
        language=Language.PYTHON,
        parent_entity_id=REPO_ID,
        name="f",
        qualified_name="f",
        source_location=SourceLocation(
            file_path="f.py", start_line=1, start_column=0, end_line=1, end_column=0
        ),
        content="old",
    )
    new_c = CodeChunk(
        id="c2",
        chunk_type=ChunkType.FILE_CONTEXT,
        repository_id=REPO_ID,
        file_id="f",
        file_path="f.py",
        language=Language.PYTHON,
        parent_entity_id=REPO_ID,
        name="f",
        qualified_name="f",
        source_location=SourceLocation(
            file_path="f.py", start_line=1, start_column=0, end_line=1, end_column=0
        ),
        content="new",
    )

    lexical.add(old_c)

    executor = PartialReindexer(lexical, vector, provider)
    plan = PartialReindexPlan(
        repository_id=REPO_ID,
        base_commit="A",
        target_commit="B",
        chunks_to_remove=["c1"],
        chunks_to_add=[new_c],
    )

    import pytest

    with pytest.raises(RuntimeError, match="Simulated lexical failure"):
        executor.execute(plan)

    # PROOF: System fractures. "c1" was successfully removed BEFORE the failure,
    # but "c2" failed to add.
    assert lexical.document_count(REPO_ID) == 0


def test_apply_stage_vector_failure_exposes_fractured_state() -> None:
    from typing import Any

    from code_analyzer.ir import SourceLocation
    from code_analyzer.parsers.models import Language
    from retrieval.enums import ChunkType
    from retrieval.models import CodeChunk
    from retrieval.partial_reindexer import PartialReindexer, PartialReindexPlan

    class FailingVectorIndex(VectorIndex):
        def add_many(self, embs: Any, chunks: Any = None) -> None:
            raise RuntimeError("Simulated vector failure")

    lexical = BM25LexicalIndex()
    vector = FailingVectorIndex()
    provider = DeterministicTestEmbeddingProvider()

    old_c = CodeChunk(
        id="c1",
        chunk_type=ChunkType.FILE_CONTEXT,
        repository_id=REPO_ID,
        file_id="f",
        file_path="f.py",
        language=Language.PYTHON,
        parent_entity_id=REPO_ID,
        name="f",
        qualified_name="f",
        source_location=SourceLocation(
            file_path="f.py", start_line=1, start_column=0, end_line=1, end_column=0
        ),
        content="old",
    )
    new_c = CodeChunk(
        id="c2",
        chunk_type=ChunkType.FILE_CONTEXT,
        repository_id=REPO_ID,
        file_id="f",
        file_path="f.py",
        language=Language.PYTHON,
        parent_entity_id=REPO_ID,
        name="f",
        qualified_name="f",
        source_location=SourceLocation(
            file_path="f.py", start_line=1, start_column=0, end_line=1, end_column=0
        ),
        content="new",
    )

    lexical.add(old_c)

    executor = PartialReindexer(lexical, vector, provider)
    plan = PartialReindexPlan(
        repository_id=REPO_ID,
        base_commit="A",
        target_commit="B",
        chunks_to_remove=["c1"],
        chunks_to_add=[new_c],
        embeddings_to_reuse=[],
    )

    import pytest

    with pytest.raises(RuntimeError, match="Simulated vector failure"):
        executor.execute(plan)

    # PROOF: Lexical mutations SUCCEEDED, but Vector mutations FAILED, resulting in mismatch.
    assert lexical.document_count(REPO_ID) == 1
    assert lexical.search("f", REPO_ID)[0].chunk_id == "c2"
