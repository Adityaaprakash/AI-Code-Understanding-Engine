"""Context Ranker implementation for TASK-6C."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from llm.planner_models import QueryPlan

from llm.enums import (
    AnswerStyle,
    QueryIntent,
    QueryScope,
    RankingReasonCode,
    RelationshipType,
)
from llm.expansion_models import GraphExpansionCandidate
from llm.ranking_config import ContextRankingConfig
from llm.ranking_contracts import ContextRankerContract
from llm.ranking_models import (
    ContextRankingResult,
    ContextRankingScoreBreakdown,
    RankedContextCandidate,
)
from retrieval.retrieval_models import RetrievalResult


class ContextRanker(ContextRankerContract):
    """Deterministic, query-aware candidate context ranking engine for Phase 6C."""

    def rank(
        self,
        query_plan: QueryPlan,
        candidates: Sequence[GraphExpansionCandidate | RetrievalResult],
        config: ContextRankingConfig | None = None,
    ) -> ContextRankingResult:
        """Deterministically rank context candidates based on QueryPlan control signals."""
        start_time = time.perf_counter()
        cfg = config or ContextRankingConfig()

        if not candidates:
            return ContextRankingResult(
                ranked_candidates=[],
                total_candidates=0,
                ranking_latency_ms=(time.perf_counter() - start_time) * 1000.0,
                ranking_metadata={"query": query_plan.query, "candidate_count": 0},
            )

        # 1. Precompute query profile once
        query_profile = self._build_query_profile(query_plan)

        # 2. Score candidates deterministically
        scored_candidates: list[
            tuple[tuple[float, float, float, int, str, str], RankedContextCandidate]
        ] = []

        for cand_item in candidates:
            ranked_cand = self._score_candidate(cand_item, query_plan, query_profile, cfg)

            # Build deterministic tie-breaking key
            score_rounded = round(ranked_cand.final_score, cfg.tie_break_precision)
            ret_score = ranked_cand.retrieval_score or 0.0
            prov_score = ranked_cand.score_breakdown.provenance_strength
            depth = ranked_cand.traversal_depth
            rel_str = str(
                getattr(
                    ranked_cand.relationship_type,
                    "value",
                    str(ranked_cand.relationship_type),
                )
            )
            cand_id = ranked_cand.candidate_id

            sort_key: tuple[float, float, float, int, str, str] = (
                -score_rounded,
                -ret_score,
                -prov_score,
                depth,
                rel_str,
                cand_id,
            )
            scored_candidates.append((sort_key, ranked_cand))

        # 3. Sort deterministically using tie-break key
        scored_candidates.sort(key=lambda item: item[0])

        # 4. Assign 1-indexed rank positions without modifying candidates
        final_ranked_list: list[RankedContextCandidate] = []
        for idx, (_, rc) in enumerate(scored_candidates, start=1):
            updated_cand = RankedContextCandidate(
                candidate_id=rc.candidate_id,
                rank=idx,
                final_score=rc.final_score,
                score_breakdown=rc.score_breakdown,
                reason_codes=rc.reason_codes,
                node_id=rc.node_id,
                symbol_name=rc.symbol_name,
                qualified_name=rc.qualified_name,
                node_kind=rc.node_kind,
                file_path=rc.file_path,
                start_line=rc.start_line,
                end_line=rc.end_line,
                source=rc.source,
                anchor_id=rc.anchor_id,
                relationship_type=rc.relationship_type,
                traversal_depth=rc.traversal_depth,
                retrieval_chunk_id=rc.retrieval_chunk_id,
                retrieval_score=rc.retrieval_score,
                original_candidate=rc.original_candidate,
                metadata=rc.metadata,
            )
            final_ranked_list.append(updated_cand)

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return ContextRankingResult(
            ranked_candidates=final_ranked_list,
            total_candidates=len(final_ranked_list),
            ranking_latency_ms=latency_ms,
            ranking_metadata={
                "query": query_plan.query,
                "primary_intent": query_plan.primary_intent.value,
                "relationship_type": query_plan.relationship_type.value,
                "candidate_count": len(final_ranked_list),
            },
        )

    def _build_query_profile(self, query_plan: QueryPlan) -> dict[str, Any]:
        """Precompute query profile features once to avoid redundant computations."""
        targets = [t.strip().lower() for t in query_plan.target_entities if t and t.strip()]
        identifiers: set[str] = set()
        if query_plan.processed_query:
            identifiers.update(
                t.strip().lower() for t in query_plan.processed_query.identifier_tokens if t
            )
            identifiers.update(
                t.strip().lower() for t in query_plan.processed_query.qualified_name_candidates if t
            )

        return {
            "targets_lower": set(targets),
            "targets_raw": query_plan.target_entities,
            "identifiers": identifiers,
            "primary_intent": query_plan.primary_intent,
            "secondary_intents": set(query_plan.secondary_intents),
            "relationship_type": query_plan.relationship_type,
            "scope": query_plan.scope,
            "answer_style": query_plan.answer_style,
        }

    def _score_candidate(
        self,
        cand: GraphExpansionCandidate | RetrievalResult,
        query_plan: QueryPlan,
        profile: dict[str, Any],
        cfg: ContextRankingConfig,
    ) -> RankedContextCandidate:
        """Extract candidate attributes, compute individual scoring components, and weight them."""
        # Normalize attributes across GraphExpansionCandidate and RetrievalResult
        (
            cid,
            node_id,
            sym_name,
            qname,
            nkind,
            file_path,
            sline,
            eline,
            src,
            anchor_id,
            rtype,
            depth,
            ret_chunk_id,
            raw_ret_score,
            orig_cand,
            meta,
        ) = self._extract_attributes(cand)

        reason_codes: set[str] = set()

        # 1. Retrieval Relevance Score [0.0, 1.0]
        norm_ret_score = self._normalize_retrieval_score(cand, raw_ret_score, src)
        if norm_ret_score > 0.0:
            reason_codes.add(RankingReasonCode.RETRIEVAL_EVIDENCE)

        # 2. Query Entity Match Score [0.0, 1.0]
        s_entity = self._score_entity_match(sym_name, qname, file_path, profile, reason_codes)

        # 3. Intent Alignment Score [0.0, 1.0]
        s_intent = self._score_intent_alignment(nkind, rtype, profile, reason_codes)

        # 4. Relationship Alignment Score [0.0, 1.0]
        s_rel = self._score_relationship_alignment(rtype, profile, reason_codes)

        # 5. Provenance Strength Score [0.0, 1.0]
        s_prov = self._score_provenance(src, cand, reason_codes)

        # 6. Graph Proximity Score [0.0, 1.0]
        s_prox = 1.0 / (1.0 + float(depth) * cfg.graph_proximity_decay)
        if depth <= 1:
            reason_codes.add(RankingReasonCode.GRAPH_PROXIMITY)

        # 7. Scope Alignment Score [0.0, 1.0]
        s_scope = self._score_scope_alignment(sym_name, qname, file_path, profile, reason_codes)

        # 8. Locality Score [0.0, 1.0]
        s_loc = self._score_locality(file_path, profile, reason_codes)

        # Calculate weighted final score
        weights_sum = (
            cfg.weight_retrieval_relevance
            + cfg.weight_query_entity_match
            + cfg.weight_intent_alignment
            + cfg.weight_relationship_alignment
            + cfg.weight_provenance_strength
            + cfg.weight_graph_proximity
            + cfg.weight_scope_alignment
            + cfg.weight_locality
        )

        raw_sum = (
            cfg.weight_retrieval_relevance * norm_ret_score
            + cfg.weight_query_entity_match * s_entity
            + cfg.weight_intent_alignment * s_intent
            + cfg.weight_relationship_alignment * s_rel
            + cfg.weight_provenance_strength * s_prov
            + cfg.weight_graph_proximity * s_prox
            + cfg.weight_scope_alignment * s_scope
            + cfg.weight_locality * s_loc
        )

        final_score = raw_sum / weights_sum if weights_sum > 0.0 else 0.0

        # Adjust for AnswerStyle if applicable
        if (
            query_plan.answer_style == AnswerStyle.CODE_LOCATION
            and (sline is not None or file_path)
        ) or (
            query_plan.answer_style == AnswerStyle.RELATIONSHIP and rtype != RelationshipType.NONE
        ):
            final_score = min(1.0, final_score * 1.05)

        sorted_reasons = sorted(reason_codes)
        if not sorted_reasons:
            sorted_reasons = [RankingReasonCode.SUPPORTING_CONTEXT]

        breakdown = ContextRankingScoreBreakdown(
            retrieval_relevance=norm_ret_score,
            query_entity_match=s_entity,
            intent_alignment=s_intent,
            relationship_alignment=s_rel,
            provenance_strength=s_prov,
            graph_proximity=s_prox,
            scope_alignment=s_scope,
            locality=s_loc,
        )

        return RankedContextCandidate(
            candidate_id=cid,
            rank=0,  # assigned during final sorting step
            final_score=final_score,
            score_breakdown=breakdown,
            reason_codes=sorted_reasons,
            node_id=node_id,
            symbol_name=sym_name,
            qualified_name=qname,
            node_kind=nkind,
            file_path=file_path,
            start_line=sline,
            end_line=eline,
            source=src,
            anchor_id=anchor_id,
            relationship_type=rtype,
            traversal_depth=depth,
            retrieval_chunk_id=ret_chunk_id,
            retrieval_score=raw_ret_score,
            original_candidate=orig_cand,
            metadata=meta,
        )

    def _extract_attributes(
        self, cand: GraphExpansionCandidate | RetrievalResult
    ) -> tuple[
        str,
        str | None,
        str | None,
        str | None,
        str | None,
        str | None,
        int | None,
        int | None,
        str,
        str | None,
        RelationshipType,
        int,
        str | None,
        float | None,
        GraphExpansionCandidate | RetrievalResult,
        dict[str, Any],
    ]:
        """Extract uniform candidate fields from either GraphExpansionCandidate or RetrievalResult."""
        if isinstance(cand, GraphExpansionCandidate):
            return (
                cand.candidate_id,
                cand.node_id,
                cand.symbol_name,
                cand.qualified_name,
                cand.node_kind,
                cand.file_path,
                cand.start_line,
                cand.end_line,
                cand.source,
                cand.anchor_id,
                cand.relationship_type,
                cand.traversal_depth,
                cand.retrieval_chunk_id,
                cand.metadata.get("retrieval_score"),
                cand,
                cand.metadata,
            )
        elif isinstance(cand, RetrievalResult):
            # Formulate source string from RetrievalResult
            src_str = "RETRIEVAL"
            if cand.sources:
                src_names = [s.value.upper() for s in cand.sources]
                src_str = f"RETRIEVAL_{'+'.join(src_names)}"

            nkind_str = (
                cand.chunk_type.value if hasattr(cand.chunk_type, "value") else str(cand.chunk_type)
            )
            node_id = cand.metadata.get("symbol_id") or cand.chunk_id

            return (
                cand.chunk_id,
                node_id,
                cand.symbol_name,
                cand.qualified_name,
                nkind_str,
                cand.file_path,
                cand.start_line,
                cand.end_line,
                src_str,
                None,
                RelationshipType.NONE,
                0,  # Direct retrieval is depth 0
                cand.chunk_id,
                cand.rerank_score or cand.fused_score or cand.score,
                cand,
                cand.metadata,
            )
        else:
            # Fallback for dynamic objects
            cid = getattr(cand, "candidate_id", None) or getattr(cand, "chunk_id", "unknown_cand")
            return (
                cid,
                getattr(cand, "node_id", None),
                getattr(cand, "symbol_name", None),
                getattr(cand, "qualified_name", None),
                str(getattr(cand, "node_kind", getattr(cand, "chunk_type", "SYMBOL"))),
                getattr(cand, "file_path", None),
                getattr(cand, "start_line", None),
                getattr(cand, "end_line", None),
                str(getattr(cand, "source", "UNKNOWN")),
                getattr(cand, "anchor_id", None),
                getattr(cand, "relationship_type", RelationshipType.NONE),
                int(getattr(cand, "traversal_depth", 0)),
                getattr(cand, "retrieval_chunk_id", None),
                getattr(cand, "score", None),
                cand,
                getattr(cand, "metadata", {}),
            )

    def _normalize_retrieval_score(
        self,
        cand: GraphExpansionCandidate | RetrievalResult,
        raw_score: float | None,
        source: str,
    ) -> float:
        """Deterministically normalize Phase 5 retrieval score into [0.0, 1.0]."""
        if isinstance(cand, RetrievalResult):
            if cand.rerank_score is not None:
                return min(1.0, max(0.0, cand.rerank_score))
            if cand.fused_score is not None:
                # Max RRF score for rank 1 is 1.0 / (60 + 1) ~= 0.016393
                # Scale fused_score up deterministically
                return min(1.0, cand.fused_score * 61.0)
            if cand.score is not None:
                val = cand.score
                if 0.0 <= val <= 1.0:
                    return val
                # Sigmoid bound for arbitrary scores
                return val / (1.0 + abs(val))
            return 0.5
        elif isinstance(cand, GraphExpansionCandidate):
            if raw_score is not None:
                val = raw_score
                return val if 0.0 <= val <= 1.0 else val / (1.0 + abs(val))
            if "RETRIEVAL" in source:
                return 0.5
            return 0.0
        return 0.0

    def _score_entity_match(
        self,
        sym_name: str | None,
        qname: str | None,
        file_path: str | None,
        profile: dict[str, Any],
        reason_codes: set[str],
    ) -> float:
        """Score alignment with explicit query target entities/symbols."""
        targets = profile["targets_lower"]
        if not targets:
            return 0.0

        sym_lower = sym_name.lower().strip() if sym_name else ""
        qname_lower = qname.lower().strip() if qname else ""
        file_lower = file_path.lower().strip() if file_path else ""

        # Exact match on qualified name or simple symbol name
        for target in targets:
            if qname_lower and target == qname_lower:
                reason_codes.add(RankingReasonCode.DIRECT_QUERY_TARGET)
                reason_codes.add(RankingReasonCode.SAME_SYMBOL)
                return 1.0
            if sym_lower and target == sym_lower:
                reason_codes.add(RankingReasonCode.DIRECT_QUERY_TARGET)
                reason_codes.add(RankingReasonCode.SAME_SYMBOL)
                return 1.0
            if file_lower and target in file_lower:
                reason_codes.add(RankingReasonCode.SAME_FILE)
                return 0.8

        # Identifier candidate token match
        identifiers = profile["identifiers"]
        if sym_lower and sym_lower in identifiers:
            reason_codes.add(RankingReasonCode.SAME_SYMBOL)
            return 0.7

        # Substring target match
        for target in targets:
            if target in sym_lower or target in qname_lower:
                reason_codes.add(RankingReasonCode.SAME_SYMBOL)
                return 0.5

        return 0.0

    def _score_intent_alignment(
        self,
        nkind: str | None,
        rtype: RelationshipType,
        profile: dict[str, Any],
        reason_codes: set[str],
    ) -> float:
        """Score candidate alignment with primary and secondary query intents."""
        primary = profile["primary_intent"]
        secondary = profile["secondary_intents"]

        # Primary intent rules
        if primary in (QueryIntent.DEPENDENCY, QueryIntent.EXPLANATION):
            if rtype in (
                RelationshipType.CALLS,
                RelationshipType.CALLERS,
                RelationshipType.DEPENDENCIES,
                RelationshipType.DEPENDENTS,
                RelationshipType.USES,
                RelationshipType.IMPORTS,
            ):
                reason_codes.add(RankingReasonCode.PRIMARY_INTENT_MATCH)
                return 1.0
        elif primary == QueryIntent.IMPACT:
            if rtype == RelationshipType.IMPACT or rtype != RelationshipType.NONE:
                reason_codes.add(RankingReasonCode.PRIMARY_INTENT_MATCH)
                return 1.0
        elif primary == QueryIntent.SYMBOL:
            if nkind in ("FUNCTION", "METHOD", "CLASS", "INTERFACE"):
                reason_codes.add(RankingReasonCode.PRIMARY_INTENT_MATCH)
                return 1.0
        elif primary == QueryIntent.ARCHITECTURE:
            if nkind in ("MODULE", "FILE", "PACKAGE", "CLASS"):
                reason_codes.add(RankingReasonCode.PRIMARY_INTENT_MATCH)
                return 1.0

        # Secondary intent check
        for sec in secondary:
            if (
                sec in (QueryIntent.DEPENDENCY, QueryIntent.IMPACT)
                and rtype != RelationshipType.NONE
            ):
                reason_codes.add(RankingReasonCode.SECONDARY_INTENT_MATCH)
                return 0.7

        return 0.3

    def _score_relationship_alignment(
        self,
        rtype: RelationshipType,
        profile: dict[str, Any],
        reason_codes: set[str],
    ) -> float:
        """Score structural relationship type alignment."""
        query_rel = profile["relationship_type"]
        if query_rel == RelationshipType.NONE:
            return 0.5

        if rtype == query_rel:
            reason_codes.add(RankingReasonCode.RELATIONSHIP_MATCH)
            return 1.0

        # Structural complement checks
        if query_rel == RelationshipType.CALLERS and rtype == RelationshipType.CALLS:
            reason_codes.add(RankingReasonCode.RELATIONSHIP_MATCH)
            return 0.7
        if query_rel == RelationshipType.CALLS and rtype == RelationshipType.CALLERS:
            reason_codes.add(RankingReasonCode.RELATIONSHIP_MATCH)
            return 0.7
        if query_rel == RelationshipType.DEPENDENTS and rtype == RelationshipType.DEPENDENCIES:
            reason_codes.add(RankingReasonCode.RELATIONSHIP_MATCH)
            return 0.7

        if rtype != RelationshipType.NONE:
            return 0.3
        return 0.0

    def _score_provenance(
        self,
        source: str,
        cand: GraphExpansionCandidate | RetrievalResult,
        reason_codes: set[str],
    ) -> float:
        """Score provenance evidence strength based on multi-source flags."""
        if source == "RETRIEVAL+GRAPH_EXPANSION" or "RETRIEVAL+" in source:
            reason_codes.add(RankingReasonCode.MULTI_SOURCE_EVIDENCE)
            return 1.0

        if isinstance(cand, RetrievalResult) and len(cand.sources) > 1:
            reason_codes.add(RankingReasonCode.MULTI_SOURCE_EVIDENCE)
            return 0.9

        if "RETRIEVAL" in source:
            reason_codes.add(RankingReasonCode.RETRIEVAL_EVIDENCE)
            return 0.6

        if "GRAPH" in source:
            reason_codes.add(RankingReasonCode.GRAPH_EVIDENCE)
            return 0.5

        return 0.3

    def _score_scope_alignment(
        self,
        sym_name: str | None,
        qname: str | None,
        file_path: str | None,
        profile: dict[str, Any],
        reason_codes: set[str],
    ) -> float:
        """Score QueryPlan scope constraint alignment."""
        scope = profile["scope"]

        if scope == QueryScope.SYMBOL:
            if sym_name or qname:
                targets = profile["targets_lower"]
                if sym_name and sym_name.lower() in targets:
                    reason_codes.add(RankingReasonCode.SCOPE_MATCH)
                    return 1.0
                return 0.7
        elif scope == QueryScope.FILE:
            if file_path:
                reason_codes.add(RankingReasonCode.SCOPE_MATCH)
                return 0.9
        elif scope in (QueryScope.MODULE, QueryScope.PACKAGE):
            reason_codes.add(RankingReasonCode.SCOPE_MATCH)
            return 0.8

        return 0.5

    def _score_locality(
        self,
        file_path: str | None,
        profile: dict[str, Any],
        reason_codes: set[str],
    ) -> float:
        """Score code locality relative to query target entities."""
        if not file_path:
            return 0.0

        file_lower = file_path.lower()
        targets = profile["targets_lower"]

        for target in targets:
            if target in file_lower:
                reason_codes.add(RankingReasonCode.SAME_FILE)
                return 1.0

        return 0.2
