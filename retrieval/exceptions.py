"""Exceptions for the retrieval engine (chunking, embeddings, lexical BM25 indexing)."""


class RetrievalError(Exception):
    """Base exception for all retrieval-related errors."""

    pass


class EmbeddingError(RetrievalError):
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


# ------------------------------------------------------------------------------
# Lexical BM25 Index Exceptions
# ------------------------------------------------------------------------------


class LexicalIndexError(RetrievalError):
    """Base exception for all lexical BM25 index errors."""

    pass


class LexicalConfigurationError(LexicalIndexError):
    """Raised when lexical index parameters (k1, b) or settings are invalid."""

    pass


class LexicalDocumentError(LexicalIndexError):
    """Raised when a lexical document or chunk input is invalid."""

    pass


class LexicalQueryError(LexicalIndexError):
    """Raised when a lexical search query parameters (e.g. top_k <= 0) are invalid."""

    pass
