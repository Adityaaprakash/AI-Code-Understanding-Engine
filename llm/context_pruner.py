"""Context Pruner implementation for TASK-6D Context Deduplication & Pruning."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from llm.planner_models import QueryPlan

from llm.enums import PruningReasonCode, RankingReasonCode
from llm.pruning_config import ContextPruningConfig
from llm.pruning_contracts import ContextPrunerContract
from llm.pruning_models import ContextPruningResult, PrunedCandidateRecord
from llm.ranking_models import (
    ContextRankingResult,
    ContextRankingScoreBreakdown,
    RankedContextCandidate,
)


class ContextPruner(ContextPrunerContract):
    """Deterministic, explainable, provenance-preserving context deduplication and pruning engine."""

    def prune(
        self,
        query_plan: QueryPlan,
        candidates: Sequence[RankedContextCandidate] | ContextRankingResult,
        config: ContextPruningConfig | None = None,
    ) -> ContextPruningResult:
        """Deterministically deduplicate and prune ranked context candidates based on QueryPlan signals."""
        start_time = time.perf_counter()
        cfg = config or ContextPruningConfig()

        # Extract candidates sequence
        if isinstance(candidates, ContextRankingResult):
            input_list = list(candidates.ranked_candidates)
        else:
            input_list = list(candidates)

        if not input_list:
            return ContextPruningResult(
                retained_candidates=[],
                pruned_candidates=[],
                input_count=0,
                deduplicated_count=0,
                pruned_count=0,
                output_count=0,
                pruning_latency_ms=(time.perf_counter() - start_time) * 1000.0,
                pruning_metadata={"query": query_plan.query, "retained_count": 0},
            )

        # 1. Pre-sort input candidates by stable key to guarantee permutation invariance
        sorted_inputs = sorted(input_list, key=self._build_candidate_sort_key)

        # 2. Stage 1 & 2: Deduplication and Evidence Merging
        surviving_dedup, dedup_records = self._deduplicate_candidates(
            sorted_inputs, query_plan, cfg
        )

        # 3. Stage 3: Structural Protection Identification & Limit Pruning
        retained, pruning_records = self._prune_redundant_candidates(
            surviving_dedup, query_plan, cfg
        )

        # Combine all audit records
        all_pruned_records = dedup_records + pruning_records

        # 4. Final deterministic re-ranking and indexing (1-indexed rank)
        final_retained = self._format_final_candidates(retained, cfg)

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return ContextPruningResult(
            retained_candidates=final_retained,
            pruned_candidates=all_pruned_records,
            input_count=len(input_list),
            deduplicated_count=len(dedup_records),
            pruned_count=len(pruning_records),
            output_count=len(final_retained),
            pruning_latency_ms=latency_ms,
            pruning_metadata={
                "query": query_plan.query,
                "primary_intent": query_plan.primary_intent.value,
                "input_count": len(input_list),
                "deduplicated_count": len(dedup_records),
                "pruned_count": len(pruning_records),
                "retained_count": len(final_retained),
            },
        )

    def _build_candidate_sort_key(
        self, cand: RankedContextCandidate
    ) -> tuple[float, float, float, int, str, str]:
        """Stable deterministic tie-breaking key independent of input ordering."""
        score_rounded = round(cand.final_score, 6)
        prov_score = cand.score_breakdown.provenance_strength
        ret_score = cand.retrieval_score or 0.0
        depth = cand.traversal_depth
        rel_str = str(getattr(cand.relationship_type, "value", str(cand.relationship_type)))
        cand_id = cand.candidate_id

        return (
            -score_rounded,
            -prov_score,
            -ret_score,
            depth,
            rel_str,
            cand_id,
        )

    def _deduplicate_candidates(
        self,
        candidates: list[RankedContextCandidate],
        query_plan: QueryPlan,
        cfg: ContextPruningConfig,
    ) -> tuple[list[RankedContextCandidate], list[PrunedCandidateRecord]]:
        """Perform exact, logical, and near-duplicate grouping and merge evidence deterministically."""
        if (
            not cfg.enable_exact_deduplication
            and not cfg.enable_logical_deduplication
            and not cfg.enable_near_duplicate_detection
        ):
            return list(candidates), []

        groups: list[list[RankedContextCandidate]] = []
        assigned = set()

        for i, c1 in enumerate(candidates):
            if c1.candidate_id in assigned:
                continue

            current_group = [c1]
            assigned.add(c1.candidate_id)

            for j in range(i + 1, len(candidates)):
                c2 = candidates[j]
                if c2.candidate_id in assigned:
                    continue

                if self._are_duplicates(c1, c2, cfg):
                    current_group.append(c2)
                    assigned.add(c2.candidate_id)

            groups.append(current_group)

        survivors: list[RankedContextCandidate] = []
        dedup_records: list[PrunedCandidateRecord] = []

        for group in groups:
            if len(group) == 1:
                survivors.append(group[0])
                continue

            # Select survivor and merge evidence
            survivor, non_survivors, reason_code = self._merge_candidate_group(
                group, query_plan, cfg
            )
            survivors.append(survivor)

            for ns in non_survivors:
                dedup_records.append(
                    PrunedCandidateRecord(
                        candidate_id=ns.candidate_id,
                        pruning_reason=reason_code,
                        details=f"Merged into winning candidate '{survivor.candidate_id}' via {reason_code.value}.",
                        winning_candidate_id=survivor.candidate_id,
                        original_candidate=ns,
                        metadata={"survivor_id": survivor.candidate_id},
                    )
                )

        return survivors, dedup_records

    def _are_duplicates(
        self,
        c1: RankedContextCandidate,
        c2: RankedContextCandidate,
        cfg: ContextPruningConfig,
    ) -> bool:
        """Deterministically determine if two candidates are exact, logical, or near duplicates."""
        # 1. Exact Duplicate Check
        if cfg.enable_exact_deduplication:
            if c1.candidate_id == c2.candidate_id:
                return True
            if (
                c1.retrieval_chunk_id
                and c2.retrieval_chunk_id
                and c1.retrieval_chunk_id == c2.retrieval_chunk_id
            ):
                return True
            if (
                c1.file_path
                and c2.file_path
                and c1.file_path == c2.file_path
                and c1.start_line is not None
                and c2.start_line is not None
                and c1.start_line == c2.start_line
                and c1.end_line == c2.end_line
            ):
                return True

        # 2. Logical Duplicate Check
        if cfg.enable_logical_deduplication:
            # Same non-empty qualified name
            if (
                c1.qualified_name
                and c2.qualified_name
                and c1.qualified_name.strip().lower() == c2.qualified_name.strip().lower()
            ):
                return True
            # Same non-empty symbol ID / node ID
            if c1.node_id and c2.node_id and c1.node_id == c2.node_id and c1.node_id != "unknown":
                return True

        # 3. Near Duplicate Check (Deterministic Token/Identifier Fingerprint)
        if cfg.enable_near_duplicate_detection:
            if self._is_near_duplicate(c1, c2, cfg.near_duplicate_threshold):
                return True

        return False

    def _is_near_duplicate(
        self, c1: RankedContextCandidate, c2: RankedContextCandidate, threshold: float
    ) -> bool:
        """Deterministic Jaccard similarity across candidate metadata tokens."""
        if not c1.file_path or not c2.file_path or c1.file_path != c2.file_path:
            return False

        # Compute overlap of metadata/symbol identifiers
        set1 = self._candidate_token_set(c1)
        set2 = self._candidate_token_set(c2)

        if not set1 or not set2:
            return False

        intersection = set1.intersection(set2)
        union = set1.union(set2)

        jaccard = len(intersection) / float(len(union))
        return jaccard >= threshold

    def _candidate_token_set(self, cand: RankedContextCandidate) -> set[str]:
        """Extract deterministic token set from candidate fields for similarity matching."""
        tokens: set[str] = set()
        if cand.symbol_name:
            tokens.add(cand.symbol_name.lower())
        if cand.qualified_name:
            tokens.update(cand.qualified_name.lower().split("."))
        if cand.node_kind:
            tokens.add(cand.node_kind.lower())
        if cand.start_line is not None and cand.end_line is not None:
            tokens.add(f"lines:{cand.start_line}-{cand.end_line}")
        return tokens

    def _merge_candidate_group(
        self,
        group: list[RankedContextCandidate],
        query_plan: QueryPlan,
        cfg: ContextPruningConfig,
    ) -> tuple[RankedContextCandidate, list[RankedContextCandidate], PruningReasonCode]:
        """Select surviving candidate and merge evidence/provenance from non-surviving group members."""
        # Sort group by survivor criteria
        sorted_group = sorted(group, key=self._build_candidate_sort_key)
        survivor = sorted_group[0]
        non_survivors = sorted_group[1:]

        # Classify deduplication reason code
        reason_code = PruningReasonCode.EXACT_DUPLICATE
        for ns in non_survivors:
            if survivor.candidate_id == ns.candidate_id:
                reason_code = PruningReasonCode.EXACT_DUPLICATE
            elif survivor.qualified_name and survivor.qualified_name == ns.qualified_name:
                reason_code = PruningReasonCode.LOGICAL_DUPLICATE
            elif cfg.enable_near_duplicate_detection:
                reason_code = PruningReasonCode.NEAR_DUPLICATE

        # Combine provenance and evidence across all members of the group
        all_sources: set[str] = set()
        all_reason_codes: set[str] = set(survivor.reason_codes)
        all_merged_ids: list[str] = []

        max_ret_relevance = survivor.score_breakdown.retrieval_relevance
        max_entity_match = survivor.score_breakdown.query_entity_match
        max_intent_align = survivor.score_breakdown.intent_alignment
        max_rel_align = survivor.score_breakdown.relationship_alignment
        max_prov_strength = survivor.score_breakdown.provenance_strength
        max_graph_prox = survivor.score_breakdown.graph_proximity
        max_scope_align = survivor.score_breakdown.scope_alignment
        max_locality = survivor.score_breakdown.locality

        for member in group:
            all_merged_ids.append(member.candidate_id)
            all_reason_codes.update(member.reason_codes)

            # Accumulate source
            if "RETRIEVAL" in member.source:
                all_sources.add("RETRIEVAL")
            if "GRAPH" in member.source:
                all_sources.add("GRAPH_EXPANSION")

            # Maximize score breakdown dimensions
            sb = member.score_breakdown
            max_ret_relevance = max(max_ret_relevance, sb.retrieval_relevance)
            max_entity_match = max(max_entity_match, sb.query_entity_match)
            max_intent_align = max(max_intent_align, sb.intent_alignment)
            max_rel_align = max(max_rel_align, sb.relationship_alignment)
            max_prov_strength = max(max_prov_strength, sb.provenance_strength)
            max_graph_prox = max(max_graph_prox, sb.graph_proximity)
            max_scope_align = max(max_scope_align, sb.scope_alignment)
            max_locality = max(max_locality, sb.locality)

        # Build merged source string
        merged_source = survivor.source
        if "RETRIEVAL" in all_sources and "GRAPH_EXPANSION" in all_sources:
            merged_source = "RETRIEVAL+GRAPH_EXPANSION"
            all_reason_codes.add(RankingReasonCode.MULTI_SOURCE_EVIDENCE)
            max_prov_strength = max(max_prov_strength, 1.0)
        elif "RETRIEVAL" in all_sources:
            merged_source = "RETRIEVAL"
        elif "GRAPH_EXPANSION" in all_sources:
            merged_source = "GRAPH_EXPANSION"

        merged_breakdown = ContextRankingScoreBreakdown(
            retrieval_relevance=max_ret_relevance,
            query_entity_match=max_entity_match,
            intent_alignment=max_intent_align,
            relationship_alignment=max_rel_align,
            provenance_strength=max_prov_strength,
            graph_proximity=max_graph_prox,
            scope_alignment=max_scope_align,
            locality=max_locality,
        )

        merged_meta = dict(survivor.metadata)
        merged_meta["merged_candidate_ids"] = sorted(set(all_merged_ids))

        updated_survivor = RankedContextCandidate(
            candidate_id=survivor.candidate_id,
            rank=survivor.rank,
            final_score=survivor.final_score,
            score_breakdown=merged_breakdown,
            reason_codes=sorted(all_reason_codes),
            node_id=survivor.node_id,
            symbol_name=survivor.symbol_name,
            qualified_name=survivor.qualified_name,
            node_kind=survivor.node_kind,
            file_path=survivor.file_path,
            start_line=survivor.start_line,
            end_line=survivor.end_line,
            source=merged_source,
            anchor_id=survivor.anchor_id,
            relationship_type=survivor.relationship_type,
            traversal_depth=survivor.traversal_depth,
            retrieval_chunk_id=survivor.retrieval_chunk_id,
            retrieval_score=survivor.retrieval_score,
            original_candidate=survivor.original_candidate,
            metadata=merged_meta,
        )

        return updated_survivor, non_survivors, reason_code

    def _prune_redundant_candidates(
        self,
        candidates: list[RankedContextCandidate],
        query_plan: QueryPlan,
        cfg: ContextPruningConfig,
    ) -> tuple[list[RankedContextCandidate], list[PrunedCandidateRecord]]:
        """Apply minimum score, structural coverage, per-symbol, per-file, and top-K limits."""
        retained: list[RankedContextCandidate] = []
        pruned_records: list[PrunedCandidateRecord] = []

        symbol_counts: dict[str, int] = {}
        file_counts: dict[str, int] = {}

        for cand in candidates:
            # 1. Identify protection status
            is_protected = self._is_candidate_protected(cand, query_plan, cfg)

            # 2. Minimum Score Filter
            if cand.final_score < cfg.minimum_score and not is_protected:
                pruned_records.append(
                    PrunedCandidateRecord(
                        candidate_id=cand.candidate_id,
                        pruning_reason=PruningReasonCode.BELOW_SCORE_THRESHOLD,
                        details=f"Candidate final score ({cand.final_score:.4f}) is below minimum threshold ({cfg.minimum_score:.4f}).",
                        original_candidate=cand,
                    )
                )
                continue

            # 3. Per-Symbol Limit Filter
            sym_key = cand.symbol_name or cand.qualified_name
            if sym_key and cfg.max_candidates_per_symbol is not None:
                current_sym_count = symbol_counts.get(sym_key, 0)
                if current_sym_count >= cfg.max_candidates_per_symbol and not is_protected:
                    pruned_records.append(
                        PrunedCandidateRecord(
                            candidate_id=cand.candidate_id,
                            pruning_reason=PruningReasonCode.REDUNDANT_SYMBOL,
                            details=f"Exceeded max candidates per symbol ({cfg.max_candidates_per_symbol}) for '{sym_key}'.",
                            original_candidate=cand,
                        )
                    )
                    continue

            # 4. Per-File Limit Filter
            file_key = cand.file_path
            if file_key and cfg.max_candidates_per_file is not None:
                current_file_count = file_counts.get(file_key, 0)
                if current_file_count >= cfg.max_candidates_per_file and not is_protected:
                    pruned_records.append(
                        PrunedCandidateRecord(
                            candidate_id=cand.candidate_id,
                            pruning_reason=PruningReasonCode.REDUNDANT_FILE,
                            details=f"Exceeded max candidates per file ({cfg.max_candidates_per_file}) for '{file_key}'.",
                            original_candidate=cand,
                        )
                    )
                    continue

            # Retain candidate and update counts
            retained.append(cand)
            if sym_key:
                symbol_counts[sym_key] = symbol_counts.get(sym_key, 0) + 1
            if file_key:
                file_counts[file_key] = file_counts.get(file_key, 0) + 1

        # 5. Top-K Max Candidates Limit Filter
        if cfg.max_candidates is not None and len(retained) > cfg.max_candidates:
            # Sort retained candidates cleanly
            retained_sorted = sorted(retained, key=self._build_candidate_sort_key)
            final_retained: list[RankedContextCandidate] = []

            for i, cand in enumerate(retained_sorted):
                is_protected = self._is_candidate_protected(cand, query_plan, cfg)
                if i < cfg.max_candidates or is_protected:
                    final_retained.append(cand)
                else:
                    pruned_records.append(
                        PrunedCandidateRecord(
                            candidate_id=cand.candidate_id,
                            pruning_reason=PruningReasonCode.MAX_CANDIDATES_EXCEEDED,
                            details=f"Exceeded top-K candidate limit ({cfg.max_candidates}).",
                            original_candidate=cand,
                        )
                    )
            retained = final_retained

        return retained, pruned_records

    def _is_candidate_protected(
        self,
        cand: RankedContextCandidate,
        query_plan: QueryPlan,
        cfg: ContextPruningConfig,
    ) -> bool:
        """Determine if a candidate is protected from pruning due to primary targets, multi-source, or structural coverage."""
        # Primary Target Protection
        if cfg.preserve_primary_targets:
            if RankingReasonCode.DIRECT_QUERY_TARGET in cand.reason_codes:
                return True
            targets = [t.lower().strip() for t in query_plan.target_entities if t]
            if cand.symbol_name and cand.symbol_name.lower().strip() in targets:
                return True
            if cand.qualified_name and cand.qualified_name.lower().strip() in targets:
                return True

        # Multi-Source Evidence Protection
        if cfg.preserve_multi_source_evidence:
            if (
                cand.source == "RETRIEVAL+GRAPH_EXPANSION"
                or RankingReasonCode.MULTI_SOURCE_EVIDENCE in cand.reason_codes
            ):
                return True

        # Structural Coverage Protection
        if cfg.preserve_structural_coverage:
            if (
                RankingReasonCode.RELATIONSHIP_MATCH in cand.reason_codes
                or RankingReasonCode.PRIMARY_INTENT_MATCH in cand.reason_codes
            ):
                return True

        return False

    def _format_final_candidates(
        self, candidates: list[RankedContextCandidate], cfg: ContextPruningConfig
    ) -> list[RankedContextCandidate]:
        """Deterministically sort final surviving candidates and assign 1-indexed rank positions."""
        sorted_retained = sorted(candidates, key=self._build_candidate_sort_key)
        final_list: list[RankedContextCandidate] = []

        for idx, rc in enumerate(sorted_retained, start=1):
            updated = RankedContextCandidate(
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
            final_list.append(updated)

        return final_list
