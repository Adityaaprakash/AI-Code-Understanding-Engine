"""Provider configuration models for TASK-6F LLM Provider Abstraction."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class LLMProviderConfig(BaseModel):
    """Immutable configuration for an LLM provider adapter instance."""

    model_config = ConfigDict(frozen=True)

    provider_name: str = Field(
        description="Unique provider identifier (e.g., openai, anthropic, fake_provider)."
    )
    model_name: str = Field(description="Default model identifier for this provider configuration.")
    api_key: SecretStr | None = Field(
        default=None, description="Sensitive API key credential (masked from string/repr output)."
    )
    api_base: str | None = Field(
        default=None, description="Optional custom base URL endpoint for provider API calls."
    )
    timeout: float = Field(default=30.0, description="Default invocation timeout limit in seconds.")
    max_retries: int = Field(
        default=0, description="Maximum number of retry attempts for transient provider failures."
    )
    extra_params: dict[str, Any] = Field(
        default_factory=dict, description="Extensible provider-specific configuration options."
    )

    @model_validator(mode="after")
    def validate_config(self) -> "LLMProviderConfig":
        """Validate provider configuration invariants."""
        if not self.provider_name or not self.provider_name.strip():
            raise ValueError("provider_name cannot be empty or whitespace-only.")
        if not self.model_name or not self.model_name.strip():
            raise ValueError("model_name cannot be empty or whitespace-only.")
        if self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got {self.timeout}.")
        if self.max_retries < 0:
            raise ValueError(f"max_retries cannot be negative, got {self.max_retries}.")
        return self
