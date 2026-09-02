"""Production-quality VectorRetriever service orchestrating query embedding and vector search."""

import time
from typing import Any

from code_analyzer.parsers.models import Language
from retrieval.contracts import (
    EmbeddingProviderContract,
    VectorIndexContract,
    VectorRetrieverContract,
)
from retrieval.embedding_models import EmbeddingInput
from retrieval.enums import ChunkType, RetrievalSource
from retrieval.exceptions import VectorQueryError
from retrieval.providers import DeterministicTestEmbeddingProvider
from retrieval.query_models import ProcessedQuery
from retrieval.query_processor import QueryPreprocessor
from retrieval.retrieval_models import RetrievalResult, RetrievalResultSet
from retrieval.text_builder import EmbeddingTextBuilder
from retrieval.vector_index import VectorIndex


class VectorRetriever(VectorRetrieverContract):
    """Production-quality VectorRetriever service for Phase 5 semantic code search.

    Orchestrates query preprocessing, query vector generation via abstract EmbeddingProvider,
    vector index search, repository boundary isolation, and result ranking.
    """

    def __init__(
        self,
        index: VectorIndexContract | None = None,
        provider: EmbeddingProviderContract | None = None,
        preprocessor: QueryPreprocessor | None = None,
        text_builder: EmbeddingTextBuilder | None = None,
    ) -> None:
        self.index = index if index is not None else VectorIndex()
        self.provider = provider if provider is not None else DeterministicTestEmbeddingProvider()
        self.preprocessor = preprocessor if preprocessor is not None else QueryPreprocessor()
        self.text_builder = text_builder if text_builder is not None else EmbeddingTextBuilder()

    def retrieve(
        self,
        query: str | ProcessedQuery,
        repository_id: str,
        top_k: int = 10,
        language: Language | None = None,
        chunk_type: ChunkType | None = None,
        file_path: str | None = None,
        commit_sha: str | None = None,
    ) -> RetrievalResultSet:
        """Execute Phase 5 vector retrieval pipeline returning ranked semantic candidates.

        Args:
            query: Raw query string or preprocessed ProcessedQuery.
            repository_id: Target repository identity for search boundary.
            top_k: Maximum number of ranked candidates to return (must be > 0).
            language: Optional language metadata filter.
            chunk_type: Optional chunk type filter.
            file_path: Optional file path filter.
            commit_sha: Optional index version / commit SHA filter.

        Returns:
            RetrievalResultSet containing ProcessedQuery and ordered RetrievalResults.
        """
        t0 = time.perf_counter()

        # 1. Validate repository_id boundary
        if not repository_id or not repository_id.strip():
            raise VectorQueryError("repository_id cannot be empty or whitespace")

        # 2. Validate top_k
        if top_k <= 0:
            raise VectorQueryError(f"top_k must be > 0, got {top_k}")

        # 3. Query preprocessing
        processed_query: ProcessedQuery
        prep_latency_ms: float = 0.0

        if isinstance(query, str):
            if not query or not query.strip():
                raise VectorQueryError("Query string cannot be empty or whitespace")
            t_prep = time.perf_counter()
            processed_query = self.preprocessor.process(query)
            prep_latency_ms = (time.perf_counter() - t_prep) * 1000.0
        elif isinstance(query, ProcessedQuery):
            processed_query = query
        else:
            raise VectorQueryError(f"Invalid query type: {type(query)}")

        # 4. Query embedding generation
        query_text = processed_query.normalized_query
        meta: dict[str, Any] = {"repository_id": repository_id}
        if commit_sha:
            meta["commit_sha"] = commit_sha

        inp = EmbeddingInput(
            chunk_id="__query__",
            text=query_text,
            model_name=self.provider.model_name,
            embedding_version=self.provider.embedding_version,
            metadata=meta,
        )

        t_search_start = time.perf_counter()
        embed_results = self.provider.embed([inp])
        if not embed_results:
            raise VectorQueryError("Embedding provider returned empty result for query vector")

        query_vector = embed_results[0].vector

        # 5. Vector index search
        hits = self.index.search(
            query_vector=query_vector,
            repository_id=repository_id,
            top_k=top_k,
            language=language,
            chunk_type=chunk_type,
            file_path=file_path,
            commit_sha=commit_sha,
        )
        retrieval_latency_ms = (time.perf_counter() - t_search_start) * 1000.0

        # 6. Map vector hits to RetrievalResult candidates
        results: list[RetrievalResult] = []
        for idx, hit in enumerate(hits):
            results.append(
                RetrievalResult(
                    chunk_id=hit.chunk_id,
                    score=hit.score,
                    rank=idx + 1,
                    repository_id=hit.repository_id,
                    commit_id=hit.commit_id,
                    commit_sha=hit.commit_sha,
                    file_path=hit.file_path,
                    language=hit.language,
                    chunk_type=hit.chunk_type,
                    symbol_name=hit.symbol_name,
                    qualified_name=hit.qualified_name,
                    start_line=hit.start_line,
                    end_line=hit.end_line,
                    metadata=hit.metadata,
                    sources=[RetrievalSource.VECTOR],
                    vector_rank=idx + 1,
                    vector_score=hit.score,
                )
            )

        total_latency_ms = (time.perf_counter() - t0) * 1000.0

        return RetrievalResultSet(
            query=processed_query,
            repository_id=repository_id,
            results=results,
            total_matches=len(results),
            preprocessing_latency_ms=prep_latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
            total_latency_ms=total_latency_ms,
        )
