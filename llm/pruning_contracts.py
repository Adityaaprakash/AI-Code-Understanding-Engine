"""Contract interfaces for TASK-6D Context Deduplication & Pruning."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from llm.planner_models import QueryPlan
    from llm.pruning_config import ContextPruningConfig
    from llm.pruning_models import ContextPruningResult
    from llm.ranking_models import ContextRankingResult, RankedContextCandidate


class ContextPrunerContract(ABC):
    """Formal contract interface for Phase 6D candidate context deduplication and pruning."""

    @abstractmethod
    def prune(
        self,
        query_plan: QueryPlan,
        candidates: Sequence[RankedContextCandidate] | ContextRankingResult,
        config: ContextPruningConfig | None = None,
    ) -> ContextPruningResult:
        """Deterministically deduplicate and prune ranked context candidates.

        Args:
            query_plan: Immutable Phase 6A query plan containing intent and control signals.
            candidates: Ranked context candidates from Phase 6C ranker.
            config: Optional ContextPruningConfig overrides.

        Returns:
            ContextPruningResult containing surviving candidates, pruning audit logs, and metrics.
        """
        pass
