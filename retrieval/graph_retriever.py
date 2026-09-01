"""Phase 5D Graph Retrieval Service implementation.

Consumes ProcessedQuery, interprets relationship query intent, and queries the existing
Phase 3 Code Knowledge Graph using GraphQueryEngine and ImpactAnalyzer contracts.
Maps structural graph node candidates into the unified RetrievalResultSet contract.
"""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any

from code_analyzer.parsers.models import Language
from graph.enums import EdgeKind, NodeKind
from graph.impact_analyzer import ImpactAnalyzer
from graph.query_engine import GraphQueryEngine
from retrieval.contracts import GraphRetrieverContract
from retrieval.enums import ChunkType
from retrieval.exceptions import GraphQueryError
from retrieval.query_models import ProcessedQuery, QueryKind
from retrieval.query_processor import QueryPreprocessor
from retrieval.retrieval_models import RetrievalResult, RetrievalResultSet

if TYPE_CHECKING:
    from graph.contracts import ImpactAnalyzerContract
    from graph.models import CodeGraph
    from graph.nodes import GraphNode
    from graph.store import InMemoryGraphStore
    from retrieval.models import CodeChunk


# Regex patterns for graph relationship intent extraction
CALLERS_PATTERN = re.compile(
    r"\b(?:who\s+calls?|what\s+calls?|called\s+by|callers?\s+of|where\s+is\s+.*?\s+called)\b",
    re.IGNORECASE,
)
CALLEES_PATTERN = re.compile(
    r"\b(?:what\s+does\s+.*?\s+call|callees?\s+of|calls?\s+made\s+by)\b",
    re.IGNORECASE,
)
IMPLEMENTS_INBOUND_PATTERN = re.compile(
    r"\b(?:which\s+classes?\s+implement|who\s+implements|what\s+implements|implementations?\s+of|implementing)\b",
    re.IGNORECASE,
)
IMPLEMENTS_OUTBOUND_PATTERN = re.compile(
    r"\b(?:what\s+does\s+.*?\s+implement|interfaces?\s+implemented\s+by)\b",
    re.IGNORECASE,
)
EXTENDS_INBOUND_PATTERN = re.compile(
    r"\b(?:what\s+inherits\s+from|which\s+classes?\s+extend|what\s+extends|subclasses?\s+of|derived\s+classes?)\b",
    re.IGNORECASE,
)
EXTENDS_OUTBOUND_PATTERN = re.compile(
    r"\b(?:what\s+does\s+.*?\s+inherit\s+from|what\s+does\s+.*?\s+extend|superclass\s+of|base\s+class\s+of)\b",
    re.IGNORECASE,
)
DEPENDENTS_PATTERN = re.compile(
    r"\b(?:who\s+depends\s+on|what\s+depends\s+on|which\s+code\s+depends\s+on|dependents?\s+of|depending\s+on)\b",
    re.IGNORECASE,
)
DEPENDENCIES_PATTERN = re.compile(
    r"\b(?:what\s+does\s+.*?\s+depend\s+on|dependencies\s+of)\b",
    re.IGNORECASE,
)
IMPORTS_INBOUND_PATTERN = re.compile(
    r"\b(?:which\s+modules?\s+import|who\s+imports|imported\s+by|where\s+is\s+.*?\s+imported)\b",
    re.IGNORECASE,
)
IMPORTS_OUTBOUND_PATTERN = re.compile(
    r"\b(?:what\s+does\s+.*?\s+import|imports\s+of)\b",
    re.IGNORECASE,
)
USES_PATTERN = re.compile(
    r"\b(?:where\s+is\s+.*?\s+used|who\s+uses|used\s+by|references?\s+to|who\s+references?)\b",
    re.IGNORECASE,
)
IMPACT_PATTERN = re.compile(
    r"\b(?:what\s+(?:will|could)?\s*be\s+affected|what\s+is\s+affected\s+by|what\s+could\s+break|impact\s+of|impact\s+radius)\b",
    re.IGNORECASE,
)


