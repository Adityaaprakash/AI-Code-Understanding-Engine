"""Code retrieval and embedding module for CodeLens AI."""

from retrieval.chunker import CodeChunker
from retrieval.contracts import CodeChunkerContract, EmbeddingProviderContract
from retrieval.embedding_models import (
    EmbeddingBatchResult,
    EmbeddingFailure,
    EmbeddingInput,
    EmbeddingResult,
)
from retrieval.embedding_pipeline import EmbeddingPipeline
from retrieval.enums import ChunkType
from retrieval.exceptions import (
    EmbeddingBatchError,
    EmbeddingConfigurationError,
    EmbeddingDimensionError,
    EmbeddingError,
    EmbeddingInputError,
    EmbeddingProviderError,
)
from retrieval.identity import generate_chunk_id
from retrieval.models import CodeChunk, CodeChunkCollection
from retrieval.providers import DeterministicTestEmbeddingProvider, HostedAPIEmbeddingProvider
from retrieval.text_builder import EmbeddingTextBuilder

__all__ = [
    "ChunkType",
    "CodeChunk",
    "CodeChunkCollection",
    "CodeChunker",
    "CodeChunkerContract",
    "DeterministicTestEmbeddingProvider",
    "EmbeddingBatchError",
    "EmbeddingBatchResult",
    "EmbeddingConfigurationError",
    "EmbeddingDimensionError",
    "EmbeddingError",
    "EmbeddingFailure",
    "EmbeddingInput",
    "EmbeddingInputError",
    "EmbeddingPipeline",
    "EmbeddingProviderContract",
    "EmbeddingProviderError",
    "EmbeddingResult",
    "EmbeddingTextBuilder",
    "HostedAPIEmbeddingProvider",
    "generate_chunk_id",
]
