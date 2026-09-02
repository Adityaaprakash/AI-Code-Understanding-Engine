"""Graph-Aware Context Expansion engine implementation for TASK-6B."""

from __future__ import annotations

import time
from collections import deque
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

    from llm.planner_models import QueryPlan

from graph.enums import EdgeKind
from graph.impact_analyzer import ImpactAnalyzer
from graph.query_engine import DEPENDENCY_EDGE_KINDS
from llm.enums import GraphStrategy, QueryScope, RelationshipType
from llm.expansion_config import GraphExpansionConfig
from llm.expansion_contracts import GraphExpanderContract
from llm.expansion_models import (
    GraphExpansionAnchor,
    GraphExpansionCandidate,
    GraphExpansionCandidatePath,
    GraphExpansionCandidateStep,
    GraphExpansionResult,
)
from retrieval.retrieval_models import RetrievalResult, RetrievalResultSet


def _get_node(graph: Any, node_id: str) -> Any | None:
    """Retrieve node from CodeGraph or InMemoryGraphStore safely."""
    if graph is None:
        return None
    if hasattr(graph, "get_node"):
        res: Any = graph.get_node(node_id)
        return res
    if hasattr(graph, "nodes") and isinstance(graph.nodes, dict):
        return graph.nodes.get(node_id)
    if hasattr(graph, "_nodes") and isinstance(graph._nodes, dict):
        return graph._nodes.get(node_id)
    return None


def _get_outbound_edges(graph: Any, source_id: str, kind: EdgeKind | None = None) -> list[Any]:
    """Retrieve outbound edges from graph safely."""
    if graph is None:
        return []
    if hasattr(graph, "get_outbound_edges"):
        out_edges: list[Any] = graph.get_outbound_edges(source_id, kind=kind)
        return out_edges
    if hasattr(graph, "edges") and isinstance(graph.edges, dict):
        edges = [e for e in graph.edges.values() if getattr(e, "source_id", None) == source_id]
        if kind is not None:
            edges = [e for e in edges if getattr(e, "kind", None) == kind]
        return edges
    return []


def _get_inbound_edges(graph: Any, target_id: str, kind: EdgeKind | None = None) -> list[Any]:
    """Retrieve inbound edges from graph safely."""
    if graph is None:
        return []
    if hasattr(graph, "get_inbound_edges"):
        in_edges: list[Any] = graph.get_inbound_edges(target_id, kind=kind)
        return in_edges
    if hasattr(graph, "edges") and isinstance(graph.edges, dict):
        edges = [e for e in graph.edges.values() if getattr(e, "target_id", None) == target_id]
        if kind is not None:
            edges = [e for e in edges if getattr(e, "kind", None) == kind]
        return edges
    return []


def _lookup_node_by_symbol(graph: Any, symbol: str) -> Any | None:
    """Lookup a graph node matching symbol string by qualified_name or name."""
    if not symbol or not graph:
        return None
    if hasattr(graph, "lookup_symbol"):
        matches: list[Any] = graph.lookup_symbol(symbol)
        if matches:
            res: Any = matches[0]
            return res
    # Fallback node collection search
    nodes: Iterable[Any] = []
    if hasattr(graph, "nodes") and isinstance(graph.nodes, dict):
        nodes = graph.nodes.values()
    elif hasattr(graph, "_nodes") and isinstance(graph._nodes, dict):
        nodes = graph._nodes.values()

    sym_clean = symbol.strip().lower()
    for n in nodes:
        qname = getattr(n, "qualified_name", None)
        name = getattr(n, "name", None)
        nid = getattr(n, "id", None)
        if qname and qname.lower() == sym_clean:
            node_res: Any = n
            return node_res
        if name and name.lower() == sym_clean:
            node_res = n
            return node_res
        if nid and nid.lower() == sym_clean:
            node_res = n
            return node_res
    return None


