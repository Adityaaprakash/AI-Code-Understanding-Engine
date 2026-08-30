"""Relationship extraction engine for the CodeLens AI engine (Task 3D).

Converts Canonical Code IR entities and resolved references into directed
semantic graph relationships (GraphEdge) and nodes (GraphNode) for the Code Knowledge Graph.

Pipeline:
    Canonical IR + Resolution Results
        ↓
    RelationshipExtractor
        ↓
    GraphNode list + GraphEdge list
        ↓
    CodeGraph container
"""

from typing import Any

from code_analyzer.ir import (
    Class,
    EntityKind,
    File,
    Function,
    Interface,
    IREntity,
    Method,
    Module,
    Reference,
    ReferenceKind,
    Variable,
)
from code_analyzer.normalization.result import NormalizationResult
from code_analyzer.resolution.context import ResolutionContext
from code_analyzer.resolution.reference_resolver import ReferenceResolver
from code_analyzer.resolution.result import ResolutionResult, ResolutionStatus
from code_analyzer.resolution.symbol_table import SymbolTable
from graph.contracts import RelationshipExtractorContract
from graph.edges import GraphEdge, generate_edge_id
from graph.enums import EdgeKind
from graph.enums import ResolutionStatus as GraphResolutionStatus
from graph.nodes import GraphNode


