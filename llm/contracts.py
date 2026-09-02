"""Abstract base class contracts for Phase 6 Query Intent & Query Planning."""

from abc import ABC, abstractmethod

from llm.planner_models import QueryPlan
from retrieval.query_models import ProcessedQuery


class QueryPlannerContract(ABC):
    """Abstract interface contract for Phase 6A Query Planner."""

    @abstractmethod
    def plan(self, query: str | ProcessedQuery) -> QueryPlan:
        """Transform a raw text query or ProcessedQuery into a structured QueryPlan.

        Args:
            query: Raw query string or preprocessed ProcessedQuery.

        Returns:
            Immutable, deterministic QueryPlan object.

        Raises:
            InvalidQueryError: If query input is invalid, empty, or whitespace-only.
            QueryPlanningError: If planning fails unexpectedly.
        """
        raise NotImplementedError
