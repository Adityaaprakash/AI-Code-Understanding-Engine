"""Abstract provider contract interface for TASK-6F LLM Provider Abstraction."""

from abc import ABC, abstractmethod

from llm.provider_models import LLMProviderCapabilities, LLMRequest, LLMResponse


class LLMProviderContract(ABC):
    """Abstract interface contract for provider-independent LLM adapters."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the unique provider identifier (e.g., 'openai', 'fake_provider')."""
        raise NotImplementedError

    @property
    @abstractmethod
    def capabilities(self) -> LLMProviderCapabilities:
        """Return the static/discovered capabilities of this provider adapter."""
        raise NotImplementedError

    @abstractmethod
    def invoke(self, request: LLMRequest) -> LLMResponse:
        """Synchronously execute an LLM invocation request.

        Args:
            request: Provider-independent LLM invocation request payload.

        Returns:
            Normalized LLM response model.

        Raises:
            InvalidLLMRequestError: If request parameters or payload are invalid.
            LLMTimeoutError: If execution exceeds configured or request timeout.
            LLMAuthenticationError: If API credentials or authentication fails.
            LLMRateLimitError: If provider rate limit or quota is exceeded.
            LLMProviderUnavailableError: If the remote provider service is down.
            LLMExecutionError: If an unhandled remote or runtime error occurs.
        """
        raise NotImplementedError

    async def ainvoke(self, request: LLMRequest) -> LLMResponse:
        """Asynchronously execute an LLM invocation request.

        Default implementation delegates to synchronous invoke. Concrete adapters
        may override with native async network calls.
        """
        return self.invoke(request)
