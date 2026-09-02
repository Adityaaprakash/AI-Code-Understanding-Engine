"""Exceptions for LLM Context & Answer Engine (Phase 6)."""


class LLMError(Exception):
    """Base exception class for all Phase 6 LLM pipeline errors."""

    pass


class QueryPlanningError(LLMError):
    """Exception raised when query planning or intent classification fails."""

    pass


class InvalidQueryError(QueryPlanningError):
    """Exception raised when query input is invalid, empty, or whitespace-only."""

    pass


class GraphExpansionError(LLMError):
    """Exception raised when graph expansion fails or encounters an invalid state."""

    pass


class InvalidExpansionConfigError(GraphExpansionError):
    """Exception raised when expansion limits or configuration settings are invalid."""

    pass


class ContextRankingError(LLMError):
    """Exception raised when context ranking fails or encounters an invalid state."""

    pass


class InvalidRankingConfigError(ContextRankingError):
    """Exception raised when ranking weights or configuration settings are invalid."""

    pass


class ContextPruningError(LLMError):
    """Exception raised when context deduplication/pruning fails or encounters an invalid state."""

    pass


class InvalidPruningConfigError(ContextPruningError):
    """Exception raised when pruning threshold or configuration settings are invalid."""

    pass


class ContextPackingError(LLMError):
    """Exception raised when context token budgeting or context packing fails."""

    pass


class InvalidBudgetConfigError(ContextPackingError):
    """Exception raised when token budget configuration or reserve settings are invalid."""

    pass


class TokenCountingError(ContextPackingError):
    """Exception raised when token calculation fails or encounters an invalid input state."""

    pass
