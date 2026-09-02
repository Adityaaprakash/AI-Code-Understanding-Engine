"""Contract interfaces for TASK-6E Context Token Budgeting & Context Packing."""

from abc import ABC, abstractmethod

from llm.budget_config import ContextBudgetConfig
from llm.budget_models import PackedContext
from llm.planner_models import QueryPlan
from llm.pruning_models import ContextPruningResult


class ContextPackerContract(ABC):
    """Formal contract interface for Phase 6E context token budgeting and context packing."""

    @abstractmethod
    def pack(
        self,
        query_plan: QueryPlan,
        pruning_result: ContextPruningResult,
        config: ContextBudgetConfig | None = None,
    ) -> PackedContext:
        """Deterministically transform 6D pruned context candidates into a bounded context package.

        Args:
            query_plan: Immutable Phase 6A query plan containing intent and query metadata.
            pruning_result: ContextPruningResult from Phase 6D context pruner.
            config: Optional ContextBudgetConfig overrides.

        Returns:
            PackedContext containing ordered packed items, omission records, and stats.

        Raises:
            ContextPackingError: If packing fails or encounters an invalid state.
        """
        pass
