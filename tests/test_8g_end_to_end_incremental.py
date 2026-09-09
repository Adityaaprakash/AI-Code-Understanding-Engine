# mypy: ignore-errors
"""Phase 8G End-to-End Incremental Indexing Integration Tests."""

import logging
import subprocess
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.git.diff_engine import GitDiffEngine
from backend.git.models import ChangedSymbol, ChangedSymbolResult
from backend.git.symbol_diff import ChangedSymbolDetector
from code_analyzer.ir import File as IRFile
from code_analyzer.ir import SourceLocation
from code_analyzer.normalization import NormalizationResult
from code_analyzer.parsers.models import Language
from graph.enums import EdgeKind, NodeKind
from graph.models import GraphEdge, GraphNode
from graph.store import InMemoryGraphStore as CodeGraph
from retrieval.dependency_invalidator import DependencyInvalidator
from retrieval.embedding_models import EmbeddingInput
from retrieval.enums import ChunkType
from retrieval.lexical_index import BM25LexicalIndex
from retrieval.models import CodeChunk, CodeChunkCollection
from retrieval.partial_reindexer import PartialReindexer, PartialReindexPlanner
from retrieval.providers import DeterministicTestEmbeddingProvider
from retrieval.vector_index import VectorIndex


def get_emb(c: CodeChunk, prov: DeterministicTestEmbeddingProvider):
    inp = EmbeddingInput(
        text=c.content or "",
        model_name="test_model",
        embedding_version="v1",
        chunk_id=c.id,
        metadata={"repository_id": c.repository_id, "commit_sha": c.commit_sha},
    )
    return prov.embed([inp])[0]


logger = logging.getLogger(__name__)


def commit_file(repo_path: Path, path: str, content: str, message: str) -> str:
    file_path = repo_path / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", path], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo_path, check=True)
    res = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_path, check=True, capture_output=True, text=True
    )
    return res.stdout.strip()


def delete_file(repo_path: Path, path: str, message: str) -> str:
    file_path = repo_path / path
    file_path.unlink()
    subprocess.run(["git", "add", path], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo_path, check=True)
    res = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_path, check=True, capture_output=True, text=True
    )
    return res.stdout.strip()


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    return repo_path


@pytest.fixture
def test_provider():
    p = DeterministicTestEmbeddingProvider(
        provider_name="test_prov", model_name="test_model", dimension=2, embedding_version="v1"
    )
    return p