class GraphContextExpander(GraphExpanderContract):
    """Production implementation of Graph-Aware Context Expansion (TASK-6B).

    Translates QueryPlan signals and Phase 5 retrieval result anchors into intent-aware,
    bounded, deterministic graph expansions over the Phase 3 Code Knowledge Graph.
    """

    def expand(
        self,
        query_plan: QueryPlan,
        retrieval_results: RetrievalResultSet | list[RetrievalResult] | None,
        graph: Any,
        config: GraphExpansionConfig | None = None,
    ) -> GraphExpansionResult:
        """Perform bounded, intent-guided graph context expansion."""
        start_time = time.perf_counter()
        effective_config = config or GraphExpansionConfig()

        effective_strategy = effective_config.graph_strategy_override or query_plan.graph_strategy

        # 1. No-op check: GraphStrategy.NONE
        if effective_strategy == GraphStrategy.NONE:
            return GraphExpansionResult(
                candidates=[],
                anchors=[],
                expanded_node_count=0,
                max_depth_reached=0,
                truncated=False,
                expansion_metadata={
                    "reason": "GRAPH_STRATEGY_NONE",
                    "latency_ms": (time.perf_counter() - start_time) * 1000.0,
                },
            )

        # 2. Extract anchors from retrieval results or query plan entities
        anchors, retrieval_map = self._extract_anchors(query_plan, retrieval_results, graph)
        if not anchors or graph is None:
            return GraphExpansionResult(
                candidates=[],
                anchors=anchors,
                expanded_node_count=0,
                max_depth_reached=0,
                truncated=False,
                expansion_metadata={
                    "reason": "NO_GRAPH_ANCHORS",
                    "latency_ms": (time.perf_counter() - start_time) * 1000.0,
                },
            )

        # 3. Resolve expansion traversal specifications
        specs = self._resolve_expansion_specs(query_plan, effective_strategy, effective_config)

        # 4. Handle IMPACT strategy specifically via ImpactAnalyzer if requested
        if (
            effective_strategy == GraphStrategy.IMPACT_RADIUS
            or query_plan.relationship_type == RelationshipType.IMPACT
        ):
            return self._expand_impact(
                anchors=anchors,
                graph=graph,
                query_plan=query_plan,
                config=effective_config,
                retrieval_map=retrieval_map,
                start_time=start_time,
            )

        # 5. General BFS Traversal over resolved specs
        candidates, expanded_count, max_depth, truncated = self._traverse_bfs(
            anchors=anchors,
            graph=graph,
            query_plan=query_plan,
            specs=specs,
            config=effective_config,
            retrieval_map=retrieval_map,
        )

        # Sort candidates deterministically
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (
                c.traversal_depth,
                c.relationship_type.value,
                c.node_kind,
                c.qualified_name or "",
                c.candidate_id,
            ),
        )

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return GraphExpansionResult(
            candidates=sorted_candidates,
            anchors=anchors,
            expanded_node_count=expanded_count,
            max_depth_reached=max_depth,
            truncated=truncated,
            expansion_metadata={
                "strategy": effective_strategy.value,
                "relationship_type": query_plan.relationship_type.value,
                "scope": query_plan.scope.value,
                "anchor_count": len(anchors),
                "candidate_count": len(sorted_candidates),
                "latency_ms": latency_ms,
            },
        )

    def _extract_anchors(
        self,
        query_plan: QueryPlan,
        retrieval_results: RetrievalResultSet | list[RetrievalResult] | None,
        graph: Any,
    ) -> tuple[list[GraphExpansionAnchor], dict[str, str]]:
        """Extract deduplicated graph expansion anchors and chunk mapping."""
        results: list[RetrievalResult] = []
        if isinstance(retrieval_results, RetrievalResultSet):
            results = retrieval_results.results
        elif isinstance(retrieval_results, list):
            results = retrieval_results

        anchors_dict: dict[str, GraphExpansionAnchor] = {}
        retrieval_map: dict[str, str] = {}  # node_id -> chunk_id

        # A. Extract anchors from Phase 5 retrieval results
        for res in results:
            node_id_candidate = (
                res.metadata.get("symbol_id")
                or res.metadata.get("node_id")
                or res.metadata.get("graph_node_id")
            )
            node = None
            if node_id_candidate:
                node = _get_node(graph, str(node_id_candidate))

            if node is None and res.chunk_id:
                node = _get_node(graph, res.chunk_id)

            if node is None and (res.qualified_name or res.symbol_name):
                node = _lookup_node_by_symbol(graph, res.qualified_name or res.symbol_name or "")

            if node is not None:
                nid = getattr(node, "id", None)
                if nid:
                    retrieval_map[nid] = res.chunk_id
                    if res.qualified_name:
                        retrieval_map[res.qualified_name] = res.chunk_id
                    if nid not in anchors_dict:
                        anchors_dict[nid] = GraphExpansionAnchor(
                            anchor_id=nid,
                            anchor_type="RETRIEVAL_RESULT",
                            symbol_name=getattr(node, "name", None) or res.symbol_name,
                            qualified_name=getattr(node, "qualified_name", None)
                            or res.qualified_name,
                            file_path=getattr(node, "file_id", None) or res.file_path,
                            retrieval_chunk_id=res.chunk_id,
                        )

        # B. Fallback / supplement: target entities from QueryPlan
        target_terms = list(query_plan.target_entities) + list(query_plan.identifiers)
        for term in target_terms:
            node = _lookup_node_by_symbol(graph, term)
            if node is not None:
                nid = getattr(node, "id", None)
                if nid and nid not in anchors_dict:
                    anchors_dict[nid] = GraphExpansionAnchor(
                        anchor_id=nid,
                        anchor_type="TARGET_ENTITY",
                        symbol_name=getattr(node, "name", None) or term,
                        qualified_name=getattr(node, "qualified_name", None),
                        file_path=getattr(node, "file_id", None),
                        retrieval_chunk_id=retrieval_map.get(nid),
                    )

        # Deterministically sort anchors
        sorted_anchors = sorted(
            anchors_dict.values(),
            key=lambda a: (a.anchor_type, a.qualified_name or "", a.anchor_id),
        )
        return sorted_anchors, retrieval_map

    def _resolve_expansion_specs(
        self,
        query_plan: QueryPlan,
        strategy: GraphStrategy,
        config: GraphExpansionConfig,
    ) -> list[tuple[str, set[EdgeKind], RelationshipType]]:
        """Resolve traversal direction, edge kinds, and relationship type for expansion.

        Returns list of (direction, allowed_edge_kinds, primary_relationship_type) tuples.
        """
        specs: list[tuple[str, set[EdgeKind], RelationshipType]] = []

        rel_type = query_plan.relationship_type

        if strategy in (GraphStrategy.CALLERS,) or rel_type == RelationshipType.CALLERS:
            specs.append(("inbound", {EdgeKind.CALLS}, RelationshipType.CALLERS))
        elif strategy in (GraphStrategy.CALLEES,) or rel_type == RelationshipType.CALLS:
            specs.append(("outbound", {EdgeKind.CALLS}, RelationshipType.CALLS))
        elif strategy in (GraphStrategy.DEPENDENTS,) or rel_type == RelationshipType.DEPENDENTS:
            specs.append(("inbound", set(DEPENDENCY_EDGE_KINDS), RelationshipType.DEPENDENTS))
        elif strategy in (GraphStrategy.DEPENDENCIES,) or rel_type == RelationshipType.DEPENDENCIES:
            specs.append(("outbound", set(DEPENDENCY_EDGE_KINDS), RelationshipType.DEPENDENCIES))
        elif (
            strategy in (GraphStrategy.IMPLEMENTATIONS,) or rel_type == RelationshipType.IMPLEMENTS
        ):
            specs.append(("inbound", {EdgeKind.IMPLEMENTS}, RelationshipType.IMPLEMENTS))
            specs.append(("outbound", {EdgeKind.IMPLEMENTS}, RelationshipType.IMPLEMENTS))
        elif strategy in (GraphStrategy.INHERITANCE,) or rel_type == RelationshipType.EXTENDS:
            specs.append(("inbound", {EdgeKind.EXTENDS}, RelationshipType.EXTENDS))
            specs.append(("outbound", {EdgeKind.EXTENDS}, RelationshipType.EXTENDS))
        elif strategy in (GraphStrategy.IMPORTS,) or rel_type == RelationshipType.IMPORTS:
            specs.append(("outbound", {EdgeKind.IMPORTS}, RelationshipType.IMPORTS))
            specs.append(("inbound", {EdgeKind.IMPORTS}, RelationshipType.IMPORTS))
        elif strategy in (GraphStrategy.USAGES,) or rel_type in (
            RelationshipType.USES,
            RelationshipType.REFERENCES,
        ):
            usage_kinds = {
                EdgeKind.USES,
                EdgeKind.REFERENCES,
                EdgeKind.FIELD_ACCESS,
                EdgeKind.READS,
                EdgeKind.WRITES,
                EdgeKind.TYPED_AS,
            }
            specs.append(("inbound", usage_kinds, RelationshipType.USES))
            specs.append(("outbound", usage_kinds, RelationshipType.USES))
        elif strategy == GraphStrategy.ARCHITECTURAL_EXPANSION:
            arch_kinds = {
                EdgeKind.CONTAINS,
                EdgeKind.DECLARES,
                EdgeKind.EXPORTS,
                EdgeKind.IMPORTS,
            } | set(DEPENDENCY_EDGE_KINDS)
            specs.append(("both", arch_kinds, RelationshipType.DEPENDENCIES))
        else:
            # General fallback: bidirectional structural expansion over dependency edge kinds
            specs.append(("outbound", set(DEPENDENCY_EDGE_KINDS), RelationshipType.DEPENDENCIES))
            specs.append(("inbound", set(DEPENDENCY_EDGE_KINDS), RelationshipType.DEPENDENTS))

        # Filter edge kinds if config.allowed_relationship_types is specified
        if config.allowed_relationship_types is not None:
            allowed_rel_set = set(config.allowed_relationship_types)
            filtered_specs: list[tuple[str, set[EdgeKind], RelationshipType]] = []
            for dir_name, kinds, rtype in specs:
                if rtype in allowed_rel_set:
                    filtered_specs.append((dir_name, kinds, rtype))
            specs = filtered_specs if filtered_specs else specs

        return specs

    def _expand_impact(
        self,
        anchors: list[GraphExpansionAnchor],
        graph: Any,
        query_plan: QueryPlan,
        config: GraphExpansionConfig,
        retrieval_map: dict[str, str],
        start_time: float,
    ) -> GraphExpansionResult:
        """Expand context using Phase 3 ImpactAnalyzer semantics for impact queries."""
        analyzer = ImpactAnalyzer()
        candidates_by_id: dict[str, GraphExpansionCandidate] = {}
        total_expanded = 0
        max_depth_reached = 0
        truncated = False

        for anchor in anchors:
            if len(candidates_by_id) >= config.max_candidates:
                truncated = True
                break
            try:
                impact_res = analyzer.analyze_impact(
                    node_id=anchor.anchor_id,
                    graph=graph,
                    max_depth=config.max_depth,
                )
            except KeyError:
                continue

            for node_info in impact_res.impacted_nodes:
                if len(candidates_by_id) >= config.max_candidates:
                    truncated = True
                    break

                total_expanded += 1
                max_depth_reached = max(max_depth_reached, node_info.minimum_depth)

                _get_node(graph, node_info.symbol_id)
                paths = impact_res.get_paths_for_node(node_info.symbol_id)
                path_obj = None
                if paths and config.retain_path_metadata:
                    primary_path = paths[0]
                    steps = [
                        GraphExpansionCandidateStep(
                            source_id=s.source_id,
                            target_id=s.target_id,
                            relationship_type=RelationshipType.IMPACT,
                            edge_kind=s.kind.value,
                        )
                        for s in primary_path.steps
                    ]
                    path_obj = GraphExpansionCandidatePath(
                        anchor_id=anchor.anchor_id,
                        target_node_id=node_info.symbol_id,
                        depth=primary_path.depth,
                        node_ids=primary_path.node_ids,
                        steps=steps,
                    )

                retrieval_chunk_id = retrieval_map.get(node_info.symbol_id)
                if not retrieval_chunk_id and node_info.qualified_name:
                    retrieval_chunk_id = retrieval_map.get(node_info.qualified_name)

                source_str = (
                    "RETRIEVAL+GRAPH_EXPANSION" if retrieval_chunk_id else "GRAPH_EXPANSION"
                )

                candidate_id = f"cand_{anchor.anchor_id}_{node_info.symbol_id}_impact"
                candidate = GraphExpansionCandidate(
                    candidate_id=candidate_id,
                    node_id=node_info.symbol_id,
                    symbol_name=node_info.name,
                    qualified_name=node_info.qualified_name,
                    node_kind=node_info.node_kind.value,
                    file_path=node_info.file_id,
                    start_line=node_info.location.start_line if node_info.location else None,
                    end_line=node_info.location.end_line if node_info.location else None,
                    source=source_str,
                    anchor_id=anchor.anchor_id,
                    relationship_type=RelationshipType.IMPACT,
                    traversal_depth=node_info.minimum_depth,
                    expansion_reason=f"IMPACT_RADIUS_DEPTH_{node_info.minimum_depth}",
                    path=path_obj,
                    retrieval_chunk_id=retrieval_chunk_id,
                )
                if (
                    node_info.symbol_id not in candidates_by_id
                    or node_info.minimum_depth
                    < candidates_by_id[node_info.symbol_id].traversal_depth
                ):
                    candidates_by_id[node_info.symbol_id] = candidate

        sorted_candidates = sorted(
            candidates_by_id.values(),
            key=lambda c: (
                c.traversal_depth,
                c.relationship_type.value,
                c.node_kind,
                c.qualified_name or "",
                c.candidate_id,
            ),
        )

        return GraphExpansionResult(
            candidates=sorted_candidates,
            anchors=anchors,
            expanded_node_count=total_expanded,
            max_depth_reached=max_depth_reached,
            truncated=truncated,
            expansion_metadata={
                "strategy": GraphStrategy.IMPACT_RADIUS.value,
                "anchor_count": len(anchors),
                "candidate_count": len(sorted_candidates),
                "latency_ms": (time.perf_counter() - start_time) * 1000.0,
            },
        )

    def _traverse_bfs(
        self,
        anchors: list[GraphExpansionAnchor],
        graph: Any,
        query_plan: QueryPlan,
        specs: list[tuple[str, set[EdgeKind], RelationshipType]],
        config: GraphExpansionConfig,
        retrieval_map: dict[str, str],
    ) -> tuple[list[GraphExpansionCandidate], int, int, bool]:
        """Perform deterministic BFS graph traversal over specified specs and configuration limits."""
        candidates_by_node_id: dict[str, GraphExpansionCandidate] = {}
        visited_nodes: set[str] = set()

        expanded_node_count = 0
        max_depth_reached = 0
        truncated = False

        # Queue item: (curr_node_id, curr_depth, anchor_id, path_node_ids, path_steps, rel_type)
        queue: deque[
            tuple[
                str,
                int,
                str,
                list[str],
                list[GraphExpansionCandidateStep],
                RelationshipType,
            ]
        ] = deque()

        for anchor in anchors:
            for _, _, rel_type in specs:
                queue.append(
                    (anchor.anchor_id, 0, anchor.anchor_id, [anchor.anchor_id], [], rel_type)
                )

        while queue:
            if (
                expanded_node_count >= config.max_expanded_nodes
                or len(candidates_by_node_id) >= config.max_candidates
            ):
                truncated = True
                break

            curr_node_id, curr_depth, anchor_id, path_nodes, path_steps, _rtype = queue.popleft()

            if curr_depth >= config.max_depth:
                max_depth_reached = max(max_depth_reached, curr_depth)
                continue

            expanded_node_count += 1
            max_depth_reached = max(max_depth_reached, curr_depth)

            curr_node = _get_node(graph, curr_node_id)
            anchor_file_id = getattr(curr_node, "file_id", None)

            for direction, allowed_kinds, spec_rtype in specs:
                if len(candidates_by_node_id) >= config.max_candidates:
                    truncated = True
                    break

                edges: list[Any] = []
                if direction in ("outbound", "both"):
                    edges.extend(_get_outbound_edges(graph, curr_node_id))
                if direction in ("inbound", "both"):
                    edges.extend(_get_inbound_edges(graph, curr_node_id))

                # Filter by allowed EdgeKinds
                valid_edges = [e for e in edges if getattr(e, "kind", None) in allowed_kinds]

                # Deterministically sort edges by (kind, neighbor_id, edge_id)
                sorted_edges = sorted(
                    valid_edges,
                    key=lambda e: (
                        getattr(e.kind, "value", str(e.kind)),
                        e.target_id if direction == "outbound" else e.source_id,
                        getattr(e, "id", ""),
                    ),
                )

                # Per-node neighbor limit
                limited_edges = sorted_edges[: config.max_neighbors_per_node]

                for edge in limited_edges:
                    neighbor_id = (
                        edge.target_id
                        if direction == "outbound" or edge.source_id == curr_node_id
                        else edge.source_id
                    )
                    if neighbor_id == curr_node_id:
                        continue  # Self-loop protection

                    neighbor_node = _get_node(graph, neighbor_id)
                    if neighbor_node is None:
                        continue

                    # Scope handling constraint check
                    if query_plan.scope == QueryScope.FILE:
                        neighbor_file_id = getattr(neighbor_node, "file_id", None)
                        if (
                            anchor_file_id
                            and neighbor_file_id
                            and anchor_file_id != neighbor_file_id
                            and not config.allow_same_file_expansion
                        ):
                            continue

                    edge_kind_str = (
                        edge.kind.value if hasattr(edge.kind, "value") else str(edge.kind)
                    )
                    step = GraphExpansionCandidateStep(
                        source_id=edge.source_id,
                        target_id=edge.target_id,
                        relationship_type=spec_rtype,
                        edge_kind=edge_kind_str,
                    )
                    new_path_nodes = [*path_nodes, neighbor_id]
                    new_path_steps = [*path_steps, step]

                    path_obj = None
                    if config.retain_path_metadata:
                        path_obj = GraphExpansionCandidatePath(
                            anchor_id=anchor_id,
                            target_node_id=neighbor_id,
                            depth=curr_depth + 1,
                            node_ids=new_path_nodes,
                            steps=new_path_steps,
                        )

                    retrieval_chunk_id = retrieval_map.get(neighbor_id)
                    qname = getattr(neighbor_node, "qualified_name", None)
                    if not retrieval_chunk_id and qname:
                        retrieval_chunk_id = retrieval_map.get(qname)

                    source_str = (
                        "RETRIEVAL+GRAPH_EXPANSION" if retrieval_chunk_id else "GRAPH_EXPANSION"
                    )

                    nkind = getattr(neighbor_node, "kind", None)
                    nkind_str = (
                        nkind.value
                        if (nkind is not None and hasattr(nkind, "value"))
                        else str(nkind or "SYMBOL")
                    )
                    location = getattr(neighbor_node, "location", None)

                    cand_id = f"cand_{anchor_id}_{neighbor_id}_{spec_rtype.value}"
                    candidate = GraphExpansionCandidate(
                        candidate_id=cand_id,
                        node_id=neighbor_id,
                        symbol_name=getattr(neighbor_node, "name", None),
                        qualified_name=qname,
                        node_kind=nkind_str,
                        file_path=getattr(neighbor_node, "file_id", None),
                        start_line=getattr(location, "start_line", None),
                        end_line=getattr(location, "end_line", None),
                        source=source_str,
                        anchor_id=anchor_id,
                        relationship_type=spec_rtype,
                        traversal_depth=curr_depth + 1,
                        expansion_reason=f"EXPANDED_{spec_rtype.value.upper()}_DEPTH_{curr_depth + 1}",
                        path=path_obj,
                        retrieval_chunk_id=retrieval_chunk_id,
                    )

                    if neighbor_id not in visited_nodes:
                        if len(candidates_by_node_id) >= config.max_candidates:
                            truncated = True
                            break
                        visited_nodes.add(neighbor_id)
                        candidates_by_node_id[neighbor_id] = candidate
                        queue.append(
                            (
                                neighbor_id,
                                curr_depth + 1,
                                anchor_id,
                                new_path_nodes,
                                new_path_steps,
                                spec_rtype,
                            )
                        )
                    elif neighbor_id in candidates_by_node_id:
                        # Path update if shorter path discovered
                        existing_cand = candidates_by_node_id[neighbor_id]
                        if curr_depth + 1 < existing_cand.traversal_depth:
                            candidates_by_node_id[neighbor_id] = candidate

        return (
            list(candidates_by_node_id.values()),
            expanded_node_count,
            max_depth_reached,
            truncated,
        )
