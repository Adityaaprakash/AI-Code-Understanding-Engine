"""Configuration model for TASK-6G Grounded Answer Generation."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm.exceptions import InvalidAnswerConfigError


class AnswerGenerationConfig(BaseModel):
    """Immutable configuration for Grounded Answer Generation."""

    model_config = ConfigDict(frozen=True)

    provider_name: str = Field(description="Target provider name to resolve from registry.")
    model_name: str = Field(description="Target model identifier.")
    temperature: float = Field(
        default=0.0, description="Sampling temperature parameter between 0.0 and 2.0."
    )
    max_tokens: int | None = Field(
        default=None, description="Maximum generation completion tokens if restricted."
    )
    top_p: float | None = Field(
        default=None, description="Nucleus sampling probability threshold between 0.0 and 1.0."
    )
    timeout: float | None = Field(
        default=None, description="Per-request execution timeout limit in seconds."
    )

    @model_validator(mode="after")
    def validate_config(self) -> "AnswerGenerationConfig":
        if not self.provider_name or not self.provider_name.strip():
            raise InvalidAnswerConfigError("Provider name cannot be empty or whitespace-only.")
        if not self.model_name or not self.model_name.strip():
            raise InvalidAnswerConfigError("Model name cannot be empty or whitespace-only.")
        if not (0.0 <= self.temperature <= 2.0):
            raise InvalidAnswerConfigError(
                f"Temperature must be between 0.0 and 2.0, got {self.temperature}."
            )
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise InvalidAnswerConfigError(
                f"max_tokens must be positive if specified, got {self.max_tokens}."
            )
        if self.top_p is not None and not (0.0 <= self.top_p <= 1.0):
            raise InvalidAnswerConfigError(f"top_p must be between 0.0 and 1.0, got {self.top_p}.")
        if self.timeout is not None and self.timeout <= 0:
            raise InvalidAnswerConfigError(
                f"timeout must be positive if specified, got {self.timeout}."
            )
        return self