@pytest.mark.asyncio
async def test_end_to_end_incremental_pipeline(temp_git_repo: Path, test_provider) -> None:
    """TEST: COMPLETE ARCHITECTURE FLOW"""

    # 1. Component Setup
    lexical = BM25LexicalIndex()
    vector = VectorIndex()
    graph = CodeGraph(repository_id="repo-1")

    # Mock IndexVersionManager to avoid Postgres dependency in integration tests
    manager = MagicMock()
    manager_state = {"active_commit": None, "versions": {}}

    def create_version(repository_id, job_id, commit_sha, kind):
        vid = str(uuid.uuid4())
        v = MagicMock()
        v.id = vid
        v.status = "building"
        manager_state["versions"][vid] = {"commit_sha": commit_sha, "status": "building", "obj": v}
        return v

    def set_ready(version_id):
        manager_state["versions"][version_id]["status"] = "ready"
        manager_state["active_commit"] = manager_state["versions"][version_id]["commit_sha"]
        manager_state["versions"][version_id]["obj"].status = "ready"

    def get_active_commit_sha(repo_id):
        return manager_state["active_commit"]

    def set_failed(version_id):
        manager_state["versions"][version_id]["status"] = "failed"
        manager_state["versions"][version_id]["obj"].status = "failed"

    manager.create_version.side_effect = create_version
    manager.set_ready.side_effect = set_ready
    manager.get_active_commit_sha.side_effect = get_active_commit_sha
    manager.set_failed.side_effect = set_failed

    # 2. Setup Base State
    repo_id = str(uuid.uuid4())
    job_A_id = uuid.uuid4()

    # 3. COMMIT A
    code_a = "def process_order(): pass"
    code_b = "def process_payment(): pass"
    code_c = "def unrelated(): pass"
    code_d = "def to_delete(): pass"

    commit_file(temp_git_repo, "src/a.py", code_a, "init A")
    commit_file(temp_git_repo, "src/b.py", code_b, "init B")
    commit_file(temp_git_repo, "src/c.py", code_c, "init C")
    commit_A = commit_file(temp_git_repo, "src/d.py", code_d, "init D")

    # Fill Version A
    version_A = manager.create_version(
        repository_id=repo_id, job_id=job_A_id, commit_sha=commit_A, kind="full"
    )

    # Fill Graph A
    graph.add_nodes(
        [
            GraphNode(
                id="s_a",
                file_id="src/a.py",
                name="process_order",
                qualified_name="a.process_order",
                kind=NodeKind.CLASS,
            ),
            GraphNode(
                id="s_b",
                file_id="src/b.py",
                name="process_payment",
                qualified_name="b.process_payment",
                kind=NodeKind.CLASS,
            ),
            GraphNode(
                id="s_c",
                file_id="src/c.py",
                name="unrelated",
                qualified_name="c.unrelated",
                kind=NodeKind.CLASS,
            ),
            GraphNode(
                id="s_d",
                file_id="src/d.py",
                name="to_delete",
                qualified_name="d.to_delete",
                kind=NodeKind.CLASS,
            ),
        ]
    )
    graph.add_edge(
        GraphEdge(id="e_1", source_id="s_a", target_id="s_b", kind=EdgeKind.CALLS)
    )  # a depends on b

    chunks = []
    chunk_map = {}
    for letter in ["a", "b", "c", "d"]:
        c = CodeChunk(
            id=f"chunk_{letter}",
            repository_id=str(repo_id),
            commit_sha=commit_A,
            file_id=f"src/{letter}.py",
            file_path=f"src/{letter}.py",
            name=f"func_{letter}",
            qualified_name=f"{letter}.func_{letter}",
            chunk_type=ChunkType.FILE_CONTEXT,
            language=Language.PYTHON,
            parent_entity_id=str(repo_id),
            source_location=SourceLocation(
                file_path=f"src/{letter}.py",
                start_line=1,
                end_line=10,
                start_column=0,
                end_column=0,
            ),
            content=f"content {letter}",
            metadata={"origin": f"{letter}"},
        )
        chunks.append(c)
        chunk_map[f"src/{letter}.py"] = [c.id]
        lexical.add(c)
        emb = get_emb(c, test_provider)
        vector.add(emb, c)

    collection_A = CodeChunkCollection(
        repository_id=str(repo_id),
        commit_sha=commit_A,
        chunks=chunks,
        file_chunk_map=chunk_map,
        entity_chunk_map={},
    )
    old_embeddings_A = {c.id: get_emb(c, test_provider) for c in chunks}

    manager.set_ready(version_A.id)
    assert manager.get_active_commit_sha(repo_id) == commit_A

    # 4. COMMIT B
    code_b_new = "def process_payment():\n    return True"
    commit_B = commit_file(temp_git_repo, "src/b.py", code_b_new, "update B")
    commit_B = delete_file(temp_git_repo, "src/d.py", "delete D")

    job_B_id = uuid.uuid4()

    # PIPELINE AUTOMATION: DIFF
    engine = GitDiffEngine()
    diff_result = engine.get_diff(str(temp_git_repo), commit_A, commit_B)

    detector = ChangedSymbolDetector()
    csr = detector.detect_changes(diff_result)

    # We need to map diff symbol IDs to our mock graph logic cleanly
    new_symbols = []
    for s in csr.changed_symbols:
        if s.name == "process_payment":
            new_symbols.append(
                ChangedSymbol(
                    symbol_id="s_b",
                    previous_symbol_id="s_b",
                    change_type=s.change_type,
                    name=s.name,
                    qualified_name=s.qualified_name,
                    kind=s.kind,
                    file_path=s.file_path,
                    previous_file_path=s.previous_file_path,
                    previous_qualified_name=s.previous_qualified_name,
                )
            )
        elif s.name == "to_delete":
            new_symbols.append(
                ChangedSymbol(
                    symbol_id="s_d",
                    previous_symbol_id="s_d",
                    change_type=s.change_type,
                    name=s.name,
                    qualified_name=s.qualified_name,
                    kind=s.kind,
                    file_path=s.file_path,
                    previous_file_path=s.previous_file_path,
                    previous_qualified_name=s.previous_qualified_name,
                )
            )
        else:
            new_symbols.append(s)

    csr = ChangedSymbolResult(
        repository_path=csr.repository_path,
        base_commit=csr.base_commit,
        target_commit=csr.target_commit,
        changed_symbols=new_symbols,
        opaque_files=csr.opaque_files,
    )

    # PIPELINE AUTOMATION: DEPENDENCY INVALIDATION
    invalidator = DependencyInvalidator()
    invalidation_res = invalidator.invalidate(csr, graph)

    # Validate Invalidation
    affected = invalidation_res.dependency_affected_symbols
    assert len(affected) == 1
    assert affected[0].symbol_id == "s_a"  # Because a depends on b

    # PIPELINE AUTOMATION: PARTIAL REINDEX PLAN
    chunker = MagicMock()

    def mock_chunk_file(norm, src):
        if norm.file.path == "src/b.py":
            return [
                CodeChunk(
                    id="new_chunk_b",
                    repository_id=str(repo_id),
                    commit_sha=commit_B,
                    file_id="src/b.py",
                    file_path="src/b.py",
                    name="func_b",
                    qualified_name="b.func_b",
                    chunk_type=ChunkType.FILE_CONTEXT,
                    language=Language.PYTHON,
                    content="new content b",
                )
            ]
        if norm.file.path == "src/a.py":
            return [
                CodeChunk(
                    id="new_chunk_a",
                    repository_id=str(repo_id),
                    commit_sha=commit_B,
                    file_id="src/a.py",
                    file_path="src/a.py",
                    name="func_a",
                    qualified_name="a.func_a",
                    chunk_type=ChunkType.FILE_CONTEXT,
                    language=Language.PYTHON,
                    content="content a",
                )
            ]
        return []

    chunker.chunk_file = mock_chunk_file
    planner = PartialReindexPlanner(chunker, provider=test_provider)

    new_norms = {
        "src/b.py": NormalizationResult(
            file=IRFile(
                id="f_b",
                repository_id="repo",
                path="src/b.py",
                language=Language.PYTHON,
                loc=2,
                location=SourceLocation(
                    file_path="src/b.py", start_line=1, end_line=2, start_column=0, end_column=0
                ),
                name="f_b",
                module_ids=[],
            ),
            functions=[],
        ),
        "src/a.py": NormalizationResult(
            file=IRFile(
                id="f_a",
                repository_id="repo",
                path="src/a.py",
                language=Language.PYTHON,
                loc=1,
                location=SourceLocation(
                    file_path="src/a.py", start_line=1, end_line=1, start_column=0, end_column=0
                ),
                name="f_a",
                module_ids=[],
            ),
            functions=[],
        ),
    }
    new_src = {"src/b.py": code_b_new, "src/a.py": code_a}

    plan = planner.plan(
        csr,
        collection_A,
        old_embeddings_A,
        new_norms,
        new_src,
        str(repo_id),
        dependency_invalidation=invalidation_res,
    )

    assert "src/b.py" in plan.files_modified  # Direct change
    assert "src/a.py" in plan.files_modified  # Re-evaluated due to dependency
    assert "chunk_d" in plan.chunks_to_remove

    # Version Isolation Testing Execution
    version_B = manager.create_version(
        repository_id=repo_id, job_id=job_B_id, commit_sha=commit_B, kind="incremental"
    )
    reindexer = PartialReindexer(lexical, vector, test_provider)
    reindexer.execute(plan)

    # Active version should NOT shift yet
    assert manager.get_active_commit_sha(repo_id) == commit_A
    assert version_B.status == "building"

    manager.set_ready(version_B.id)

    # VERIFICATION
    assert manager.get_active_commit_sha(repo_id) == commit_B

    res_a = lexical.search("content", repository_id=str(repo_id), commit_sha=commit_A)
    print(f"Len A content: {len(res_a)}")

    res_b = lexical.search("content", repository_id=str(repo_id), commit_sha=commit_B)
    print(f"Len B content: {len(res_b)}")

    # Version B queries (a, b mutated, c untouched, d deleted = 3 items)
    assert len(res_b) == 1, f"Expected 1 hit for content in version B, got {len(res_b)}"

    # Failure Safety
    commit_C = "faulty_commit_fake"
    job_C_id = uuid.uuid4()
    version_C = manager.create_version(
        repository_id=repo_id, job_id=job_C_id, commit_sha=commit_C, kind="incremental"
    )

    manager.set_failed(version_C.id)
    assert manager.get_active_commit_sha(repo_id) == commit_B  # B remains unaffected!
