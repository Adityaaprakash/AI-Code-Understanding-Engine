"""Phase 6 — LLM Context & Answer Engine package."""

from llm.budget_config import ContextBudgetConfig
from llm.budget_contracts import ContextPackerContract
from llm.budget_models import (
    ContextOmissionRecord,
    ContextPackingStats,
    PackedContext,
    PackedContextItem,
)
from llm.context_packer import ContextPacker
from llm.context_pruner import ContextPruner
from llm.context_ranker import ContextRanker
from llm.contracts import QueryPlannerContract
from llm.enums import (
    AnswerStyle,
    ContextOverflowPolicy,
    ContextPackingReasonCode,
    GraphStrategy,
    PruningReasonCode,
    QueryIntent,
    QueryScope,
    RankingReasonCode,
    RelationshipType,
    RetrievalStrategy,
    TokenCountMode,
)
from llm.exceptions import (
    ContextPackingError,
    ContextPruningError,
    ContextRankingError,
    GraphExpansionError,
    InvalidBudgetConfigError,
    InvalidExpansionConfigError,
    InvalidPruningConfigError,
    InvalidQueryError,
    InvalidRankingConfigError,
    LLMError,
    QueryPlanningError,
    TokenCountingError,
)
from llm.expansion_config import GraphExpansionConfig
from llm.expansion_contracts import GraphExpanderContract
from llm.expansion_models import (
    GraphExpansionAnchor,
    GraphExpansionCandidate,
    GraphExpansionCandidatePath,
    GraphExpansionCandidateStep,
    GraphExpansionResult,
)
from llm.graph_expander import GraphContextExpander
from llm.planner_models import QueryPlan
from llm.pruning_config import ContextPruningConfig
from llm.pruning_contracts import ContextPrunerContract
from llm.pruning_models import ContextPruningResult, PrunedCandidateRecord
from llm.query_planner import QueryPlanner
from llm.ranking_config import ContextRankingConfig
from llm.ranking_contracts import ContextRankerContract
from llm.ranking_models import (
    ContextRankingResult,
    ContextRankingScoreBreakdown,
    RankedContextCandidate,
)
from llm.token_counter import (
    DeterministicFallbackTokenCounter,
    ExactTokenCounter,
    TokenCounterContract,
)

__all__ = [
    "AnswerStyle",
    "ContextBudgetConfig",
    "ContextOmissionRecord",
    "ContextOverflowPolicy",
    "ContextPacker",
    "ContextPackerContract",
    "ContextPackingError",
    "ContextPackingReasonCode",
    "ContextPackingStats",
    "ContextPruner",
    "ContextPrunerContract",
    "ContextPruningConfig",
    "ContextPruningError",
    "ContextPruningResult",
    "ContextRanker",
    "ContextRankerContract",
    "ContextRankingConfig",
    "ContextRankingError",
    "ContextRankingResult",
    "ContextRankingScoreBreakdown",
    "DeterministicFallbackTokenCounter",
    "ExactTokenCounter",
    "GraphContextExpander",
    "GraphExpanderContract",
    "GraphExpansionAnchor",
    "GraphExpansionCandidate",
    "GraphExpansionCandidatePath",
    "GraphExpansionCandidateStep",
    "GraphExpansionConfig",
    "GraphExpansionError",
    "GraphExpansionResult",
    "GraphStrategy",
    "InvalidBudgetConfigError",
    "InvalidExpansionConfigError",
    "InvalidPruningConfigError",
    "InvalidQueryError",
    "InvalidRankingConfigError",
    "LLMError",
    "PackedContext",
    "PackedContextItem",
    "PrunedCandidateRecord",
    "PruningReasonCode",
    "QueryIntent",
    "QueryPlan",
    "QueryPlanner",
    "QueryPlannerContract",
    "QueryPlanningError",
    "QueryScope",
    "RankedContextCandidate",
    "RankingReasonCode",
    "RelationshipType",
    "RetrievalStrategy",
    "TokenCountMode",
    "TokenCounterContract",
    "TokenCountingError",
]
