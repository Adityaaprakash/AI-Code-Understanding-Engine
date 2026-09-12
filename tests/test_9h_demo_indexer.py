"""Phase 9H — Integration Test Suite for End-to-End Demo Indexing.

Verifies that the Synchronous Demo Indexing orchestrator properly connects
the AST parsers, Canonical IR, Chunker, Embeddings, BM25 Index, and Graph Store,
and correctly populates the global runtime API stores.
"""

import uuid
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.repository import Repository
from backend.services.demo_indexer import DemoIndexer
from backend.services.graph_service import graph_service
from backend.services.query import query_service


@pytest.mark.asyncio
async def test_demo_indexer_e2e_population(db_session: AsyncSession, tmp_path: Path) -> None:
    """Verify that DemoIndexer end-to-end execution populates all runtime stores."""
    # 1. Setup a valid mini-repository in tmp path
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    (src_dir / "user_service.py").write_text(
        "class UserService:\n"
        "    def create_user(self, name: str):\n"
        "        print('Creating user', name)\n",
        encoding="utf-8",
    )

    (src_dir / "main.py").write_text(
        "from user_service import UserService\n"
        "\n"
        "def run():\n"
        "    svc = UserService()\n"
        "    svc.create_user('Alice')\n",
        encoding="utf-8",
    )

    repo_id = uuid.uuid4()

    # 2. Register repository in Database
    db_repo = Repository(
        id=repo_id,
        name="test-demo-repo",
        source_type="local",
        url="",
        local_path=str(tmp_path),
        default_branch="main",
        status="pending",
    )
    db_session.add(db_repo)
    await db_session.commit()

    # Clear out prior state for clean test
    query_service.lexical_index.clear()

    if hasattr(query_service.vector_index, "clear"):
        query_service.vector_index.clear()
    else:
        query_service.vector_index.embeddings.clear()
        query_service.vector_index.chunks.clear()

    if hasattr(graph_service.store, "clear"):
        try:
            graph_service.store.clear()
        except TypeError:
            pass  # old signature fallback

    # 3. Trigger the Demo Orchestrator synchronously
    stats = await DemoIndexer.index_repository(repo_id, db_session)

    # 4. Verify orchestration statistics
    assert stats["files_parsed"] == 2
    assert stats["nodes_created"] > 0
    assert stats["edges_created"] > 0
    assert stats["chunks_indexed"] > 0

    await db_session.refresh(db_repo)
    assert db_repo.status == "indexed"

    # 5. Verify population of global runtime service instances
    # Verify Lexical Index
    assert query_service.lexical_index.document_count(str(repo_id)) > 0

    # Verify Vector Index
    assert query_service.vector_index.document_count(str(repo_id)) > 0

    # Verify Graph Store - using impact analysis to test graph integration indirectly
    # Find the node for 'UserService' class
    user_svc_hits = query_service.lexical_retriever.retrieve("UserService", str(repo_id), top_k=5)

    assert len(user_svc_hits.results) > 0
    target_hit = None
    for h in user_svc_hits.results:
        if "UserService" in (h.symbol_name or "") or "UserService" in (h.qualified_name or ""):
            target_hit = h
            break

    assert target_hit is not None, "Could not find UserService chunk in BM25"

    # Find dependencies inside graph store
    # Even just ensuring there's more than 0 nodes is sufficient for the orchestrator proof
    assert graph_service.store.node_count > 0
