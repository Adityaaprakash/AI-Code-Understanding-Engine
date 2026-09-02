"""Token counting abstraction for TASK-6E Context Token Budgeting & Context Packing."""

import re
from abc import ABC, abstractmethod
from collections.abc import Callable

from llm.enums import TokenCountMode
from llm.exceptions import TokenCountingError


class TokenCounterContract(ABC):
    """Abstract interface contract for token counting implementations."""

    @abstractmethod
    def count(self, text: str) -> int:
        """Calculate token count for the given text.

        Args:
            text: Input string to calculate token count for.

        Returns:
            Non-negative integer token count.

        Raises:
            TokenCountingError: If input text is invalid or tokenization fails.
        """
        pass

    @abstractmethod
    def get_mode(self) -> TokenCountMode:
        """Return token counting mode (EXACT or ESTIMATED)."""
        pass


class DeterministicFallbackTokenCounter(TokenCounterContract):
    """Deterministic token counter using character/word/symbol heuristics for offline estimation.

    Note: Counts produced by this estimator are explicitly marked as TokenCountMode.ESTIMATED
    and are suitable for budget safety calculations before LLM dispatch.
    """

    # Split code on whitespace and punctuation boundaries
    _TOKEN_SPLIT_REGEX = re.compile(r"\w+|[^\w\s]")

    def count(self, text: str) -> int:
        """Estimate token count deterministically."""
        if not isinstance(text, str):
            raise TokenCountingError(f"Expected text to be a string, got {type(text).__name__}")

        if not text:
            return 0

        # Heuristic 1: Sub-tokenization on punctuation/alphanumeric transitions
        tokens = self._TOKEN_SPLIT_REGEX.findall(text)
        token_based_count = len(tokens)

        # Heuristic 2: ~4 characters per token estimate
        char_based_count = (len(text) + 3) // 4

        # Take max of word/symbol tokens and character estimate to ensure safety
        estimated = max(token_based_count, char_based_count)
        return max(1, estimated)

    def get_mode(self) -> TokenCountMode:
        """Return ESTIMATED mode."""
        return TokenCountMode.ESTIMATED


class ExactTokenCounter(TokenCounterContract):
    """Token counter wrapper utilizing an exact model tokenizer function or encoding."""

    def __init__(self, tokenizer_fn: Callable[[str], int]) -> None:
        """Initialize with an exact tokenizer function.

        Args:
            tokenizer_fn: Callable taking text string and returning token count integer.
        """
        if not callable(tokenizer_fn):
            raise TokenCountingError("tokenizer_fn must be a callable function")
        self._tokenizer_fn = tokenizer_fn

    def count(self, text: str) -> int:
        """Compute exact token count using wrapped tokenizer."""
        if not isinstance(text, str):
            raise TokenCountingError(f"Expected text to be a string, got {type(text).__name__}")

        if not text:
            return 0

        try:
            cnt = self._tokenizer_fn(text)
            if cnt < 0:
                raise TokenCountingError(f"Tokenizer returned negative token count: {cnt}")
            return cnt

        except Exception as e:
            if isinstance(e, TokenCountingError):
                raise
            raise TokenCountingError(f"Exact tokenizer failed: {e}") from e

    def get_mode(self) -> TokenCountMode:
        """Return EXACT mode."""
        return TokenCountMode.EXACT
