"""Provider registry and resolution engine for TASK-6F LLM Provider Abstraction."""

from threading import Lock

from llm.exceptions import InvalidLLMConfigError, LLMProviderNotFoundError
from llm.provider_contracts import LLMProviderContract


class LLMProviderRegistry:
    """Thread-safe registry for registering and resolving LLM provider implementations."""

    def __init__(self) -> None:
        self._providers: dict[str, LLMProviderContract] = {}
        self._lock = Lock()

    def register(
        self, provider_name: str, provider: LLMProviderContract, overwrite: bool = False
    ) -> None:
        """Register an LLM provider adapter instance.

        Args:
            provider_name: Unique string name identifying the provider.
            provider: Concrete LLMProviderContract instance.
            overwrite: If True, overwrite existing registered provider under provider_name.

        Raises:
            InvalidLLMConfigError: If provider_name is empty, provider is invalid,
                                  or provider_name is already registered and overwrite is False.
        """
        if not provider_name or not provider_name.strip():
            raise InvalidLLMConfigError("Provider name cannot be empty or whitespace-only.")

        name_key = provider_name.strip().lower()

        if not isinstance(provider, LLMProviderContract):
            raise InvalidLLMConfigError(
                f"Registered provider for '{provider_name}' must implement LLMProviderContract."
            )

        with self._lock:
            if name_key in self._providers and not overwrite:
                raise InvalidLLMConfigError(
                    f"Provider '{name_key}' is already registered. Set overwrite=True to replace.",
                    provider_name=name_key,
                )
            self._providers[name_key] = provider

    def resolve(self, provider_name: str) -> LLMProviderContract:
        """Resolve a registered LLM provider adapter instance by name.

        Args:
            provider_name: Case-insensitive unique string identifier of requested provider.

        Returns:
            The registered LLMProviderContract instance.

        Raises:
            LLMProviderNotFoundError: If provider_name is not registered.
        """
        if not provider_name or not provider_name.strip():
            raise LLMProviderNotFoundError("Provider name cannot be empty or whitespace-only.")

        name_key = provider_name.strip().lower()

        with self._lock:
            provider = self._providers.get(name_key)
            if provider is None:
                available = ", ".join(sorted(self._providers.keys())) or "none"
                raise LLMProviderNotFoundError(
                    f"LLM Provider '{name_key}' is not registered. Available providers: [{available}].",
                    provider_name=name_key,
                )
            return provider

    def unregister(self, provider_name: str) -> bool:
        """Unregister a provider by name. Returns True if provider was removed, False if not found."""
        name_key = provider_name.strip().lower()
        with self._lock:
            if name_key in self._providers:
                del self._providers[name_key]
                return True
            return False

    def list_providers(self) -> list[str]:
        """Return a sorted list of registered provider names."""
        with self._lock:
            return sorted(self._providers.keys())

    def clear(self) -> None:
        """Clear all registered providers from the registry."""
        with self._lock:
            self._providers.clear()


# Default thread-safe singleton instance for convenience
provider_registry = LLMProviderRegistry()
