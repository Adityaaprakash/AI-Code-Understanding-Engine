"""Contract interfaces for TASK-6C Context Ranking."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from llm.expansion_models import GraphExpansionCandidate
    from llm.planner_models import QueryPlan
    from llm.ranking_config import ContextRankingConfig
    from llm.ranking_models import ContextRankingResult
    from retrieval.retrieval_models import RetrievalResult


class ContextRankerContract(ABC):
    """Formal contract for Phase 6C candidate context ranking."""

    @abstractmethod
    def rank(
        self,
        query_plan: QueryPlan,
        candidates: Sequence[GraphExpansionCandidate | RetrievalResult],
        config: ContextRankingConfig | None = None,
    ) -> ContextRankingResult:
        """Deterministically rank context candidates based on query plan control signals.

        Args:
            query_plan: Immutable Phase 6A query plan containing intent and control signals.
            candidates: Combined context candidates from Phase 5 retrieval and/or Phase 6B expansion.
            config: Optional ContextRankingConfig overrides.

        Returns:
            ContextRankingResult containing ranked candidates in deterministic order.
        """
        pass
