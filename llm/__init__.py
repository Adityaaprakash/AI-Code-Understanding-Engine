"""Phase 6 — LLM Context & Answer Engine package."""

from llm.answer_config import AnswerGenerationConfig
from llm.answer_contracts import AnswerGeneratorContract
from llm.answer_generator import AnswerGenerator
from llm.answer_models import GeneratedAnswer
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
    CitationStatus,
    ClaimStatus,
    ContextOverflowPolicy,
    ContextPackingReasonCode,
    GraphStrategy,
    GroundingReasonCode,
    GroundingStatus,
    LLMFinishReason,
    LLMMessageRole,
    LLMProviderErrorCategory,
    PruningReasonCode,
    QueryIntent,
    QueryScope,
    RankingReasonCode,
    RelationshipType,
    RetrievalStrategy,
    TokenCountMode,
)
from llm.exceptions import (
    AnswerGenerationError,
    ContextPackingError,
    ContextPruningError,
    ContextRankingError,
    GraphExpansionError,
    GroundingVerificationError,
    InvalidAnswerConfigError,
    InvalidBudgetConfigError,
    InvalidExpansionConfigError,
    InvalidGroundingConfigError,
    InvalidLLMConfigError,
    InvalidLLMRequestError,
    InvalidPruningConfigError,
    InvalidQueryError,
    InvalidRankingConfigError,
    LLMAuthenticationError,
    LLMError,
    LLMExecutionError,
    LLMModelUnavailableError,
    LLMProviderError,
    LLMProviderNotFoundError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
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
from llm.fake_provider import FakeLLMProvider
from llm.graph_expander import GraphContextExpander
from llm.grounding_config import GroundingVerificationConfig
from llm.grounding_contracts import GroundingEngineContract
from llm.grounding_engine import GroundingEngine
from llm.grounding_models import (
    CitationReference,
    GroundingClaim,
    GroundingMetrics,
    GroundingVerificationResult,
)
from llm.planner_models import QueryPlan
from llm.provider_config import LLMProviderConfig
from llm.provider_contracts import LLMProviderContract
from llm.provider_models import (
    LLMMessage,
    LLMProviderCapabilities,
    LLMRequest,
    LLMResponse,
)
from llm.provider_registry import LLMProviderRegistry, provider_registry
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
    "AnswerGenerationConfig",
    "AnswerGenerationError",
    "AnswerGenerator",
    "AnswerGeneratorContract",
    "AnswerStyle",
    "CitationReference",
    "CitationStatus",
    "ClaimStatus",
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
    "FakeLLMProvider",
    "GeneratedAnswer",
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
    "GroundingClaim",
    "GroundingEngine",
    "GroundingEngineContract",
    "GroundingMetrics",
    "GroundingReasonCode",
    "GroundingStatus",
    "GroundingVerificationConfig",
    "GroundingVerificationError",
    "GroundingVerificationResult",
    "InvalidAnswerConfigError",
    "InvalidBudgetConfigError",
    "InvalidExpansionConfigError",
    "InvalidGroundingConfigError",
    "InvalidLLMConfigError",
    "InvalidLLMRequestError",
    "InvalidPruningConfigError",
    "InvalidQueryError",
    "InvalidRankingConfigError",
    "LLMAuthenticationError",
    "LLMError",
    "LLMExecutionError",
    "LLMFinishReason",
    "LLMMessage",
    "LLMMessageRole",
    "LLMModelUnavailableError",
    "LLMProviderCapabilities",
    "LLMProviderConfig",
    "LLMProviderContract",
    "LLMProviderError",
    "LLMProviderErrorCategory",
    "LLMProviderNotFoundError",
    "LLMProviderRegistry",
    "LLMProviderUnavailableError",
    "LLMRateLimitError",
    "LLMRequest",
    "LLMResponse",
    "LLMTimeoutError",
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
    "provider_registry",
]
