"""Dependency-Aware Invalidation for Phase 8D."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from backend.git.models import ChangedSymbolResult  # noqa: TC001
from graph.enums import EdgeKind  # noqa: TC001
from graph.impact_analyzer import ImpactAnalyzer

if TYPE_CHECKING:
    from graph.models import CodeGraph


class AffectedSymbol(BaseModel):
    """Represents a symbol that is affected by a dependency change."""

    model_config = ConfigDict(frozen=True)

    symbol_id: str
    file_path: str
    minimum_depth: int
    relationship_types: list[EdgeKind]


class AffectedFile(BaseModel):
    """Represents a file containing one or more dependency-affected symbols."""

    model_config = ConfigDict(frozen=True)

    file_path: str
    affected_symbols: list[str]


class DependencyInvalidationResult(BaseModel):
    """Result of dependency-aware semantic invalidation."""

    model_config = ConfigDict(frozen=True)

    repository_id: str
    base_commit: str
    target_commit: str
    directly_changed_symbols: list[str] = Field(default_factory=list)
    dependency_affected_symbols: list[AffectedSymbol] = Field(default_factory=list)
    affected_files: list[AffectedFile] = Field(default_factory=list)
    maximum_depth: int | None = None


class DependencyInvalidator:
    """Determines the closure of dependency-affected symbols based on direct changes."""

    def __init__(self, impact_analyzer: ImpactAnalyzer | None = None) -> None:
        self.impact_analyzer = impact_analyzer or ImpactAnalyzer()

    def invalidate(
        self,
        changed_result: ChangedSymbolResult,
        graph: CodeGraph,
        max_depth: int | None = None,
    ) -> DependencyInvalidationResult:
        """Compute dependency-affected targets without treating them as direct modifications."""

        # 1. Identify directly changed symbols (taking precedence)
        direct_symbols = set()
        for sym in changed_result.changed_symbols:
            # Added/modified/deleted symbols are direct changes
            direct_symbols.add(sym.symbol_id)
            if sym.previous_symbol_id:
                direct_symbols.add(sym.previous_symbol_id)

        # We explicitly omit opaque files from generating dependency relationships.
        # Unresolved/ambiguous/parser failures lack exact graph states.

        affected_symbol_map: dict[str, AffectedSymbol] = {}

        # 2. Extract impact for every directly changed symbol
        for root_id in direct_symbols:
            # We use try/except gracefully since deleted nodes or unknown IDs
            # might not perfectly exist in the current historical graph snapshot.
            try:
                impact = self.impact_analyzer.analyze_impact(
                    node_id=root_id, graph=graph, max_depth=max_depth
                )

                for node in impact.impacted_nodes:
                    # Direct changes take precedence over dependency affection.
                    if node.symbol_id in direct_symbols:
                        continue

                    # File paths are crucial for tracking boundaries
                    if not node.file_id:
                        continue

                    # Deduplication & minimum depth tracking across multi-root traversal
                    existing = affected_symbol_map.get(node.symbol_id)

                    combined_rels = set(node.relationship_types)
                    min_depth = node.minimum_depth

                    if existing:
                        combined_rels.update(existing.relationship_types)
                        min_depth = min(existing.minimum_depth, node.minimum_depth)

                    affected_symbol_map[node.symbol_id] = AffectedSymbol(
                        symbol_id=node.symbol_id,
                        file_path=node.file_id,  # Assume node.file_id stores the path in GraphNode for now
                        minimum_depth=min_depth,
                        relationship_types=sorted(combined_rels, key=lambda k: k.value),
                    )
            except KeyError:
                # Graph node not found (e.g., deleted symbol not in new graph)
                # Historical state parsing handled passively if the store supports it,
                # otherwise skipped.
                continue

        # 3. File deduplication mapping
        file_map: dict[str, set[str]] = {}
        # Sort symbols for determinism
        sorted_symbols = sorted(affected_symbol_map.values(), key=lambda s: s.symbol_id)

        for aff_sym in sorted_symbols:
            file_map.setdefault(aff_sym.file_path, set()).add(aff_sym.symbol_id)

        affected_files = [
            AffectedFile(file_path=fpath, affected_symbols=sorted(syms))
            for fpath, syms in sorted(file_map.items())
        ]

        return DependencyInvalidationResult(
            repository_id=changed_result.repository_path,
            base_commit=changed_result.base_commit,
            target_commit=changed_result.target_commit,
            directly_changed_symbols=sorted(direct_symbols),
            dependency_affected_symbols=sorted_symbols,
            affected_files=affected_files,
            maximum_depth=max_depth,
        )
