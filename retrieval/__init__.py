"""Code retrieval and embedding module for CodeLens AI."""

from retrieval.chunker import CodeChunker
from retrieval.contracts import CodeChunkerContract, EmbeddingProviderContract, LexicalIndexContract
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
    LexicalConfigurationError,
    LexicalDocumentError,
    LexicalIndexError,
    LexicalQueryError,
    RetrievalError,
)
from retrieval.identity import generate_chunk_id
from retrieval.lexical_index import BM25LexicalIndex
from retrieval.lexical_models import LexicalDocument, LexicalSearchResult, LexicalSearchResultSet
from retrieval.lexical_text_builder import LexicalTextBuilder
from retrieval.models import CodeChunk, CodeChunkCollection
from retrieval.providers import DeterministicTestEmbeddingProvider, HostedAPIEmbeddingProvider
from retrieval.text_builder import EmbeddingTextBuilder
from retrieval.tokenizer import CodeTokenizer, tokenize_code, tokenize_query

__all__ = [
    "BM25LexicalIndex",
    "ChunkType",
    "CodeChunk",
    "CodeChunkCollection",
    "CodeChunker",
    "CodeChunkerContract",
    "CodeTokenizer",
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
    "LexicalConfigurationError",
    "LexicalDocument",
    "LexicalDocumentError",
    "LexicalIndexContract",
    "LexicalIndexError",
    "LexicalQueryError",
    "LexicalSearchResult",
    "LexicalSearchResultSet",
    "LexicalTextBuilder",
    "RetrievalError",
    "generate_chunk_id",
    "tokenize_code",
    "tokenize_query",
]
