"""Exceptions for the retrieval and embedding pipeline."""


class EmbeddingError(Exception):
    """Base exception for all embedding-related errors."""

    pass


class EmbeddingConfigurationError(EmbeddingError):
    """Raised when embedding configuration (provider, dimension, batch size) is invalid."""

    pass


class EmbeddingProviderError(EmbeddingError):
    """Raised when an embedding provider fails during embedding generation."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class EmbeddingDimensionError(EmbeddingError):
    """Raised when a provider returns a vector with unexpected dimension."""

    pass


class EmbeddingInputError(EmbeddingError):
    """Raised when embedding inputs are invalid (empty text, duplicate chunk IDs)."""

    pass


class EmbeddingBatchError(EmbeddingError):
    """Raised when batch processing fails or result count mismatches requested inputs."""

    pass
