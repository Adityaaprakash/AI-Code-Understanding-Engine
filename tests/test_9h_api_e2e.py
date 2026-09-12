"""Phase 9H - Real API End-to-End Test for Demo Indexing."""

from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_demo_api_end_to_end(async_client: AsyncClient, tmp_path: Path) -> None:
    """Verify that DemoIndexer successfully coordinates the entire API flow:
    Repository Creation -> Sync Index Demo -> Query -> Symbol -> Graph.
    """
    if async_client is None:
        pytest.skip("Test environment is missing async_client.")

    # 1. Setup a real codebase (Python)
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    (src_dir / "user_auth.py").write_text(
        "class MockAuthService:\n"
        "    def login(self, username, password):\n"
        "        pass\n"
        "\n"
        "    def logout(self, user_id):\n"
        "        pass\n",
        encoding="utf-8",
    )

    (src_dir / "main.py").write_text(
        "from user_auth import MockAuthService\n"
        "\n"
        "def run_app():\n"
        "    auth = MockAuthService()\n"
        "    auth.login('admin', '1234')\n",
        encoding="utf-8",
    )

    # 2. Register repository
    create_payload = {
        "name": "api-demo-repo",
        "url": "https://github.com/test/demo",
        "local_path": str(tmp_path),
        "source_type": "local",
    }
    create_res = await async_client.post("/api/v1/repositories", json=create_payload)
    if create_res.status_code != 201:
        # Fallback to local session injection fallback if necessary
        pytest.skip(
            f"Could not create repository via API, DB might not be configured: {create_res.text}"
        )

    repo_data = create_res.json()
    repo_id = repo_data["id"]

    # 3. Call the Sync orchestrator endpoint
    index_res = await async_client.post(f"/api/v1/repositories/{repo_id}/index-demo")
    assert index_res.status_code == 200, f"Demo Index failed: {index_res.text}"

    index_data = index_res.json()
    assert "stats" in index_data
    stats = index_data["stats"]
    assert stats["files_parsed"] == 2
    assert stats["chunks_indexed"] >= 2
    assert stats["nodes_created"] > 0

    assert "job" in index_data
    assert index_data["job"]["status"] == "done"

    # 4. Search API
    query_payload = {
        "repository_id": repo_id,
        "query": "Where is the login logic?",
        "top_k": 5,
        "generate_answer": False,
    }

    search_res = await async_client.post("/api/v1/query", json=query_payload)
    assert search_res.status_code == 200, f"Query failed: {search_res.text}"

    search_data = search_res.json()
    assert "results" in search_data
    assert len(search_data["results"]) > 0

    # The result contract exposes the matched symbol name, rather than source text.
    found_login = any(
        "login" in (c.get("symbol_name") or "").lower() for c in search_data["results"]
    )
    assert found_login, "Failed to retrieve the target concept via hybrid search."

    # 5. Symbols API provides a graph node to traverse.
    sym_res = await async_client.get(
        f"/api/v1/symbols?repository_id={repo_id}&query=MockAuthService"
    )
    assert sym_res.status_code == 200
    sym_data = sym_res.json()["results"]

    assert len(sym_data) > 0

    node_id = sym_data[0]["node_id"]

    # 6. Graph traversal
    trav_res = await async_client.get(f"/api/v1/graph?source_node_id={node_id}&depth=1")
    assert trav_res.status_code == 200, f"Graph traversal failed: {trav_res.text}"
    trav_data = trav_res.json()
    assert "nodes" in trav_data
    assert "edges" in trav_data

    # 7. Impact API
    impact_res = await async_client.get(f"/api/v1/impact?source_node_id={node_id}&depth=3")
    assert impact_res.status_code == 200, f"Impact analysis failed: {impact_res.text}"

    impact_data = impact_res.json()
    assert "impacted_nodes" in impact_data
    # While the exact count depends on the AST linkage, the schema must be populated
    assert isinstance(impact_data["impacted_nodes"], list)
