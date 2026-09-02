"""Context Packer implementation for TASK-6E Context Token Budgeting & Context Packing."""

import time

from llm.budget_config import ContextBudgetConfig
from llm.budget_contracts import ContextPackerContract
from llm.budget_models import (
    ContextOmissionRecord,
    ContextPackingStats,
    PackedContext,
    PackedContextItem,
)
from llm.enums import ContextOverflowPolicy, ContextPackingReasonCode, TokenCountMode
from llm.planner_models import QueryPlan
from llm.pruning_models import ContextPruningResult
from llm.ranking_models import RankedContextCandidate
from llm.token_counter import (
    DeterministicFallbackTokenCounter,
    ExactTokenCounter,
    TokenCounterContract,
)


class ContextPacker(ContextPackerContract):
    """Deterministic, provider-independent context token budgeting and evidence packing engine."""

    def __init__(self, token_counter: TokenCounterContract | None = None) -> None:
        """Initialize ContextPacker with optional custom token counter."""
        self._default_token_counter = token_counter

    def pack(
        self,
        query_plan: QueryPlan,
        pruning_result: ContextPruningResult,
        config: ContextBudgetConfig | None = None,
    ) -> PackedContext:
        """Deterministically transform 6D pruned candidates into a bounded PackedContext package."""
        start_time = time.perf_counter()
        cfg = config or ContextBudgetConfig()

        # Select token counter based on configuration mode if not injected
        counter = self._resolve_token_counter(cfg)

        usable_budget = cfg.usable_evidence_budget
        retained_candidates = list(pruning_result.retained_candidates)

        if not retained_candidates or usable_budget == 0:
            stats = self._build_stats(
                config=cfg,
                counter_mode=counter.get_mode(),
                input_count=len(retained_candidates),
                packed_count=0,
                omitted_count=len(retained_candidates),
                packed_tokens=0,
            )

            # Record all candidates as omitted if usable budget is zero but candidates were provided
            zero_budget_omitted_records: list[ContextOmissionRecord] = []
            if usable_budget == 0 and retained_candidates:
                for cand in retained_candidates:
                    fmt_code = self._format_candidate_code(cand)
                    cand_tokens = counter.count(fmt_code)
                    zero_budget_omitted_records.append(
                        ContextOmissionRecord(
                            candidate_id=cand.candidate_id,
                            omission_reason=ContextPackingReasonCode.BUDGET_EXHAUSTED,
                            details="Usable evidence budget is 0 tokens.",
                            candidate_token_count=cand_tokens,
                            available_budget_at_omission=0,
                            original_candidate=cand,
                        )
                    )

            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return PackedContext(
                query=query_plan.query,
                query_plan_summary={
                    "primary_intent": query_plan.primary_intent.value,
                    "target_entities": query_plan.target_entities,
                    "scope": query_plan.scope.value,
                },
                packed_items=[],
                omitted_records=zero_budget_omitted_records,
                stats=stats,
                formatted_context_str="",
                packing_latency_ms=latency_ms,
                metadata={
                    "query": query_plan.query,
                    "usable_evidence_budget": usable_budget,
                    "packed_count": 0,
                    "omitted_count": len(zero_budget_omitted_records),
                },
            )

        # 1. Normalize candidate order by rank / stable key to guarantee permutation invariance
        sorted_candidates = sorted(retained_candidates, key=self._build_candidate_sort_key)

        # 2. Iterate candidates and pack within usable evidence budget
        packed_items: list[PackedContextItem] = []
        omitted_records: list[ContextOmissionRecord] = []
        remaining_budget = usable_budget

        for cand in sorted_candidates:
            # Extract content and header metadata
            header_str, snippet_text, lang = self._extract_candidate_components(cand)

            # Build full formatted candidate string
            formatted_code = self._assemble_formatted_code(header_str, snippet_text, lang)

            # Count tokens on the exact formatted string passed downstream
            header_tokens = counter.count(header_str)
            code_tokens = counter.count(snippet_text)
            total_item_tokens = counter.count(formatted_code)

            # Filter min/max token limits if configured
            if (
                cfg.minimum_candidate_tokens is not None
                and total_item_tokens < cfg.minimum_candidate_tokens
            ):
                omitted_records.append(
                    ContextOmissionRecord(
                        candidate_id=cand.candidate_id,
                        omission_reason=ContextPackingReasonCode.TOKEN_BUDGET_EXCEEDED,
                        details=f"Candidate token count ({total_item_tokens}) is below minimum candidate limit ({cfg.minimum_candidate_tokens}).",
                        candidate_token_count=total_item_tokens,
                        available_budget_at_omission=remaining_budget,
                        original_candidate=cand,
                    )
                )
                continue

            if (
                cfg.maximum_candidate_tokens is not None
                and total_item_tokens > cfg.maximum_candidate_tokens
            ):
                omitted_records.append(
                    ContextOmissionRecord(
                        candidate_id=cand.candidate_id,
                        omission_reason=ContextPackingReasonCode.CANDIDATE_TOO_LARGE,
                        details=f"Candidate token count ({total_item_tokens}) exceeds maximum candidate limit ({cfg.maximum_candidate_tokens}).",
                        candidate_token_count=total_item_tokens,
                        available_budget_at_omission=remaining_budget,
                        original_candidate=cand,
                    )
                )
                continue

            # Check fit against remaining budget
            if total_item_tokens <= remaining_budget:
                repo_id = self._extract_repository_id(cand)
                item = PackedContextItem(
                    candidate_id=cand.candidate_id,
                    rank=cand.rank,
                    final_score=cand.final_score,
                    repository_id=repo_id,
                    file_path=cand.file_path,
                    start_line=cand.start_line,
                    end_line=cand.end_line,
                    symbol_name=cand.symbol_name,
                    qualified_name=cand.qualified_name,
                    node_id=cand.node_id,
                    node_kind=cand.node_kind,
                    source=cand.source,
                    relationship_type=cand.relationship_type,
                    formatted_code=formatted_code,
                    code_tokens=code_tokens,
                    header_tokens=header_tokens,
                    token_count=total_item_tokens,
                    truncated=False,
                    original_token_count=total_item_tokens,
                    reason_codes=list(cand.reason_codes),
                    score_breakdown=cand.score_breakdown,
                    metadata=dict(cand.metadata),
                )
                packed_items.append(item)
                remaining_budget -= total_item_tokens
            else:
                # Overflow handling
                if cfg.overflow_policy == ContextOverflowPolicy.TRUNCATE and remaining_budget > (
                    header_tokens + 10
                ):
                    truncated_formatted_code, truncated_tokens, trunc_code_tokens = (
                        self._truncate_candidate(
                            header_str=header_str,
                            snippet_text=snippet_text,
                            lang=lang,
                            max_tokens=remaining_budget,
                            counter=counter,
                        )
                    )
                    repo_id = self._extract_repository_id(cand)
                    item = PackedContextItem(
                        candidate_id=cand.candidate_id,
                        rank=cand.rank,
                        final_score=cand.final_score,
                        repository_id=repo_id,
                        file_path=cand.file_path,
                        start_line=cand.start_line,
                        end_line=cand.end_line,
                        symbol_name=cand.symbol_name,
                        qualified_name=cand.qualified_name,
                        node_id=cand.node_id,
                        node_kind=cand.node_kind,
                        source=cand.source,
                        relationship_type=cand.relationship_type,
                        formatted_code=truncated_formatted_code,
                        code_tokens=trunc_code_tokens,
                        header_tokens=header_tokens,
                        token_count=truncated_tokens,
                        truncated=True,
                        original_token_count=total_item_tokens,
                        reason_codes=list(cand.reason_codes),
                        score_breakdown=cand.score_breakdown,
                        metadata=dict(cand.metadata),
                    )
                    packed_items.append(item)
                    remaining_budget -= truncated_tokens
                else:
                    # Determine exact omission reason code
                    if remaining_budget <= 0:
                        reason_code = ContextPackingReasonCode.BUDGET_EXHAUSTED
                        details = f"Context budget exhausted ({usable_budget} tokens)."
                    elif total_item_tokens > usable_budget:
                        reason_code = ContextPackingReasonCode.CANDIDATE_TOO_LARGE
                        details = f"Candidate token count ({total_item_tokens}) exceeds total usable evidence budget ({usable_budget})."
                    else:
                        reason_code = ContextPackingReasonCode.TOKEN_BUDGET_EXCEEDED
                        details = f"Candidate token count ({total_item_tokens}) exceeds remaining available budget ({remaining_budget})."

                    omitted_records.append(
                        ContextOmissionRecord(
                            candidate_id=cand.candidate_id,
                            omission_reason=reason_code,
                            details=details,
                            candidate_token_count=total_item_tokens,
                            available_budget_at_omission=remaining_budget,
                            original_candidate=cand,
                        )
                    )

        # 3. Assemble statistics and concatenated context string
        packed_tokens_sum = sum(item.token_count for item in packed_items)
        stats = self._build_stats(
            config=cfg,
            counter_mode=counter.get_mode(),
            input_count=len(retained_candidates),
            packed_count=len(packed_items),
            omitted_count=len(omitted_records),
            packed_tokens=packed_tokens_sum,
        )

        formatted_context_str = "\n\n---\n\n".join(item.formatted_code for item in packed_items)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return PackedContext(
            query=query_plan.query,
            query_plan_summary={
                "primary_intent": query_plan.primary_intent.value,
                "target_entities": query_plan.target_entities,
                "scope": query_plan.scope.value,
            },
            packed_items=packed_items,
            omitted_records=omitted_records,
            stats=stats,
            formatted_context_str=formatted_context_str,
            packing_latency_ms=latency_ms,
            metadata={
                "query": query_plan.query,
                "usable_evidence_budget": usable_budget,
                "packed_count": len(packed_items),
                "omitted_count": len(omitted_records),
            },
        )

    def _resolve_token_counter(self, cfg: ContextBudgetConfig) -> TokenCounterContract:
        """Resolve token counter instance based on configuration or default."""
        if self._default_token_counter is not None:
            return self._default_token_counter

        if cfg.token_count_mode == TokenCountMode.EXACT:
            # Simple exact character fallback tokenizer if no custom exact tokenizer provided
            return ExactTokenCounter(lambda s: (len(s) + 3) // 4)
        return DeterministicFallbackTokenCounter()

    def _build_candidate_sort_key(
        self, cand: RankedContextCandidate
    ) -> tuple[int, float, float, int, str]:
        """Stable deterministic tie-breaking sort key based on 6C/6D rank and score."""
        score_rounded = round(cand.final_score, 6)
        prov_score = cand.score_breakdown.provenance_strength if cand.score_breakdown else 0.0
        depth = cand.traversal_depth
        cand_id = cand.candidate_id
        return (cand.rank, -score_rounded, -prov_score, depth, cand_id)

    def _extract_repository_id(self, cand: RankedContextCandidate) -> str:
        """Extract repository ID from candidate metadata or original candidate."""
        if cand.metadata and "repository_id" in cand.metadata and cand.metadata["repository_id"]:
            return str(cand.metadata["repository_id"])
        if cand.original_candidate and hasattr(cand.original_candidate, "repository_id"):
            val = cand.original_candidate.repository_id
            if val:
                return str(val)
        return "default_repo"

    def _extract_candidate_components(self, cand: RankedContextCandidate) -> tuple[str, str, str]:
        """Extract header string, raw snippet content, and code language string."""
        rel_str = str(getattr(cand.relationship_type, "value", str(cand.relationship_type)))
        lines_str = f"{cand.start_line if cand.start_line is not None else '?'}-{cand.end_line if cand.end_line is not None else '?'}"
        header = (
            f"FILE: {cand.file_path or 'unknown'}\n"
            f"SYMBOL: {cand.qualified_name or cand.symbol_name or 'N/A'}\n"
            f"LINES: {lines_str}\n"
            f"SOURCE: {cand.source}\n"
            f"RELATIONSHIP: {rel_str}"
        )

        # Snippet text extraction
        snippet = ""
        if cand.metadata:
            for k in ("content", "chunk_text", "code", "snippet", "text"):
                if cand.metadata.get(k):
                    snippet = str(cand.metadata[k])
                    break

        if not snippet and cand.original_candidate:
            if hasattr(cand.original_candidate, "content") and cand.original_candidate.content:
                snippet = str(cand.original_candidate.content)
            elif hasattr(cand.original_candidate, "metadata") and isinstance(
                cand.original_candidate.metadata, dict
            ):
                meta = cand.original_candidate.metadata
                for k in ("content", "chunk_text", "code", "snippet", "text"):
                    if meta.get(k):
                        snippet = str(meta[k])
                        break

        if not snippet:
            sym_desc = cand.qualified_name or cand.symbol_name or cand.candidate_id
            snippet = (
                f"# Declaration for {sym_desc}\n# Source: {cand.file_path or 'unknown'}:{lines_str}"
            )

        # Detect code language
        lang = "text"
        if cand.file_path:
            fp = cand.file_path.lower()
            if fp.endswith(".py"):
                lang = "python"
            elif fp.endswith(".java"):
                lang = "java"
            elif fp.endswith((".ts", ".tsx")):
                lang = "typescript"
            elif fp.endswith((".js", ".jsx")):
                lang = "javascript"
            elif fp.endswith(".json"):
                lang = "json"

        return header, snippet, lang

    def _assemble_formatted_code(self, header: str, snippet: str, lang: str) -> str:
        """Combine header metadata and code block into standard formatted representation."""
        return f"{header}\n\n```{lang}\n{snippet}\n```"

    def _format_candidate_code(self, cand: RankedContextCandidate) -> str:
        """Format candidate directly into string representation for token counting."""
        header, snippet, lang = self._extract_candidate_components(cand)
        return self._assemble_formatted_code(header, snippet, lang)

    def _truncate_candidate(
        self,
        header_str: str,
        snippet_text: str,
        lang: str,
        max_tokens: int,
        counter: TokenCounterContract,
    ) -> tuple[str, int, int]:
        """Truncate candidate code line-by-line or char-by-char to fit exactly within max_tokens."""
        lines = snippet_text.splitlines()
        truncated_lines: list[str] = []

        for line in lines:
            test_snippet = "\n".join([*truncated_lines, line]) + "\n... [TRUNCATED]"
            test_formatted = self._assemble_formatted_code(header_str, test_snippet, lang)
            if counter.count(test_formatted) <= max_tokens:
                truncated_lines.append(line)
            else:
                break

        if not truncated_lines:
            # Fallback char-by-char truncation if single line is too long
            char_limit = max(10, (max_tokens - counter.count(header_str) - 20) * 3)
            truncated_snippet = snippet_text[:char_limit] + "... [TRUNCATED]"
        else:
            truncated_snippet = "\n".join(truncated_lines) + "\n... [TRUNCATED]"

        final_formatted = self._assemble_formatted_code(header_str, truncated_snippet, lang)
        total_tokens = counter.count(final_formatted)
        code_tokens = counter.count(truncated_snippet)

        return final_formatted, total_tokens, code_tokens

    def _build_stats(
        self,
        config: ContextBudgetConfig,
        counter_mode: TokenCountMode,
        input_count: int,
        packed_count: int,
        omitted_count: int,
        packed_tokens: int,
    ) -> ContextPackingStats:
        """Construct ContextPackingStats container."""
        usable_budget = config.usable_evidence_budget
        remaining = max(0, usable_budget - packed_tokens)
        ratio = (packed_tokens / float(usable_budget)) if usable_budget > 0 else 0.0
        ratio = min(1.0, max(0.0, ratio))

        return ContextPackingStats(
            total_model_context_limit=config.max_context_tokens,
            reserved_system_tokens=config.reserved_system_tokens,
            reserved_query_tokens=config.reserved_query_tokens,
            reserved_output_tokens=config.reserved_output_tokens,
            safety_margin_tokens=config.safety_margin_tokens,
            usable_evidence_budget=usable_budget,
            packed_evidence_tokens=packed_tokens,
            remaining_evidence_budget=remaining,
            utilization_ratio=ratio,
            input_candidate_count=input_count,
            packed_candidate_count=packed_count,
            omitted_candidate_count=omitted_count,
            token_count_mode=counter_mode,
            overflow_policy=config.overflow_policy,
        )
