"""Tests for Phase 8D Dependency-Aware Invalidation."""

from backend.git.models import ChangedSymbol, ChangedSymbolResult, SymbolChangeType
from graph.edges import GraphEdge
from graph.enums import EdgeKind, NodeKind
from graph.models import CodeGraph
from graph.nodes import GraphNode
from retrieval.dependency_invalidator import DependencyInvalidator


def test_unrelated_files_are_ignored() -> None:
    """CRITICAL: A changed, B dependent, C/D/E unrelated = untouched."""
    invalidator = DependencyInvalidator()
    graph = CodeGraph(repository_id="r1", nodes={}, edges={})

    # A = root, B = depends on A, C/D/E = unrelated
    n_a = GraphNode(id="A", kind=NodeKind.CLASS, name="A", qualified_name="A", file_id="f_a")
    n_b = GraphNode(id="B", kind=NodeKind.CLASS, name="B", qualified_name="B", file_id="f_b")
    n_c = GraphNode(id="C", kind=NodeKind.CLASS, name="C", qualified_name="C", file_id="f_c")

    graph.nodes = {"A": n_a, "B": n_b, "C": n_c}
    # B calls A
    graph.edges = {"e1": GraphEdge(id="e1", source_id="B", target_id="A", kind=EdgeKind.CALLS)}

    c = ChangedSymbolResult(
        repository_path="r1",
        base_commit="1",
        target_commit="2",
        changed_symbols=[
            ChangedSymbol(
                symbol_id="A",
                change_type=SymbolChangeType.MODIFIED,
                name="A",
                qualified_name="A",
                kind="CLASS",
                file_path="f_a",
            )
        ],
        opaque_files=[],
    )

    res = invalidator.invalidate(c, graph)

    assert res.directly_changed_symbols == ["A"]
    assert len(res.dependency_affected_symbols) == 1
    assert res.dependency_affected_symbols[0].symbol_id == "B"
    assert res.dependency_affected_symbols[0].file_path == "f_b"

    affected_files = [f.file_path for f in res.affected_files]
    assert affected_files == ["f_b"]
    # C is untouched entirely.


def test_multiple_dependency_paths() -> None:
    """CRITICAL: A changes. B depends on A. C depends on A. D depends on B and C. D exactly once."""
    graph = CodeGraph(repository_id="r1", nodes={}, edges={})
    nodes = {
        "A": GraphNode(id="A", kind=NodeKind.CLASS, name="A", qualified_name="A", file_id="f_a"),
        "B": GraphNode(id="B", kind=NodeKind.CLASS, name="B", qualified_name="B", file_id="f_b"),
        "C": GraphNode(id="C", kind=NodeKind.CLASS, name="C", qualified_name="C", file_id="f_c"),
        "D": GraphNode(id="D", kind=NodeKind.CLASS, name="D", qualified_name="D", file_id="f_d"),
    }
    graph.nodes = nodes
    graph.edges = {
        "e1": GraphEdge(id="e1", source_id="B", target_id="A", kind=EdgeKind.CALLS),
        "e2": GraphEdge(id="e2", source_id="C", target_id="A", kind=EdgeKind.CALLS),
        "e3": GraphEdge(id="e3", source_id="D", target_id="B", kind=EdgeKind.CALLS),
        "e4": GraphEdge(id="e4", source_id="D", target_id="C", kind=EdgeKind.CALLS),
    }

    c = ChangedSymbolResult(
        repository_path="r1",
        base_commit="1",
        target_commit="2",
        changed_symbols=[
            ChangedSymbol(
                symbol_id="A",
                change_type=SymbolChangeType.MODIFIED,
                name="A",
                qualified_name="A",
                kind="CLASS",
                file_path="f_a",
            )
        ],
        opaque_files=[],
    )

    invalidator = DependencyInvalidator()
    res = invalidator.invalidate(c, graph)

    assert len(res.dependency_affected_symbols) == 3
    d_sym = next(s for s in res.dependency_affected_symbols if s.symbol_id == "D")
    assert d_sym.minimum_depth == 2


