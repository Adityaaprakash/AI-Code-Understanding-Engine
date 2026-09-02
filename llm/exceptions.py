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