def _node_kind_to_chunk_type(kind: NodeKind) -> ChunkType:
    """Map Phase 3 NodeKind to Phase 5 ChunkType."""
    if kind == NodeKind.CLASS:
        return ChunkType.CLASS_CONTEXT
    if kind == NodeKind.INTERFACE:
        return ChunkType.INTERFACE_CONTEXT
    if kind == NodeKind.FUNCTION:
        return ChunkType.FUNCTION
    if kind == NodeKind.METHOD:
        return ChunkType.METHOD
    return ChunkType.FILE_CONTEXT


class GraphRetriever(GraphRetrieverContract):
    """Phase 5 Graph Retrieval Service.

    Consumes ProcessedQuery, interprets relationship intent, queries the existing
    Phase 3 Code Knowledge Graph, and returns a unified RetrievalResultSet.
    """

    def __init__(
        self,
        graph: CodeGraph | InMemoryGraphStore | None = None,
        graph_store: InMemoryGraphStore | None = None,
        query_engine: GraphQueryEngine | None = None,
        impact_analyzer: ImpactAnalyzerContract | None = None,
        query_preprocessor: QueryPreprocessor | None = None,
        chunk_lookup: dict[str, CodeChunk] | None = None,
    ) -> None:
        """Initialize GraphRetriever service.

        Args:
            graph: Single CodeGraph or InMemoryGraphStore container.
            graph_store: Multi-repository InMemoryGraphStore engine.
            query_engine: Phase 3 GraphQueryEngine instance.
            impact_analyzer: Phase 3 ImpactAnalyzer instance.
            query_preprocessor: QueryPreprocessor instance.
            chunk_lookup: Optional chunk map keyed by chunk_id or entity_id.
        """
        self.graph = graph
        self.graph_store = graph_store
        self.query_engine = query_engine or GraphQueryEngine()
        self.impact_analyzer = impact_analyzer or ImpactAnalyzer(query_engine=self.query_engine)
        self.preprocessor = query_preprocessor or QueryPreprocessor()
        self.chunk_lookup = chunk_lookup or {}

    def retrieve(
        self,
        query: str | ProcessedQuery,
        repository_id: str,
        top_k: int = 10,
        language: Language | None = None,
        chunk_type: ChunkType | None = None,
        file_path: str | None = None,
        commit_sha: str | None = None,
    ) -> RetrievalResultSet:
        """Execute Phase 5 graph retrieval pipeline returning ranked structural candidates."""
        # 1. Input Validation
        if not repository_id or not repository_id.strip():
            raise GraphQueryError("repository_id cannot be empty or whitespace")
        repo_id = repository_id.strip()

        if top_k <= 0:
            raise GraphQueryError(f"top_k must be > 0, got {top_k}")

        prep_latency_ms = 0.0

        # 2. Query Preprocessing

        if isinstance(query, ProcessedQuery):
            processed_query = query
        elif isinstance(query, str):
            if not query or not query.strip():
                raise GraphQueryError("Query string cannot be empty or whitespace")
            p_start = time.perf_counter()
            processed_query = self.preprocessor.process(query)
            prep_latency_ms = (time.perf_counter() - p_start) * 1000.0
        else:
            raise GraphQueryError(
                f"Query must be str or ProcessedQuery, got {type(query).__name__}"
            )

        retrieval_start = time.perf_counter()

        # 3. Locate Target Graph Container for Repository
        repo_graph = self._resolve_graph_for_repo(repo_id)
        if repo_graph is None:
            total_lat = prep_latency_ms + (time.perf_counter() - retrieval_start) * 1000.0
            return RetrievalResultSet(
                query=processed_query,
                repository_id=repo_id,
                results=[],
                total_matches=0,
                preprocessing_latency_ms=prep_latency_ms,
                retrieval_latency_ms=total_lat - prep_latency_ms,
                total_latency_ms=total_lat,
            )

        # 4. Interpret Query Intent
        intent = self._interpret_query(processed_query)
        if not intent["is_graph_relevant"]:
            total_lat = prep_latency_ms + (time.perf_counter() - retrieval_start) * 1000.0
            return RetrievalResultSet(
                query=processed_query,
                repository_id=repo_id,
                results=[],
                total_matches=0,
                preprocessing_latency_ms=prep_latency_ms,
                retrieval_latency_ms=total_lat - prep_latency_ms,
                total_latency_ms=total_lat,
            )

        # 5. Resolve Target Symbol Nodes in Graph
        target_nodes = self._resolve_target_nodes(
            repo_graph=repo_graph,
            target_candidates=intent["target_candidates"],
        )

        if not target_nodes:
            total_lat = prep_latency_ms + (time.perf_counter() - retrieval_start) * 1000.0
            return RetrievalResultSet(
                query=processed_query,
                repository_id=repo_id,
                results=[],
                total_matches=0,
                preprocessing_latency_ms=prep_latency_ms,
                retrieval_latency_ms=total_lat - prep_latency_ms,
                total_latency_ms=total_lat,
            )

        # 6. Execute Graph Traversal & Relationship Queries
        raw_candidates: list[tuple[GraphNode, float, int, str, str]] = []
        # Item: (node, score, depth, relationship_kind_str, direction)

        for target_node in target_nodes:
            if intent["is_impact_query"]:
                try:
                    impact_res = self.impact_analyzer.analyze_impact(
                        node_id=target_node.id,
                        graph=repo_graph,
                        max_depth=5,
                    )
                    for impacted in impact_res.impacted_nodes:
                        inode = self._get_node(repo_graph, impacted.symbol_id)
                        if inode is not None:
                            depth = impacted.minimum_depth
                            score = max(0.1, 1.0 - (depth * 0.1))
                            rel_str = (
                                impacted.relationship_types[0].value
                                if impacted.relationship_types
                                else "IMPACT"
                            )
                            raw_candidates.append((inode, score, depth, rel_str, "inbound"))
                except KeyError:
                    pass

            elif intent["relationship"] == EdgeKind.CALLS:
                if intent["direction"] == "inbound":
                    nodes = self.query_engine.get_callers(target_node.id, repo_graph)
                    for n in nodes:
                        raw_candidates.append((n, 0.9, 1, "CALLS", "inbound"))
                else:
                    nodes = self.query_engine.get_callees(target_node.id, repo_graph)
                    for n in nodes:
                        raw_candidates.append((n, 0.9, 1, "CALLS", "outbound"))

            elif intent["relationship"] == "DEPENDENT":
                nodes = self.query_engine.get_dependents(target_node.id, repo_graph, max_depth=1)
                for n in nodes:
                    raw_candidates.append((n, 0.9, 1, "DEPENDENT", "inbound"))

            elif intent["relationship"] == "DEPENDENCY":
                nodes = self.query_engine.get_dependencies(target_node.id, repo_graph, max_depth=1)
                for n in nodes:
                    raw_candidates.append((n, 0.9, 1, "DEPENDENCY", "outbound"))

            elif isinstance(intent["relationship"], EdgeKind):
                ekind = intent["relationship"]
                if intent["direction"] == "inbound":
                    nodes = self.query_engine.get_inbound_neighbors(
                        target_node.id, repo_graph, kind=ekind
                    )
                    for n in nodes:
                        raw_candidates.append((n, 0.9, 1, ekind.value.upper(), "inbound"))
                else:
                    nodes = self.query_engine.get_outbound_neighbors(
                        target_node.id, repo_graph, kind=ekind
                    )
                    for n in nodes:
                        raw_candidates.append((n, 0.9, 1, ekind.value.upper(), "outbound"))

            elif intent["relationship"] == "IDENTIFIER":
                # For pure identifier queries, include target node itself + depth 1 neighbors
                raw_candidates.append((target_node, 1.0, 0, "EXACT_TARGET", "self"))
                in_neighbors = self.query_engine.get_inbound_neighbors(target_node.id, repo_graph)
                for n in in_neighbors:
                    raw_candidates.append((n, 0.8, 1, "NEIGHBOR", "inbound"))
                out_neighbors = self.query_engine.get_outbound_neighbors(target_node.id, repo_graph)
                for n in out_neighbors:
                    raw_candidates.append((n, 0.8, 1, "NEIGHBOR", "outbound"))

        # 7. Convert Graph Nodes to RetrievalResult and Apply Filters
        dedup_results: dict[str, RetrievalResult] = {}
        # Key: chunk_id -> best RetrievalResult

        for node, score, depth, rel_str, direction in raw_candidates:
            res = self._map_node_to_retrieval_result(
                node=node,
                repository_id=repo_id,
                score=score,
                rank=1,
                graph_relationship=rel_str,
                graph_direction=direction,
                graph_depth=depth,
            )

            # Enforce repository boundary
            if res.repository_id != repo_id:
                continue

            # Apply Metadata Filters
            if language is not None and res.language != language:
                continue
            if chunk_type is not None and res.chunk_type != chunk_type:
                continue
            if file_path is not None and res.file_path != file_path:
                continue
            if commit_sha is not None:
                c_sha = res.commit_sha or res.metadata.get("commit_sha")
                if c_sha != commit_sha:
                    continue

            # Deduplicate by canonical chunk_id (keep highest score / lowest depth)
            cid = res.chunk_id
            if cid not in dedup_results or res.score > dedup_results[cid].score:
                dedup_results[cid] = res

        # 8. Sort Candidates Deterministically
        sorted_candidates = sorted(
            dedup_results.values(),
            key=lambda r: (
                -r.score,
                r.metadata.get("graph_depth", 0),
                r.symbol_name or "",
                r.chunk_id,
            ),
        )

        total_matches = len(sorted_candidates)
        top_candidates = sorted_candidates[:top_k]

        # Re-assign 1-indexed ranks
        ranked_results: list[RetrievalResult] = []
        for idx, item in enumerate(top_candidates, start=1):
            ranked_results.append(item.model_copy(update={"rank": idx}))

        retrieval_latency_ms = (time.perf_counter() - retrieval_start) * 1000.0
        total_latency_ms = prep_latency_ms + retrieval_latency_ms

        return RetrievalResultSet(
            query=processed_query,
            repository_id=repo_id,
            results=ranked_results,
            total_matches=total_matches,
            preprocessing_latency_ms=prep_latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
            total_latency_ms=total_latency_ms,
        )

    def _resolve_graph_for_repo(self, repository_id: str) -> CodeGraph | InMemoryGraphStore | None:
        """Find graph container matching target repository_id."""
        if self.graph is not None:
            repo_id = getattr(self.graph, "repository_id", None)
            if repo_id is None or repo_id == repository_id:
                return self.graph
        if self.graph_store is not None:
            if (
                hasattr(self.graph_store, "repository_id")
                and self.graph_store.repository_id == repository_id
            ):
                return self.graph_store
            # Check if saved in graph store
            if repository_id in getattr(self.graph_store, "_saved_graphs", {}):
                return self.graph_store._saved_graphs[repository_id]
        return None

    def _get_node(self, graph: CodeGraph | InMemoryGraphStore, node_id: str) -> GraphNode | None:
        """Helper to safely retrieve node by ID from CodeGraph or InMemoryGraphStore."""
        if hasattr(graph, "get_node"):
            return graph.get_node(node_id)
        if hasattr(graph, "nodes") and isinstance(graph.nodes, dict):
            return graph.nodes.get(node_id)
        return None

    def _interpret_query(self, query: ProcessedQuery) -> dict[str, Any]:
        """Deterministically interpret query text and ProcessedQuery metadata into graph intent."""
        norm_query = query.normalized_query

        # Extract target candidates
        target_candidates: list[str] = list(query.qualified_name_candidates)
        for token in query.identifier_tokens:
            if token not in target_candidates:
                target_candidates.append(token)

        is_impact = bool(IMPACT_PATTERN.search(norm_query))
        if is_impact:
            return {
                "relationship": "IMPACT",
                "direction": "inbound",
                "target_candidates": target_candidates,
                "is_impact_query": True,
                "is_graph_relevant": bool(target_candidates),
            }

        # Check Calls (inbound)
        if CALLERS_PATTERN.search(norm_query):
            return {
                "relationship": EdgeKind.CALLS,
                "direction": "inbound",
                "target_candidates": target_candidates,
                "is_impact_query": False,
                "is_graph_relevant": bool(target_candidates),
            }

        # Check Calls (outbound)
        if CALLEES_PATTERN.search(norm_query):
            return {
                "relationship": EdgeKind.CALLS,
                "direction": "outbound",
                "target_candidates": target_candidates,
                "is_impact_query": False,
                "is_graph_relevant": bool(target_candidates),
            }

        # Check Implements (inbound)
        if IMPLEMENTS_INBOUND_PATTERN.search(norm_query):
            return {
                "relationship": EdgeKind.IMPLEMENTS,
                "direction": "inbound",
                "target_candidates": target_candidates,
                "is_impact_query": False,
                "is_graph_relevant": bool(target_candidates),
            }

        # Check Implements (outbound)
        if IMPLEMENTS_OUTBOUND_PATTERN.search(norm_query):
            return {
                "relationship": EdgeKind.IMPLEMENTS,
                "direction": "outbound",
                "target_candidates": target_candidates,
                "is_impact_query": False,
                "is_graph_relevant": bool(target_candidates),
            }

        # Check Extends / Inherits (inbound)
        if EXTENDS_INBOUND_PATTERN.search(norm_query):
            return {
                "relationship": EdgeKind.EXTENDS,
                "direction": "inbound",
                "target_candidates": target_candidates,
                "is_impact_query": False,
                "is_graph_relevant": bool(target_candidates),
            }

        # Check Extends / Inherits (outbound)
        if EXTENDS_OUTBOUND_PATTERN.search(norm_query):
            return {
                "relationship": EdgeKind.EXTENDS,
                "direction": "outbound",
                "target_candidates": target_candidates,
                "is_impact_query": False,
                "is_graph_relevant": bool(target_candidates),
            }

        # Check Dependents (inbound)
        if DEPENDENTS_PATTERN.search(norm_query):
            return {
                "relationship": "DEPENDENT",
                "direction": "inbound",
                "target_candidates": target_candidates,
                "is_impact_query": False,
                "is_graph_relevant": bool(target_candidates),
            }

        # Check Dependencies (outbound)
        if DEPENDENCIES_PATTERN.search(norm_query):
            return {
                "relationship": "DEPENDENCY",
                "direction": "outbound",
                "target_candidates": target_candidates,
                "is_impact_query": False,
                "is_graph_relevant": bool(target_candidates),
            }

        # Check Imports (inbound)
        if IMPORTS_INBOUND_PATTERN.search(norm_query):
            return {
                "relationship": EdgeKind.IMPORTS,
                "direction": "inbound",
                "target_candidates": target_candidates,
                "is_impact_query": False,
                "is_graph_relevant": bool(target_candidates),
            }

        # Check Imports (outbound)
        if IMPORTS_OUTBOUND_PATTERN.search(norm_query):
            return {
                "relationship": EdgeKind.IMPORTS,
                "direction": "outbound",
                "target_candidates": target_candidates,
                "is_impact_query": False,
                "is_graph_relevant": bool(target_candidates),
            }

        # Check Uses / References
        if USES_PATTERN.search(norm_query):
            return {
                "relationship": EdgeKind.USES,
                "direction": "inbound",
                "target_candidates": target_candidates,
                "is_impact_query": False,
                "is_graph_relevant": bool(target_candidates),
            }

        # Identifier Queries
        if query.query_kind in (QueryKind.IDENTIFIER, QueryKind.QUALIFIED_IDENTIFIER):
            return {
                "relationship": "IDENTIFIER",
                "direction": "both",
                "target_candidates": target_candidates,
                "is_impact_query": False,
                "is_graph_relevant": bool(target_candidates),
            }

        # Mixed Queries with target candidates
        if query.query_kind == QueryKind.MIXED and target_candidates:
            return {
                "relationship": "IDENTIFIER",
                "direction": "both",
                "target_candidates": target_candidates,
                "is_impact_query": False,
                "is_graph_relevant": True,
            }

        # Non-graph natural language prose
        return {
            "relationship": None,
            "direction": "none",
            "target_candidates": target_candidates,
            "is_impact_query": False,
            "is_graph_relevant": False,
        }

    def _resolve_target_nodes(
        self,
        repo_graph: CodeGraph | InMemoryGraphStore,
        target_candidates: list[str],
    ) -> list[GraphNode]:
        """Resolve target candidate strings to GraphNode instances in repo_graph."""
        nodes_dict: dict[str, GraphNode] = {}
        if hasattr(repo_graph, "nodes") and isinstance(repo_graph.nodes, dict):
            nodes_dict = repo_graph.nodes
        elif hasattr(repo_graph, "_nodes") and isinstance(repo_graph._nodes, dict):
            nodes_dict = repo_graph._nodes

        resolved: list[GraphNode] = []
        seen_ids: set[str] = set()

        for cand in target_candidates:
            cand_clean = cand.strip()
            if not cand_clean:
                continue

            # 1. Exact match on qualified_name or id
            for node in nodes_dict.values():
                if node.id in seen_ids:
                    continue
                if node.qualified_name == cand_clean or node.id == cand_clean:
                    seen_ids.add(node.id)
                    resolved.append(node)

            # 2. Match on name
            for node in nodes_dict.values():
                if node.id in seen_ids:
                    continue
                if node.name == cand_clean:
                    seen_ids.add(node.id)
                    resolved.append(node)

            # 3. Match suffix of qualified_name
            for node in nodes_dict.values():
                if node.id in seen_ids:
                    continue
                if node.qualified_name and (
                    node.qualified_name.endswith("." + cand_clean)
                    or node.qualified_name.endswith(":" + cand_clean)
                ):
                    seen_ids.add(node.id)
                    resolved.append(node)

        return resolved

    def _map_node_to_retrieval_result(
        self,
        node: GraphNode,
        repository_id: str,
        score: float,
        rank: int,
        graph_relationship: str,
        graph_direction: str,
        graph_depth: int,
    ) -> RetrievalResult:
        """Map a Phase 3 GraphNode to a Phase 5 RetrievalResult."""
        chunk = self.chunk_lookup.get(node.id)
        if chunk is not None:
            meta = dict(chunk.metadata)
            meta["graph_relationship"] = graph_relationship
            meta["graph_direction"] = graph_direction
            meta["graph_depth"] = graph_depth

            return RetrievalResult(
                chunk_id=chunk.id,
                score=score,
                rank=rank,
                repository_id=chunk.repository_id or repository_id,
                commit_id=chunk.commit_id,
                commit_sha=chunk.commit_sha,
                file_path=chunk.file_path,
                language=chunk.language,
                chunk_type=chunk.chunk_type,
                symbol_name=chunk.symbol_name or node.name,
                qualified_name=chunk.qualified_name or node.qualified_name,
                start_line=chunk.source_location.start_line if chunk.source_location else None,
                end_line=chunk.source_location.end_line if chunk.source_location else None,
                metadata=meta,
            )

        # Direct node extraction when CodeChunk object is not registered
        node_file = (
            node.attributes.get("path")
            or node.attributes.get("file_path")
            or node.file_id
            or "unknown/file"
        )
        node_lang = Language.PYTHON
        if node.language:
            try:
                lang_str = str(node.language).lower()
                node_lang = Language(lang_str)
            except ValueError:
                node_lang = Language.PYTHON

        meta = dict(node.attributes)
        meta["graph_relationship"] = graph_relationship
        meta["graph_direction"] = graph_direction
        meta["graph_depth"] = graph_depth

        start_l = node.location.start_line if node.location else None
        end_l = node.location.end_line if node.location else None

        return RetrievalResult(
            chunk_id=node.id,
            score=score,
            rank=rank,
            repository_id=repository_id,
            commit_id=node.attributes.get("commit_id"),
            commit_sha=node.attributes.get("commit_sha"),
            file_path=node_file,
            language=node_lang,
            chunk_type=_node_kind_to_chunk_type(node.kind),
            symbol_name=node.name,
            qualified_name=node.qualified_name,
            start_line=start_l,
            end_line=end_l,
            metadata=meta,
        )
