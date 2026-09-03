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


class LLMProviderError(LLMError):
    """Base exception class for all LLM provider abstraction errors."""

    def __init__(
        self,
        message: str,
        category: str = "execution_failure",
        provider_name: str | None = None,
        details: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.category = category
        self.provider_name = provider_name
        self.details = details or {}


class InvalidLLMConfigError(LLMProviderError):
    """Exception raised when provider configuration is invalid or missing required credentials."""

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        details: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        super().__init__(
            message, category="configuration", provider_name=provider_name, details=details
        )


class LLMAuthenticationError(LLMProviderError):
    """Exception raised when provider authentication or API key validation fails."""

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        details: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        super().__init__(
            message, category="authentication", provider_name=provider_name, details=details
        )


class LLMProviderUnavailableError(LLMProviderError):
    """Exception raised when provider service or endpoint is unavailable."""

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        details: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        super().__init__(
            message, category="unavailable", provider_name=provider_name, details=details
        )


class LLMTimeoutError(LLMProviderError):
    """Exception raised when provider invocation exceeds timeout limit."""

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        details: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        super().__init__(message, category="timeout", provider_name=provider_name, details=details)


class LLMRateLimitError(LLMProviderError):
    """Exception raised when provider rate limit or quota is exceeded."""

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        details: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        super().__init__(
            message, category="rate_limit", provider_name=provider_name, details=details
        )


class InvalidLLMRequestError(LLMProviderError):
    """Exception raised when invocation request parameters or payload are invalid."""

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        details: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        super().__init__(
            message, category="invalid_request", provider_name=provider_name, details=details
        )


class LLMModelUnavailableError(LLMProviderError):
    """Exception raised when requested model identifier is unavailable or unsupported."""

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        details: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        super().__init__(
            message, category="model_unavailable", provider_name=provider_name, details=details
        )


class LLMExecutionError(LLMProviderError):
    """Exception raised when provider execution fails due to remote runtime or unexpected errors."""

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        details: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        super().__init__(
            message, category="execution_failure", provider_name=provider_name, details=details
        )


class LLMProviderNotFoundError(LLMProviderError):
    """Exception raised when attempting to resolve an unregistered provider."""

    def __init__(
        self,
        message: str,
        provider_name: str | None = None,
        details: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        super().__init__(
            message, category="configuration", provider_name=provider_name, details=details
        )
