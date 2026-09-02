"""Abstract base contracts for TASK-6B Graph-Aware Context Expansion."""

from abc import ABC, abstractmethod
from typing import Any

from llm.expansion_config import GraphExpansionConfig
from llm.expansion_models import GraphExpansionResult
from llm.planner_models import QueryPlan
from retrieval.retrieval_models import RetrievalResult, RetrievalResultSet


class GraphExpanderContract(ABC):
    """Contract for intent-aware, bounded, deterministic graph context expansion."""

    @abstractmethod
    def expand(
        self,
        query_plan: QueryPlan,
        retrieval_results: RetrievalResultSet | list[RetrievalResult] | None,
        graph: Any,
        config: GraphExpansionConfig | None = None,
    ) -> GraphExpansionResult:
        """Perform bounded, intent-guided graph context expansion around retrieval anchors.

        Args:
            query_plan: Structured QueryPlan from Phase 6A.
            retrieval_results: Phase 5 RetrievalResultSet or candidate list.
            graph: CodeGraph or InMemoryGraphStore instance.
            config: Optional GraphExpansionConfig override.

        Returns:
            GraphExpansionResult containing candidates, anchors, path metadata, and limits info.
        """
        raise NotImplementedError
