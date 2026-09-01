"""Phase 5 TASK-5F Deterministic Baseline Candidate Reranker implementation."""

import time

from retrieval.contracts import RerankerContract
from retrieval.exceptions import (
    RerankerConfigurationError,
    RerankerInputError,
)
from retrieval.query_models import ProcessedQuery
from retrieval.query_processor import QueryPreprocessor
from retrieval.retrieval_models import RetrievalResult, RetrievalResultSet


class DeterministicReranker(RerankerContract):
    """Deterministic local feature-based candidate reranker for CodeLens AI Phase 5."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        rerank_top_k: int = 50,
        query_preprocessor: QueryPreprocessor | None = None,
    ) -> None:
        """Initialize DeterministicReranker.

        Args:
            weights: Optional dictionary of feature weights (default values sum to 1.0).
            rerank_top_k: Maximum candidate pool size from 5E to consider for reranking (default 50).
            query_preprocessor: Optional QueryPreprocessor instance for query string inputs.
        """
        if rerank_top_k <= 0:
            raise RerankerConfigurationError(f"rerank_top_k must be > 0, got {rerank_top_k}")

        self.rerank_top_k = rerank_top_k
        self.preprocessor = query_preprocessor or QueryPreprocessor()

        default_weights = {
            "exact_symbol": 0.35,
            "qualified_symbol": 0.20,
            "token_overlap": 0.25,
            "source_agreement": 0.10,
            "rrf_prior": 0.10,
        }
        if weights:
            for k, v in weights.items():
                if k not in default_weights:
                    raise RerankerConfigurationError(f"Unknown reranker feature weight: {k}")
                if v < 0.0:
                    raise RerankerConfigurationError(
                        f"Weight for feature '{k}' must be >= 0.0, got {v}"
                    )
            self.weights = {**default_weights, **weights}
        else:
            self.weights = default_weights

    def rerank(
        self,
        query: str | ProcessedQuery,
        results: RetrievalResultSet,
        top_k: int = 10,
    ) -> RetrievalResultSet:
        """Rerank candidate results from CandidateFusionEngine using deterministic feature scoring.

        Args:
            query: Raw query string or preprocessed ProcessedQuery.
            results: RetrievalResultSet from 5E (CandidateFusionEngine).
            top_k: Maximum number of reranked candidates to return (must be > 0).

        Returns:
            RetrievalResultSet containing ProcessedQuery and reranked RetrievalResults.

        Raises:
            RerankerInputError: If top_k <= 0 or query mismatches.
            RerankerConfigurationError: If reranker options are invalid.
        """
        if top_k <= 0:
            raise RerankerInputError(f"top_k must be > 0, got {top_k}")

        start_time = time.perf_counter()

        # 1. Resolve ProcessedQuery
        if isinstance(query, str):
            processed_q = self.preprocessor.process(query)
        else:
            processed_q = query

        # 2. Query consistency check
        if results.query and results.query.normalized_query:
            if results.query.normalized_query != processed_q.normalized_query:
                raise RerankerInputError(
                    "Query mismatch between provided query and result set query"
                )

        # 3. Empty results handling
        if not results.results:
            rerank_latency = (time.perf_counter() - start_time) * 1000.0
            tot_lat = results.total_latency_ms + rerank_latency
            return RetrievalResultSet(
                query=processed_q,
                repository_id=results.repository_id,
                results=[],
                total_matches=0,
                preprocessing_latency_ms=results.preprocessing_latency_ms,
                retrieval_latency_ms=results.retrieval_latency_ms,
                fusion_latency_ms=results.fusion_latency_ms,
                reranking_latency_ms=rerank_latency,
                total_latency_ms=tot_lat,
            )

        # 4. Truncate to candidate pool for reranking (up to rerank_top_k)
        candidate_pool = results.results[: self.rerank_top_k]

        max_rrf = max(
            (item.fused_score if item.fused_score is not None else item.score for item in candidate_pool),
            default=1.0,
        )
        if max_rrf <= 0.0:
            max_rrf = 1.0

        target_symbol = (
            processed_q.identifier_tokens[0].lower()
            if processed_q.identifier_tokens
            else processed_q.normalized_query.lower()
        )
        query_tokens = set(t.lower() for t in processed_q.tokens)


        scored_candidates: list[tuple[float, RetrievalResult]] = []

        for item in candidate_pool:
            # Feature 1: Exact symbol match
            f_exact_symbol = 0.0
            if target_symbol and item.symbol_name:
                if item.symbol_name.lower() == target_symbol:
                    f_exact_symbol = 1.0

            # Feature 2: Qualified symbol match
            f_qualified_symbol = 0.0
            if target_symbol and item.qualified_name:
                if target_symbol in item.qualified_name.lower():
                    f_qualified_symbol = 1.0

            # Feature 3: Token overlap ratio
            candidate_text_tokens: set[str] = set()
            if item.symbol_name:
                candidate_text_tokens.add(item.symbol_name.lower())
            if item.qualified_name:
                candidate_text_tokens.update(item.qualified_name.lower().split("."))
            if item.file_path:
                candidate_text_tokens.update(
                    item.file_path.lower().replace("/", " ").replace(".", " ").split()
                )
            if "code_content" in item.metadata and isinstance(item.metadata["code_content"], str):
                candidate_text_tokens.update(item.metadata["code_content"].lower().split())

            f_token_overlap = 0.0
            if query_tokens and candidate_text_tokens:
                overlap = query_tokens.intersection(candidate_text_tokens)
                f_token_overlap = len(overlap) / len(query_tokens)

            # Feature 4: Source agreement ratio (max 3 sources: bm25, vector, graph)
            num_sources = len(item.sources)
            f_source_agreement = min(float(num_sources) / 3.0, 1.0)

            # Feature 5: RRF prior
            raw_rrf = item.fused_score if item.fused_score is not None else item.score
            f_rrf_prior = min(max(raw_rrf / max_rrf, 0.0), 1.0)

            # Calculate weighted score
            rerank_score = (
                self.weights["exact_symbol"] * f_exact_symbol
                + self.weights["qualified_symbol"] * f_qualified_symbol
                + self.weights["token_overlap"] * f_token_overlap
                + self.weights["source_agreement"] * f_source_agreement
                + self.weights["rrf_prior"] * f_rrf_prior
            )

            scored_candidates.append((rerank_score, item))

        # Sort deterministically: rerank_score DESC, chunk_id ASC
        scored_candidates.sort(key=lambda pair: (-pair[0], pair[1].chunk_id))

        top_candidates = scored_candidates[:top_k]

        # Construct reranked RetrievalResult objects preserving ALL original evidence
        reranked_results: list[RetrievalResult] = []
        for rank_idx, (r_score, item) in enumerate(top_candidates, start=1):
            reranked_item = RetrievalResult(
                chunk_id=item.chunk_id,
                score=r_score,
                rank=rank_idx,
                repository_id=item.repository_id,
                commit_id=item.commit_id,
                commit_sha=item.commit_sha,
                file_path=item.file_path,
                language=item.language,
                chunk_type=item.chunk_type,
                symbol_name=item.symbol_name,
                qualified_name=item.qualified_name,
                start_line=item.start_line,
                end_line=item.end_line,
                metadata=item.metadata,
                sources=item.sources,
                bm25_rank=item.bm25_rank,
                vector_rank=item.vector_rank,
                graph_rank=item.graph_rank,
                bm25_score=item.bm25_score,
                vector_score=item.vector_score,
                graph_score=item.graph_score,
                fused_score=item.fused_score,
                rerank_score=r_score,
            )
            reranked_results.append(reranked_item)

        rerank_latency = (time.perf_counter() - start_time) * 1000.0
        tot_lat = results.total_latency_ms + rerank_latency

        return RetrievalResultSet(
            query=processed_q,
            repository_id=results.repository_id,
            results=reranked_results,
            total_matches=len(results.results),
            preprocessing_latency_ms=results.preprocessing_latency_ms,
            retrieval_latency_ms=results.retrieval_latency_ms,
            fusion_latency_ms=results.fusion_latency_ms,
            reranking_latency_ms=rerank_latency,
            total_latency_ms=tot_lat,
        )