class RelationshipExtractor(RelationshipExtractorContract):
    """Extracts structural and semantic relationships from Canonical Code IR and resolved references.

    Translates resolved IR references and parent-child structural declarations
    into immutable GraphEdge objects conforming to the Code Knowledge Graph schema.
    """

    def __init__(self, reference_resolver: ReferenceResolver | None = None) -> None:
        """Initialize RelationshipExtractor.

        Args:
            reference_resolver: Optional ReferenceResolver instance. If omitted,
                a default instance will be used when resolving references on the fly.
        """
        self.resolver = reference_resolver or ReferenceResolver()

    def extract_relationships(self, ir_file: File) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Extract nodes and edges from a parsed IR file entity (Contract Implementation).

        Args:
            ir_file: Parsed IR file entity.

        Returns:
            Tuple of extracted GraphNode list and GraphEdge list.
        """
        nodes: list[GraphNode] = [GraphNode.from_ir_entity(ir_file)]
        edges: list[GraphEdge] = []

        # If the file entity includes references, process them
        refs: list[Reference] = getattr(ir_file, "references", [])
        for ref in refs:
            if ref.target_symbol_id:
                edge = self._create_edge_from_reference(
                    ref=ref,
                    status=ResolutionStatus.RESOLVED,
                    target_symbol_id=ref.target_symbol_id,
                    confidence=ref.confidence,
                    repository_id=ir_file.repository_id,
                )
                if edge:
                    edges.append(edge)

        return sorted(nodes, key=lambda n: n.id), sorted(
            edges, key=lambda e: (e.kind.value, e.source_id, e.target_id, e.id)
        )

    def extract_from_normalization_result(
        self,
        norm_result: NormalizationResult,
        symbol_table: SymbolTable,
        resolution_context: ResolutionContext | None = None,
        resolution_results: dict[str, ResolutionResult] | None = None,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Extract all graph nodes and edges from a Phase 2 NormalizationResult.

        Args:
            norm_result: NormalizationResult containing IR entities and references for a file.
            symbol_table: Indexed SymbolTable for candidate symbol metadata lookups.
            resolution_context: Context for resolving references if results are omitted.
            resolution_results: Optional pre-resolved mapping of reference_id -> ResolutionResult.

        Returns:
            Tuple of (nodes, edges) sorted deterministically.
        """
        repository_id = norm_result.file.repository_id
        nodes_dict: dict[str, GraphNode] = {}
        edges_dict: dict[str, GraphEdge] = {}

        # 1. Extract GraphNodes for all IR entities declared in this file
        all_entities: list[IREntity] = [
            norm_result.file,
            *norm_result.classes,
            *norm_result.interfaces,
            *norm_result.functions,
            *norm_result.methods,
            *norm_result.variables,
            *norm_result.parameters,
            *norm_result.modules,
        ]

        for entity in all_entities:
            nodes_dict[entity.id] = GraphNode.from_ir_entity(entity)

        # 2. Extract structural DECLARES edges (File -> Class, Class -> Method, Method -> Parameter, etc.)
        self._extract_structural_declares(all_entities, repository_id, edges_dict)

        # 3. Extract type-level USES / EXTENDS / IMPLEMENTS edges from entity signatures
        self._extract_entity_type_relationships(
            all_entities, symbol_table, repository_id, edges_dict
        )

        # 4. Resolve and extract edges for all explicit References in the file
        if norm_result.references:
            # Build or use resolution context if needed
            ctx = resolution_context or ResolutionContext(
                repository_id=repository_id,
                file_id=norm_result.file.id,
                file_path=norm_result.file.path,
                language=norm_result.file.language,
                symbol_table=symbol_table,
            )

            # Pre-resolve references if not provided
            res_map = resolution_results or self.resolver.resolve_all(norm_result.references, ctx)

            for ref in norm_result.references:
                res_result = res_map.get(ref.id)
                if res_result is None:
                    # Fallback to direct resolution
                    res_result = self.resolver.resolve(ref, ctx)

                # STAGE 4 FILTER: Only RESOLVED references create definitive graph edges
                if res_result.status != ResolutionStatus.RESOLVED:
                    continue
                if not res_result.target_symbol_id:
                    continue

                edge = self._create_edge_from_reference(
                    ref=ref,
                    status=res_result.status,
                    target_symbol_id=res_result.target_symbol_id,
                    confidence=res_result.confidence,
                    repository_id=repository_id,
                    symbol_table=symbol_table,
                )
                if edge:
                    edges_dict[edge.id] = edge

        # Sort nodes and edges deterministically
        sorted_nodes = sorted(nodes_dict.values(), key=lambda n: n.id)
        sorted_edges = sorted(
            edges_dict.values(),
            key=lambda e: (e.kind.value, e.source_id, e.target_id, e.id),
        )

        return sorted_nodes, sorted_edges

    def extract_repository_relationships(
        self,
        norm_results: list[NormalizationResult],
        symbol_table: SymbolTable,
        repository_id: str,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Extract all graph nodes and edges across an entire multi-file repository.

        Args:
            norm_results: List of NormalizationResult objects for all indexed files.
            symbol_table: Populate repository SymbolTable.
            repository_id: Target repository UUID string.

        Returns:
            Tuple of (aggregated_nodes, aggregated_edges) sorted deterministically.
        """
        all_nodes_dict: dict[str, GraphNode] = {}
        all_edges_dict: dict[str, GraphEdge] = {}

        for norm in norm_results:
            ctx = ResolutionContext(
                repository_id=repository_id,
                file_id=norm.file.id,
                file_path=norm.file.path,
                language=norm.file.language,
                symbol_table=symbol_table,
            )
            nodes, edges = self.extract_from_normalization_result(
                norm_result=norm,
                symbol_table=symbol_table,
                resolution_context=ctx,
            )
            for n in nodes:
                all_nodes_dict[n.id] = n
            for e in edges:
                all_edges_dict[e.id] = e

        sorted_nodes = sorted(all_nodes_dict.values(), key=lambda n: n.id)
        sorted_edges = sorted(
            all_edges_dict.values(),
            key=lambda e: (e.kind.value, e.source_id, e.target_id, e.id),
        )

        return sorted_nodes, sorted_edges

    # ──────────────────────────────────────────────────────────────────────────
    # Internal Classification & Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _create_edge_from_reference(
        self,
        ref: Reference,
        status: ResolutionStatus,
        target_symbol_id: str,
        confidence: float,
        repository_id: str | None = None,
        symbol_table: SymbolTable | None = None,
    ) -> GraphEdge | None:
        """Classify a resolved Reference into a GraphEdge."""
        if status != ResolutionStatus.RESOLVED or not target_symbol_id:
            return None

        source_id = ref.source_symbol_id or ref.source_file_id or ref.id
        target_id = target_symbol_id

        # Determine semantic edge kind
        edge_kind = self._classify_reference_kind(ref, target_symbol_id, symbol_table)

        source_line = ref.source_location.start_line if ref.source_location else None
        edge_id = generate_edge_id(
            source_id=source_id,
            target_id=target_id,
            kind=edge_kind,
            source_line=source_line,
        )

        attributes: dict[str, Any] = {
            "target_qualified_name": ref.target_qualified_name,
            "reference_id": ref.id,
        }
        if repository_id:
            attributes["repository_id"] = repository_id
        if ref.metadata:
            attributes.update(ref.metadata)

        # Map ResolutionStatus to GraphResolutionStatus enum
        graph_status = GraphResolutionStatus(status.value)

        return GraphEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            kind=edge_kind,
            resolution_status=graph_status,
            confidence=confidence,
            source_location=ref.source_location,
            attributes=attributes,
        )

    def _classify_reference_kind(
        self,
        ref: Reference,
        target_symbol_id: str,
        symbol_table: SymbolTable | None = None,
    ) -> EdgeKind:
        """Classify reference semantics into EdgeKind enum."""
        # 1. Direct ReferenceKind mappings
        if ref.ref_kind == ReferenceKind.CALL:
            # Check target symbol kind if available in symbol table
            if symbol_table:
                target_entry = symbol_table.lookup_by_id(target_symbol_id)
                if target_entry and target_entry.kind in (
                    EntityKind.CLASS,
                    EntityKind.INTERFACE,
                ):
                    return EdgeKind.USES
            return EdgeKind.CALLS

        if ref.ref_kind == ReferenceKind.IMPORT:
            return EdgeKind.IMPORTS

        if ref.ref_kind == ReferenceKind.EXTENDS:
            return EdgeKind.EXTENDS

        if ref.ref_kind == ReferenceKind.IMPLEMENTS:
            return EdgeKind.IMPLEMENTS

        if ref.ref_kind == ReferenceKind.TYPE_USAGE:
            return EdgeKind.USES

        if ref.ref_kind == ReferenceKind.OVERRIDE:
            return EdgeKind.OVERRIDES

        if ref.ref_kind == ReferenceKind.FIELD_ACCESS:
            return EdgeKind.FIELD_ACCESS

        if ref.ref_kind == ReferenceKind.VARIABLE_USAGE:
            return EdgeKind.READS

        return EdgeKind.REFERENCES

    def _extract_structural_declares(
        self,
        all_entities: list[IREntity],
        repository_id: str,
        edges_dict: dict[str, GraphEdge],
    ) -> None:
        """Extract structural DECLARES edges from parent-child entity ownership."""
        for entity in all_entities:
            parent_id = entity.id

            child_ids: list[str] = []

            if isinstance(entity, File):
                child_ids.extend(entity.symbol_ids)
                child_ids.extend(entity.module_ids)
            elif isinstance(entity, Module):
                child_ids.extend(entity.exported_symbol_ids)
            elif isinstance(entity, (Class, Interface)):
                child_ids.extend(entity.method_ids)
                child_ids.extend(entity.field_ids)
            elif isinstance(entity, (Function, Method)):
                for p in entity.parameters:
                    child_ids.append(p.id)
            elif isinstance(entity, Variable):
                pass

            for child_id in child_ids:
                if not child_id:
                    continue
                edge_id = generate_edge_id(
                    source_id=parent_id,
                    target_id=child_id,
                    kind=EdgeKind.DECLARES,
                )
                edges_dict[edge_id] = GraphEdge(
                    id=edge_id,
                    source_id=parent_id,
                    target_id=child_id,
                    kind=EdgeKind.DECLARES,
                    resolution_status=GraphResolutionStatus.RESOLVED,
                    confidence=1.0,
                    source_location=getattr(entity, "location", None),
                    attributes={"repository_id": repository_id},
                )

    def _extract_entity_type_relationships(
        self,
        all_entities: list[IREntity],
        symbol_table: SymbolTable,
        repository_id: str,
        edges_dict: dict[str, GraphEdge],
    ) -> None:
        """Extract USES, EXTENDS, and IMPLEMENTS edges from entity signatures."""
        for entity in all_entities:
            # A. Variable/Field declared_type -> USES edge
            if isinstance(entity, Variable) and entity.declared_type:
                type_name = str(entity.declared_type).strip()
                matches = symbol_table.lookup_by_simple_name(
                    type_name, repository_id
                ) or symbol_table.lookup_by_qualified_name(type_name, repository_id)
                if matches:
                    target_id = matches[0].symbol_id
                    source_id = entity.parent_id or entity.id
                    edge_id = generate_edge_id(
                        source_id=source_id,
                        target_id=target_id,
                        kind=EdgeKind.USES,
                    )
                    edges_dict[edge_id] = GraphEdge(
                        id=edge_id,
                        source_id=source_id,
                        target_id=target_id,
                        kind=EdgeKind.USES,
                        resolution_status=GraphResolutionStatus.RESOLVED,
                        confidence=0.9,
                        source_location=entity.location,
                        attributes={
                            "repository_id": repository_id,
                            "context": "declared_type",
                        },
                    )

            # B. Method/Function return_type or parameter types -> USES edge
            elif isinstance(entity, (Function, Method)):
                if entity.return_type:
                    ret_str = str(entity.return_type).strip()
                    matches = symbol_table.lookup_by_simple_name(
                        ret_str, repository_id
                    ) or symbol_table.lookup_by_qualified_name(ret_str, repository_id)
                    if matches:
                        target_id = matches[0].symbol_id
                        edge_id = generate_edge_id(
                            source_id=entity.id,
                            target_id=target_id,
                            kind=EdgeKind.USES,
                        )
                        edges_dict[edge_id] = GraphEdge(
                            id=edge_id,
                            source_id=entity.id,
                            target_id=target_id,
                            kind=EdgeKind.USES,
                            resolution_status=GraphResolutionStatus.RESOLVED,
                            confidence=0.9,
                            source_location=entity.location,
                            attributes={
                                "repository_id": repository_id,
                                "context": "return_type",
                            },
                        )

                for param in entity.parameters:
                    if param.declared_type:
                        p_type = str(param.declared_type).strip()
                        matches = symbol_table.lookup_by_simple_name(
                            p_type, repository_id
                        ) or symbol_table.lookup_by_qualified_name(p_type, repository_id)
                        if matches:
                            target_id = matches[0].symbol_id
                            edge_id = generate_edge_id(
                                source_id=entity.id,
                                target_id=target_id,
                                kind=EdgeKind.USES,
                            )
                            edges_dict[edge_id] = GraphEdge(
                                id=edge_id,
                                source_id=entity.id,
                                target_id=target_id,
                                kind=EdgeKind.USES,
                                resolution_status=GraphResolutionStatus.RESOLVED,
                                confidence=0.9,
                                source_location=param.location,
                                attributes={
                                    "repository_id": repository_id,
                                    "context": "parameter_type",
                                },
                            )
