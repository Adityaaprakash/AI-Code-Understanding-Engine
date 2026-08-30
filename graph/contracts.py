"""Abstract base class contracts and interfaces for Phase 3 Code Knowledge Graph components."""

from abc import ABC, abstractmethod
from typing import Any

from code_analyzer.ir import File, IREntity, Reference
from graph.edges import GraphEdge
from graph.models import CodeGraph
from graph.nodes import GraphNode


class SymbolRegistrarContract(ABC):
    """Contract for symbol registration and symbol table lookup (Task 3B)."""

    @abstractmethod
    def register_symbols(self, repository_id: str, ir_file: File) -> list[GraphNode]:
        """Register all declared symbols from a parsed IR file into the symbol index.

        Args:
            repository_id: Target repository UUID.
            ir_file: Parsed IR file entity.

        Returns:
            List of registered symbol GraphNode instances.
        """
        raise NotImplementedError

    @abstractmethod
    def lookup_symbol(
        self, qualified_name: str, repository_id: str | None = None
    ) -> list[GraphNode]:
        """Lookup graph symbol nodes by qualified name.

        Args:
            qualified_name: Fully qualified symbol name string.
            repository_id: Optional repository filter.

        Returns:
            List of matching GraphNode instances.
        """
        raise NotImplementedError


class ImportResolverContract(ABC):
    """Contract for resolving file and module import statements (Task 3C)."""

    @abstractmethod
    def resolve_imports(self, ir_file: File, graph: CodeGraph) -> list[GraphEdge]:
        """Resolve import statements within an IR file into graph import edges.

        Args:
            ir_file: Parsed IR file entity containing import references.
            graph: Existing CodeGraph snapshot.

        Returns:
            List of resolved import GraphEdge instances.
        """
        raise NotImplementedError


class ReferenceResolverContract(ABC):
    """Contract for resolving symbol call-site and type use-site references (Task 3D)."""

    @abstractmethod
    def resolve_reference(self, reference: Reference, graph: CodeGraph) -> GraphEdge:
        """Resolve a single IR Reference to a target symbol node in the graph.

        Args:
            reference: IR Reference entity.
            graph: Existing CodeGraph snapshot.

        Returns:
            GraphEdge representing the resolved (or unresolved) relationship.
        """
        raise NotImplementedError


class RelationshipExtractorContract(ABC):
    """Contract for extracting structural and semantic relationships from IR (Task 3F)."""

    @abstractmethod
    def extract_relationships(self, ir_file: File) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Extract nodes and edges from a parsed IR file entity.

        Args:
            ir_file: Parsed IR file entity.

        Returns:
            Tuple of extracted GraphNode list and GraphEdge list.
        """
        raise NotImplementedError


class GraphBuilderContract(ABC):
    """Contract for constructing complete CodeGraph derived from Canonical Code IR."""

    @abstractmethod
    def build_graph(self, repository_id: str, ir_entities: list[IREntity]) -> CodeGraph:
        """Build a CodeGraph instance from a collection of Canonical Code IR entities.

        Args:
            repository_id: Repository ID.
            ir_entities: Collection of IR entities (Files, Classes, Functions, etc.).

        Returns:
            Constructed CodeGraph container.
        """
        raise NotImplementedError


class GraphStoreContract(ABC):
    """Contract for graph storage, persistence, and persistence queries (Task 3E)."""

    @abstractmethod
    async def save_graph(self, graph: CodeGraph) -> None:
        """Save or persist a CodeGraph snapshot to the persistent storage layer.

        Args:
            graph: CodeGraph container instance.
        """
        raise NotImplementedError

    @abstractmethod
    async def load_graph(self, repository_id: str) -> CodeGraph:
        """Load a CodeGraph snapshot for a repository from persistent storage.

        Args:
            repository_id: Repository ID.

        Returns:
            Loaded CodeGraph container instance.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_graph(self, repository_id: str) -> None:
        """Delete all graph nodes and edges for a repository from persistent storage.

        Args:
            repository_id: Repository ID.
        """
        raise NotImplementedError


class GraphQueryEngineContract(ABC):
    """Contract for graph traversal, dependency analysis, and impact analysis (Task 3G)."""

    @abstractmethod
    def get_callers(self, symbol_id: str, graph: CodeGraph) -> list[GraphNode]:
        """Retrieve all nodes that call the specified target symbol node.

        Args:
            symbol_id: Target symbol node ID.
            graph: CodeGraph instance.

        Returns:
            List of caller GraphNode instances.
        """
        raise NotImplementedError

    @abstractmethod
    def get_callees(self, symbol_id: str, graph: CodeGraph) -> list[GraphNode]:
        """Retrieve all nodes called by the specified source symbol node.

        Args:
            symbol_id: Source symbol node ID.
            graph: CodeGraph instance.

        Returns:
            List of callee GraphNode instances.
        """
        raise NotImplementedError

    @abstractmethod
    def get_dependencies(
        self, node_id: str, graph: CodeGraph, max_depth: int = 1
    ) -> list[GraphNode]:
        """Retrieve dependency closure for a given graph node up to max_depth.

        Args:
            node_id: Root node ID.
            graph: CodeGraph instance.
            max_depth: Traversal depth limit.

        Returns:
            List of dependent GraphNode instances.
        """
        raise NotImplementedError

    @abstractmethod
    def get_impact_radius(
        self, node_id: str, graph: CodeGraph, max_depth: int = 5
    ) -> list[GraphNode]:
        """Compute blast radius / reverse impact analysis for a node modification up to max_depth.

        Args:
            node_id: Modified node ID.
            graph: CodeGraph instance.
            max_depth: Traversal depth limit.

        Returns:
            List of impacted GraphNode instances.
        """
        raise NotImplementedError


class ImpactAnalyzerContract(ABC):
    """Contract for deterministic, graph-based initial impact analysis (Task 3H)."""

    @abstractmethod
    def analyze_impact(
        self,
        node_id: str,
        graph: Any,
        max_depth: int | None = None,
        edge_kinds: set[Any] | list[Any] | None = None,
    ) -> Any:
        """Compute structured impact analysis result for a modified symbol node.

        Args:
            node_id: Target/root node ID being modified.
            graph: CodeGraph container or InMemoryGraphStore.
            max_depth: Traversal depth limit (1 = direct dependents, None = unlimited).
            edge_kinds: Optional custom edge kinds filter. Defaults to DEPENDENCY_EDGE_KINDS.

        Returns:
            ImpactAnalysisResult containing root metadata, impacted nodes, paths, and depth info.

        Raises:
            KeyError: If node_id is not found in graph.
        """
        raise NotImplementedError

