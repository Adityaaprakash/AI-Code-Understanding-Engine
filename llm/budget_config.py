"""Configuration model for TASK-6E Context Token Budgeting & Context Packing."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm.enums import ContextOverflowPolicy, TokenCountMode
from llm.exceptions import InvalidBudgetConfigError


class ContextBudgetConfig(BaseModel):
    """Immutable configuration governing context window budgeting, reserves, and overflow policies."""

    model_config = ConfigDict(frozen=True)

    max_context_tokens: int = Field(
        default=8000,
        description="Total context window limit for the target model (must be > 0).",
    )
    reserved_system_tokens: int = Field(
        default=1000,
        description="Reserved token budget for system instructions and prompts (must be >= 0).",
    )
    reserved_query_tokens: int = Field(
        default=500,
        description="Reserved token budget for the user query (must be >= 0).",
    )
    reserved_output_tokens: int = Field(
        default=1000,
        description="Reserved token budget for model answer generation (must be >= 0).",
    )
    safety_margin_tokens: int = Field(
        default=500,
        description="Safety buffer tokens to prevent context overflow (must be >= 0).",
    )
    minimum_candidate_tokens: int | None = Field(
        default=None,
        description="Optional minimum candidate token threshold for inclusion.",
    )
    maximum_candidate_tokens: int | None = Field(
        default=None,
        description="Optional maximum candidate token threshold for inclusion.",
    )
    overflow_policy: ContextOverflowPolicy = Field(
        default=ContextOverflowPolicy.SKIP,
        description="Action policy when a candidate exceeds remaining usable evidence budget.",
    )
    token_count_mode: TokenCountMode = Field(
        default=TokenCountMode.ESTIMATED,
        description="Mode indicator for token counting (EXACT or ESTIMATED).",
    )

    @model_validator(mode="after")
    def validate_budget_settings(self) -> "ContextBudgetConfig":
        """Validate token limits, non-negative reserves, and overall budget capacity."""
        if self.max_context_tokens <= 0:
            raise InvalidBudgetConfigError(
                f"max_context_tokens must be > 0, got {self.max_context_tokens}"
            )

        if self.reserved_system_tokens < 0:
            raise InvalidBudgetConfigError(
                f"reserved_system_tokens must be >= 0, got {self.reserved_system_tokens}"
            )

        if self.reserved_query_tokens < 0:
            raise InvalidBudgetConfigError(
                f"reserved_query_tokens must be >= 0, got {self.reserved_query_tokens}"
            )

        if self.reserved_output_tokens < 0:
            raise InvalidBudgetConfigError(
                f"reserved_output_tokens must be >= 0, got {self.reserved_output_tokens}"
            )

        if self.safety_margin_tokens < 0:
            raise InvalidBudgetConfigError(
                f"safety_margin_tokens must be >= 0, got {self.safety_margin_tokens}"
            )

        if self.minimum_candidate_tokens is not None and self.minimum_candidate_tokens < 0:
            raise InvalidBudgetConfigError(
                f"minimum_candidate_tokens must be >= 0, got {self.minimum_candidate_tokens}"
            )

        if self.maximum_candidate_tokens is not None and self.maximum_candidate_tokens < 0:
            raise InvalidBudgetConfigError(
                f"maximum_candidate_tokens must be >= 0, got {self.maximum_candidate_tokens}"
            )

        if (
            self.minimum_candidate_tokens is not None
            and self.maximum_candidate_tokens is not None
            and self.minimum_candidate_tokens > self.maximum_candidate_tokens
        ):
            raise InvalidBudgetConfigError(
                f"minimum_candidate_tokens ({self.minimum_candidate_tokens}) cannot exceed "
                f"maximum_candidate_tokens ({self.maximum_candidate_tokens})"
            )

        total_reserves = (
            self.reserved_system_tokens
            + self.reserved_query_tokens
            + self.reserved_output_tokens
            + self.safety_margin_tokens
        )

        if total_reserves > self.max_context_tokens:
            raise InvalidBudgetConfigError(
                f"Total reserved tokens ({total_reserves}) exceeds max_context_tokens ({self.max_context_tokens}). "
                "Reserved tokens + safety margin must fit within the model context limit."
            )

        return self

    @property
    def total_reserved_tokens(self) -> int:
        """Calculate total reserved tokens across system, query, output, and safety margin."""
        return (
            self.reserved_system_tokens
            + self.reserved_query_tokens
            + self.reserved_output_tokens
            + self.safety_margin_tokens
        )

    @property
    def usable_evidence_budget(self) -> int:
        """Calculate usable context budget available strictly for evidence packing."""
        return max(0, self.max_context_tokens - self.total_reserved_tokens)
