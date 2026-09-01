"""Phase 5 TASK-5E Candidate Fusion Engine implementation (Reciprocal Rank Fusion - RRF)."""

import time
from typing import TYPE_CHECKING, Any

from retrieval.contracts import CandidateFusionContract
from retrieval.enums import ChunkType, RetrievalSource
from retrieval.exceptions import (
    FusionQueryError,
    FusionRepositoryError,
    FusionVersionError,
)
from retrieval.retrieval_models import RetrievalResult, RetrievalResultSet

if TYPE_CHECKING:
    from code_analyzer.parsers.models import Language


class _CandidateAccumulator:
    """Internal helper accumulator for merging evidence of a single candidate chunk across retrieval branches."""

    def __init__(self, base_result: RetrievalResult) -> None:
        self.chunk_id: str = base_result.chunk_id
        self.repository_id: str = base_result.repository_id
        self.commit_id: str | None = base_result.commit_id
        self.commit_sha: str | None = base_result.commit_sha
        self.file_path: str = base_result.file_path
        self.language: Language = base_result.language
        self.chunk_type: ChunkType = base_result.chunk_type
        self.symbol_name: str | None = base_result.symbol_name
        self.qualified_name: str | None = base_result.qualified_name
        self.start_line: int | None = base_result.start_line
        self.end_line: int | None = base_result.end_line
        self.metadata: dict[str, Any] = dict(base_result.metadata)

        self.sources: list[RetrievalSource] = []
        self.bm25_rank: int | None = None
        self.vector_rank: int | None = None
        self.graph_rank: int | None = None
        self.bm25_score: float | None = None
        self.vector_score: float | None = None
        self.graph_score: float | None = None
        self.fused_score: float = 0.0

    def add_evidence(
        self,
        source: RetrievalSource,
        rank: int,
        raw_score: float,
        rrf_k: int,
        result: RetrievalResult,
    ) -> None:
        """Accumulate RRF contribution and preserve source evidence from a retrieval branch."""
        if source not in self.sources:
            self.sources.append(source)

        contribution = 1.0 / (rrf_k + rank)
        self.fused_score += contribution

        if source == RetrievalSource.BM25:
            self.bm25_rank = rank
            self.bm25_score = raw_score
        elif source == RetrievalSource.VECTOR:
            self.vector_rank = rank
            self.vector_score = raw_score
        elif source == RetrievalSource.GRAPH:
            self.graph_rank = rank
            self.graph_score = raw_score

        # Safely merge extra metadata from other sources without overwriting existing keys
        for k, v in result.metadata.items():
            if k not in self.metadata:
                self.metadata[k] = v


