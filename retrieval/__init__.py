"""Code retrieval, preprocessing, and search orchestration module for CodeLens AI."""

from retrieval.chunker import CodeChunker
from retrieval.contracts import (
    CodeChunkerContract,
    EmbeddingProviderContract,
    LexicalIndexContract,
    LexicalRetrieverContract,
)
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
from retrieval.lexical_models import LexicalDocument, LexicalSearchResult
from retrieval.lexical_retriever import LexicalRetriever
from retrieval.lexical_text_builder import LexicalTextBuilder
from retrieval.models import CodeChunk, CodeChunkCollection
from retrieval.providers import DeterministicTestEmbeddingProvider, HostedAPIEmbeddingProvider
from retrieval.query_models import ProcessedQuery, QueryKind
from retrieval.query_processor import QueryPreprocessor
from retrieval.retrieval_models import LexicalRetrievalRequest, RetrievalResult, RetrievalResultSet
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
    "LexicalRetrievalRequest",
    "LexicalRetriever",
    "LexicalRetrieverContract",
    "LexicalSearchResult",
    "LexicalTextBuilder",
    "ProcessedQuery",
    "QueryKind",
    "QueryPreprocessor",
    "RetrievalError",
    "RetrievalResult",
    "RetrievalResultSet",
    "generate_chunk_id",
    "tokenize_code",
    "tokenize_query",
]