def test_cycle_safety() -> None:
    """CRITICAL: A -> B -> C -> A. A changes. Terminates, B and C exactly once."""
    graph = CodeGraph(repository_id="r1", nodes={}, edges={})
    graph.nodes = {
        "A": GraphNode(id="A", kind=NodeKind.CLASS, name="A", qualified_name="A", file_id="f_a"),
        "B": GraphNode(id="B", kind=NodeKind.CLASS, name="B", qualified_name="B", file_id="f_b"),
        "C": GraphNode(id="C", kind=NodeKind.CLASS, name="C", qualified_name="C", file_id="f_c"),
    }
    graph.edges = {
        "e1": GraphEdge(id="e1", source_id="A", target_id="B", kind=EdgeKind.CALLS),
        "e2": GraphEdge(id="e2", source_id="B", target_id="C", kind=EdgeKind.CALLS),
        "e3": GraphEdge(id="e3", source_id="C", target_id="A", kind=EdgeKind.CALLS),
    }

    c = ChangedSymbolResult(
        repository_path="r1",
        base_commit="1",
        target_commit="2",
        changed_symbols=[
            ChangedSymbol(
                symbol_id="A",
                change_type=SymbolChangeType.MODIFIED,
                name="A",
                qualified_name="A",
                kind="CLASS",
                file_path="f_a",
            )
        ],
        opaque_files=[],
    )

    invalidator = DependencyInvalidator()
    res = invalidator.invalidate(c, graph)

    # Impacted: C (depth 1), B (depth 2). A is direct change, omitted.
    assert len(res.dependency_affected_symbols) == 2
    assert {"B", "C"} == {s.symbol_id for s in res.dependency_affected_symbols}


def test_false_positive_by_name() -> None:
    """CRITICAL: B has similar name but no graph edge -> not affected."""
    graph = CodeGraph(repository_id="r1", nodes={}, edges={})
    graph.nodes = {
        "PaymentService": GraphNode(
            id="P", kind=NodeKind.CLASS, name="PaymentService", qualified_name="P", file_id="f"
        ),
        "PaymentServiceHelper": GraphNode(
            id="PH",
            kind=NodeKind.CLASS,
            name="PaymentServiceHelper",
            qualified_name="PH",
            file_id="f2",
        ),
    }

    c = ChangedSymbolResult(
        repository_path="r1",
        base_commit="1",
        target_commit="2",
        changed_symbols=[
            ChangedSymbol(
                symbol_id="P",
                change_type=SymbolChangeType.MODIFIED,
                name="PaymentService",
                qualified_name="P",
                kind="CLASS",
                file_path="f",
            )
        ],
        opaque_files=[],
    )

    invalidator = DependencyInvalidator()
    res = invalidator.invalidate(c, graph)

    assert len(res.dependency_affected_symbols) == 0


def test_deleted_dependency() -> None:
    """CRITICAL: A deleted. B previously depended on A. B affected."""
    graph = CodeGraph(repository_id="r1", nodes={}, edges={})
    graph.nodes = {
        "A": GraphNode(id="A", kind=NodeKind.CLASS, name="A", qualified_name="A", file_id="f_a"),
        "B": GraphNode(id="B", kind=NodeKind.CLASS, name="B", qualified_name="B", file_id="f_b"),
    }
    graph.edges = {"e1": GraphEdge(id="e1", source_id="B", target_id="A", kind=EdgeKind.CALLS)}

    # A is marked deleted
    c = ChangedSymbolResult(
        repository_path="r1",
        base_commit="1",
        target_commit="2",
        changed_symbols=[
            ChangedSymbol(
                symbol_id="A",
                change_type=SymbolChangeType.DELETED,
                name="A",
                qualified_name="A",
                kind="CLASS",
                file_path="f_a",
            )
        ],
        opaque_files=[],
    )

    invalidator = DependencyInvalidator()
    res = invalidator.invalidate(c, graph)
    assert len(res.dependency_affected_symbols) == 1
    assert res.dependency_affected_symbols[0].symbol_id == "B"


