"""Production-grade Phase 5 BM25 Lexical Retrieval Service orchestrating preprocessing and search."""

import time

from code_analyzer.parsers.models import Language
from retrieval.contracts import LexicalIndexContract, LexicalRetrieverContract
from retrieval.enums import ChunkType
from retrieval.exceptions import LexicalQueryError
from retrieval.lexical_index import BM25LexicalIndex
from retrieval.query_models import ProcessedQuery
from retrieval.query_processor import QueryPreprocessor
from retrieval.retrieval_models import RetrievalResult, RetrievalResultSet


class LexicalRetriever(LexicalRetrieverContract):
    """Phase 5 BM25 Lexical Retrieval Service.

    Consumes Phase 4 BM25 index primitives through clean retrieval contracts.
    Executes query preprocessing, repository isolation scoping, metadata filtering,
    and returns ranked retrieval candidates with latency metrics.
    """

    def __init__(
        self,
        index: LexicalIndexContract | None = None,
        preprocessor: QueryPreprocessor | None = None,
    ) -> None:
        self.index = index if index is not None else BM25LexicalIndex()
        self.preprocessor = preprocessor if preprocessor is not None else QueryPreprocessor()

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
        """Execute Phase 5 lexical retrieval pipeline returning ranked candidates.

        Args:
            query: Raw query string or preprocessed ProcessedQuery instance.
            repository_id: Mandatory target repository identity boundary.
            top_k: Maximum number of ranked candidates to return (must be > 0).
            language: Optional language metadata filter.
            chunk_type: Optional chunk type filter.
            file_path: Optional file path filter.
            commit_sha: Optional commit SHA / index version filter.

        Returns:
            RetrievalResultSet containing ProcessedQuery, ordered RetrievalResults, and latency metrics.

        Raises:
            LexicalQueryError: If query, repository_id, or top_k are invalid.
        """
        if not repository_id or not repository_id.strip():
            raise LexicalQueryError("repository_id is required and cannot be empty or whitespace")

        if top_k <= 0:
            raise LexicalQueryError(f"top_k must be > 0, got {top_k}")

        repo_id = repository_id.strip()
        t0 = time.perf_counter()

        # 1. Query Preprocessing
        if isinstance(query, str):
            processed_query = self.preprocessor.process(query)
        elif isinstance(query, ProcessedQuery):
            processed_query = query
        else:
            raise LexicalQueryError(
                f"Query must be a string or ProcessedQuery, got {type(query).__name__}"
            )

        t1 = time.perf_counter()
        prep_latency_ms = (t1 - t0) * 1000.0

        # 2. BM25 Search Execution
        search_results = self.index.search(
            query=processed_query.normalized_query,
            repository_id=repo_id,
            top_k=top_k,
            language=language,
            chunk_type=chunk_type,
            file_path=file_path,
            commit_sha=commit_sha,
        )

        t2 = time.perf_counter()
        search_latency_ms = (t2 - t1) * 1000.0
        total_latency_ms = (t2 - t0) * 1000.0

        # 3. Result Mapping
        candidates: list[RetrievalResult] = []
        for lex_res in search_results:
            candidates.append(
                RetrievalResult(
                    chunk_id=lex_res.chunk_id,
                    score=lex_res.score,
                    rank=lex_res.rank,
                    repository_id=lex_res.repository_id,
                    commit_id=lex_res.commit_id,
                    commit_sha=lex_res.commit_sha,
                    file_path=lex_res.file_path,
                    language=lex_res.language,
                    chunk_type=lex_res.chunk_type,
                    symbol_name=lex_res.symbol_name,
                    qualified_name=lex_res.qualified_name,
                    start_line=lex_res.start_line,
                    end_line=lex_res.end_line,
                    metadata=lex_res.metadata,
                )
            )

        return RetrievalResultSet(
            query=processed_query,
            repository_id=repo_id,
            results=candidates,
            total_matches=len(candidates),
            preprocessing_latency_ms=round(prep_latency_ms, 4),
            retrieval_latency_ms=round(search_latency_ms, 4),
            total_latency_ms=round(total_latency_ms, 4),
        )