class CandidateFusionEngine(CandidateFusionContract):
    """Deterministic Candidate Fusion Service executing Reciprocal Rank Fusion (RRF)."""

    def __init__(self, rrf_k: int = 60) -> None:
        if rrf_k <= 0:
            raise FusionQueryError(f"rrf_k must be > 0, got {rrf_k}")
        self.rrf_k = rrf_k

    def fuse(
        self,
        lexical_results: RetrievalResultSet | None = None,
        vector_results: RetrievalResultSet | None = None,
        graph_results: RetrievalResultSet | None = None,
        top_k: int = 10,
    ) -> RetrievalResultSet:
        """Fuse candidate result sets from independent retrieval branches using RRF.

        Args:
            lexical_results: Optional RetrievalResultSet from Lexical (BM25) retriever.
            vector_results: Optional RetrievalResultSet from Vector retriever.
            graph_results: Optional RetrievalResultSet from Graph retriever.
            top_k: Maximum number of fused ranked candidates to return (must be > 0).

        Returns:
            RetrievalResultSet containing unified ProcessedQuery, fused RetrievalResults, and latency metrics.

        Raises:
            FusionQueryError: If top_k <= 0 or query strings conflict.
            FusionRepositoryError: If input result sets belong to different repositories.
            FusionVersionError: If input result sets belong to conflicting commit SHAs.
        """
        if top_k <= 0:
            raise FusionQueryError(f"top_k must be > 0, got {top_k}")

        start_time = time.perf_counter()

        # Collect input branches
        inputs: list[tuple[RetrievalSource, RetrievalResultSet]] = []
        if lexical_results is not None:
            inputs.append((RetrievalSource.BM25, lexical_results))
        if vector_results is not None:
            inputs.append((RetrievalSource.VECTOR, vector_results))
        if graph_results is not None:
            inputs.append((RetrievalSource.GRAPH, graph_results))

        if not inputs:
            raise FusionQueryError(
                "At least one RetrievalResultSet must be provided for candidate fusion"
            )

        # 1. Validate Repository Isolation & Commit SHA Consistency & Query Consistency across branches
        repo_ids = {res.repository_id for _, res in inputs if res.repository_id}
        if len(repo_ids) > 1:
            raise FusionRepositoryError(
                f"Conflicting repository IDs in fusion inputs: {sorted(repo_ids)}"
            )
        target_repo_id = next(iter(repo_ids)) if repo_ids else ""
        if not target_repo_id:
            raise FusionRepositoryError("repository_id cannot be empty")

        # Commit SHA consistency validation
        commit_shas: set[str] = set()
        for _, res in inputs:
            if res.query and res.query.metadata.get("commit_sha"):
                commit_shas.add(str(res.query.metadata["commit_sha"]))
            for item in res.results:
                if item.commit_sha:
                    commit_shas.add(item.commit_sha)

        if len(commit_shas) > 1:
            raise FusionVersionError(
                f"Conflicting commit SHAs in fusion inputs: {sorted(commit_shas)}"
            )

        # Query consistency validation
        query_texts = {
            res.query.normalized_query
            for _, res in inputs
            if res.query and res.query.normalized_query
        }
        if len(query_texts) > 1:
            raise FusionQueryError(
                f"Conflicting queries across retrieval branches: {sorted(query_texts)}"
            )

        # Resolve primary ProcessedQuery
        primary_query = inputs[0][1].query

        # Check if all branches are empty of results
        total_input_results = sum(len(res.results) for _, res in inputs)
        if total_input_results == 0:
            fusion_latency_ms = (time.perf_counter() - start_time) * 1000.0
            prep_lat = max((res.preprocessing_latency_ms for _, res in inputs), default=0.0)
            ret_lat = max((res.retrieval_latency_ms for _, res in inputs), default=0.0)
            tot_lat = (
                max((res.total_latency_ms for _, res in inputs), default=0.0) + fusion_latency_ms
            )
            return RetrievalResultSet(
                query=primary_query,
                repository_id=target_repo_id,
                results=[],
                total_matches=0,
                preprocessing_latency_ms=prep_lat,
                retrieval_latency_ms=ret_lat,
                fusion_latency_ms=fusion_latency_ms,
                total_latency_ms=tot_lat,
            )

        # 2. Perform RRF Accumulation across candidates
        accumulators: dict[str, _CandidateAccumulator] = {}

        for source, res_set in inputs:
            for idx, item in enumerate(res_set.results, start=1):
                rank = item.rank if item.rank > 0 else idx
                chunk_id = item.chunk_id

                if chunk_id not in accumulators:
                    accumulators[chunk_id] = _CandidateAccumulator(item)

                accumulators[chunk_id].add_evidence(
                    source=source,
                    rank=rank,
                    raw_score=item.score,
                    rrf_k=self.rrf_k,
                    result=item,
                )

        # 3. Deterministic Sorting
        # Primary: fused_score DESC, Secondary: chunk_id ASC
        sorted_accs = sorted(
            accumulators.values(),
            key=lambda acc: (-acc.fused_score, acc.chunk_id),
        )

        total_matches = len(sorted_accs)
        top_accs = sorted_accs[:top_k]

        # 4. Construct Ranked Results
        fused_results: list[RetrievalResult] = []
        for rank_idx, acc in enumerate(top_accs, start=1):
            fused_result = RetrievalResult(
                chunk_id=acc.chunk_id,
                score=acc.fused_score,
                rank=rank_idx,
                repository_id=acc.repository_id,
                commit_id=acc.commit_id,
                commit_sha=acc.commit_sha,
                file_path=acc.file_path,
                language=acc.language,
                chunk_type=acc.chunk_type,
                symbol_name=acc.symbol_name,
                qualified_name=acc.qualified_name,
                start_line=acc.start_line,
                end_line=acc.end_line,
                metadata=acc.metadata,
                sources=acc.sources,
                bm25_rank=acc.bm25_rank,
                vector_rank=acc.vector_rank,
                graph_rank=acc.graph_rank,
                bm25_score=acc.bm25_score,
                vector_score=acc.vector_score,
                graph_score=acc.graph_score,
                fused_score=acc.fused_score,
            )
            fused_results.append(fused_result)

        # 5. Latency metrics
        fusion_latency_ms = (time.perf_counter() - start_time) * 1000.0
        prep_lat = max((res.preprocessing_latency_ms for _, res in inputs), default=0.0)
        ret_lat = max((res.retrieval_latency_ms for _, res in inputs), default=0.0)
        tot_lat = max((res.total_latency_ms for _, res in inputs), default=0.0) + fusion_latency_ms

        return RetrievalResultSet(
            query=primary_query,
            repository_id=target_repo_id,
            results=fused_results,
            total_matches=total_matches,
            preprocessing_latency_ms=prep_lat,
            retrieval_latency_ms=ret_lat,
            fusion_latency_ms=fusion_latency_ms,
            total_latency_ms=tot_lat,
        )