def test_dependency_affected_does_not_regenerate_embedding() -> None:
    """CRITICAL: 8C planner reuse logic avoids regenerating text embeddings for pure dependency-affected unchanged files."""
    from code_analyzer.ir import File as IRFile
    from code_analyzer.ir import SourceLocation
    from code_analyzer.normalization import NormalizationResult
    from code_analyzer.parsers.models import Language
    from retrieval.chunker import CodeChunker
    from retrieval.embedding_models import EmbeddingResult
    from retrieval.partial_reindexer import PartialReindexPlanner
    from retrieval.providers import DeterministicTestEmbeddingProvider

    invalidator = DependencyInvalidator()
    graph = CodeGraph(repository_id="r1", nodes={}, edges={})
    graph.nodes = {
        "A": GraphNode(id="A", kind=NodeKind.CLASS, name="A", qualified_name="A", file_id="f_a"),
        "B": GraphNode(id="B", kind=NodeKind.CLASS, name="B", qualified_name="B", file_id="f_b"),
    }
    graph.edges = {"e1": GraphEdge(id="e1", source_id="B", target_id="A", kind=EdgeKind.CALLS)}
    c = ChangedSymbolResult(
        repository_path="r1",
        base_commit="1",
        target_commit="2",
        changed_symbols=[
            ChangedSymbol(
                symbol_id="A",
                change_type=SymbolChangeType.MODIFIED,
                name="A",
                qualified_name="A",
                kind="CLASS",
                file_path="f_a",
            )
        ],
        opaque_files=[],
    )
    inv_res = invalidator.invalidate(c, graph)

    chunker = CodeChunker()
    prov = DeterministicTestEmbeddingProvider(
        provider_name="P1", model_name="M1", dimension=10, embedding_version="V1"
    )
    planner = PartialReindexPlanner(chunker, provider=prov)

    # f_b is the dependency affected file. It has source "unchanged".
    n_fb = NormalizationResult(
        file=IRFile(
            id="f_b",
            repository_id="r1",
            path="f_b",
            language=Language.PYTHON,
            loc=1,
            location=SourceLocation(
                file_path="f_b", start_line=1, start_column=0, end_line=1, end_column=0
            ),
            name="B",
            module_ids=[],
        ),
        functions=[],
    )
    old_coll = chunker.chunk_repository([n_fb], {"f_b": "unchanged"}, commit_sha="1")
    old_c = old_coll.chunks[0]
    old_embs = {
        old_c.id: EmbeddingResult(
            chunk_id=old_c.id,
            vector=[0.1] * 10,
            dimension=10,
            provider_name="P1",
            model_name="M1",
            embedding_version="V1",
            repository_id="r1",
        )
    }

    # A is skipped here to isolate just B (to keep test small)
    new_norm = {"f_b": n_fb}
    new_src = {"f_b": "unchanged"}

    plan = planner.plan(
        c, old_coll, old_embs, new_norm, new_src, "r1", dependency_invalidation=inv_res
    )

    # PROOF: Although f_b was in the affected target plan (via inv_res),
    # its identical source bypassed embedding regeneration completely!
    assert "f_b" in plan.files_modified
    assert len(plan.embeddings_to_reuse) == 1
    assert plan.embeddings_to_reuse[0].chunk_id == old_c.id
    assert len(plan.chunks_to_embed) == 0  # No AI calls needed!


def test_large_transitive_graph() -> None:
    """CRITICAL: Large synthetic graph for scalability sanity."""
    from backend.git.models import ChangedSymbol, ChangedSymbolResult, SymbolChangeType
    from graph.edges import GraphEdge
    from graph.enums import EdgeKind, NodeKind
    from graph.models import CodeGraph
    from graph.nodes import GraphNode
    from retrieval.dependency_invalidator import DependencyInvalidator

    graph = CodeGraph(repository_id="r1", nodes={}, edges={})

    # Root node
    graph.nodes["Root"] = GraphNode(
        id="Root", kind=NodeKind.CLASS, name="Root", qualified_name="Root", file_id="f_root"
    )

    # 5,000 dependents
    import time

    for i in range(5000):
        nid = f"Dep_{i}"
        graph.nodes[nid] = GraphNode(
            id=nid, kind=NodeKind.CLASS, name=nid, qualified_name=nid, file_id=f"f_{i}"
        )
        # Every node depends on Root
        eid = f"e_{i}"
        graph.edges[eid] = GraphEdge(id=eid, source_id=nid, target_id="Root", kind=EdgeKind.CALLS)

    c = ChangedSymbolResult(
        repository_path="r1",
        base_commit="1",
        target_commit="2",
        changed_symbols=[
            ChangedSymbol(
                symbol_id="Root",
                change_type=SymbolChangeType.MODIFIED,
                name="Root",
                qualified_name="Root",
                kind="CLASS",
                file_path="f_root",
            )
        ],
        opaque_files=[],
    )

    invalidator = DependencyInvalidator()
    start = time.time()
    res = invalidator.invalidate(c, graph)
    end = time.time()

    assert len(res.dependency_affected_symbols) == 5000
    assert len(res.affected_files) == 5000
    print(f"\nTransitive graph test: 5000 nodes, time={end - start:.3f}s")
