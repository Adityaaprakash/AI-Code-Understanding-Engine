# backend/services/graph_service.py
"""Application service coordinating Phase 3 Graph Engine and Impact Analyzer."""

from backend.schemas.graph import (
    GraphEdgeSchema,
    GraphTraversalResponse,
    ImpactAnalysisResponse,
    ImpactNodeSchema,
    SymbolResponseItem,
)
from graph.impact_analyzer import ImpactAnalyzer
from graph.query_engine import GraphQueryEngine
from graph.store import InMemoryGraphStore


class GraphApplicationService:
    """Coordinates the structural traversal and impact APIs."""

    def __init__(self) -> None:
        self.store = InMemoryGraphStore()
        self.query_engine = GraphQueryEngine()
        self.impact_analyzer = ImpactAnalyzer(self.query_engine)

    def search_symbols(self, query: str, repository_id: str) -> list[SymbolResponseItem]:
        results = []
        for node in self.store._nodes.values():
            if getattr(node, "repository_id", repository_id) == repository_id:
                if (node.name and query.lower() in node.name.lower()) or (
                    node.qualified_name and query.lower() in node.qualified_name.lower()
                ):
                    loc = getattr(node, "location", None)
                    lang_obj = getattr(node, "language", None)

                    results.append(
                        SymbolResponseItem(
                            node_id=node.id,
                            name=node.name or "",
                            qualified_name=node.qualified_name or node.name or "",
                            kind=node.kind.value if hasattr(node.kind, "value") else str(node.kind),
                            file_path=getattr(node, "file_path", getattr(node, "file_id", None)),
                            start_line=loc.start_line if loc is not None else None,
                            end_line=loc.end_line if loc is not None else None,
                            language=getattr(lang_obj, "value", None)
                            if lang_obj is not None
                            else None,
                        )
                    )
        return results

    def traverse(self, source_node_id: str, depth: int) -> GraphTraversalResponse:
        nodes = self.query_engine.traverse(source_node_id, self.store, max_depth=depth)

        visited_ids = {source_node_id}
        node_items = []
        edge_items = []

        for n in nodes:
            visited_ids.add(n.id)
            loc = getattr(n, "location", None)
            lang_obj = getattr(n, "language", None)

            node_items.append(
                SymbolResponseItem(
                    node_id=n.id,
                    name=n.name or "",
                    qualified_name=n.qualified_name or n.name or "",
                    kind=n.kind.value if hasattr(n.kind, "value") else str(n.kind),
                    file_path=getattr(n, "file_path", getattr(n, "file_id", None)),
                    start_line=loc.start_line if loc is not None else None,
                    end_line=loc.end_line if loc is not None else None,
                    language=getattr(lang_obj, "value", None) if lang_obj is not None else None,
                )
            )

        for n_id in visited_ids:
            outbound = self.query_engine.get_outbound_edges(n_id, self.store)
            for e in outbound:
                if e.target_id in visited_ids:
                    edge_items.append(
                        GraphEdgeSchema(
                            source_id=e.source_id,
                            target_id=e.target_id,
                            kind=e.kind.value if hasattr(e.kind, "value") else str(e.kind),
                        )
                    )

        return GraphTraversalResponse(
            source_node_id=source_node_id, depth=depth, nodes=node_items, edges=edge_items
        )

    def analyze_impact(self, source_node_id: str, depth: int) -> ImpactAnalysisResponse:
        result = self.impact_analyzer.analyze_impact(source_node_id, self.store, max_depth=depth)

        impacted = []
        for n in result.impacted_nodes:
            loc = getattr(n, "location", None)

            impacted.append(
                ImpactNodeSchema(
                    node_id=n.symbol_id,
                    name=n.name or "",
                    qualified_name=n.qualified_name or n.name or "",
                    kind=n.node_kind.value if hasattr(n.node_kind, "value") else str(n.node_kind),
                    file_path=getattr(n, "file_path", getattr(n, "file_id", None)),
                    start_line=loc.start_line if loc is not None else None,
                    end_line=loc.end_line if loc is not None else None,
                    language=None,  # Not present in Phase 3 ImpactedNode
                    impact_score=1.0 / n.minimum_depth if n.minimum_depth > 0 else 1.0,
                    categories=[
                        c.value if hasattr(c, "value") else str(c) for c in n.relationship_types
                    ],
                )
            )

        return ImpactAnalysisResponse(
            source_node_id=source_node_id,
            depth=depth,
            impacted_nodes=impacted,
            total_impact_score=float(len(impacted)),
        )


graph_service = GraphApplicationService()
