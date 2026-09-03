"""Implementation of the deterministic Grounding Verification Engine (TASK-6H)."""

import re

from llm.answer_models import GeneratedAnswer
from llm.budget_models import PackedContext, PackedContextItem
from llm.enums import CitationStatus, ClaimStatus, GroundingReasonCode, GroundingStatus
from llm.exceptions import GroundingVerificationError
from llm.grounding_config import GroundingVerificationConfig
from llm.grounding_contracts import GroundingEngineContract
from llm.grounding_models import (
    CitationReference,
    GroundingClaim,
    GroundingMetrics,
    GroundingVerificationResult,
)


class GroundingEngine(GroundingEngineContract):
    """Deterministic, local verification engine correlating GeneratedAnswer against PackedContext."""

    def verify(
        self,
        answer: GeneratedAnswer,
        context: PackedContext,
        config: GroundingVerificationConfig | None = None,
    ) -> GroundingVerificationResult:
        if config is None:
            config = GroundingVerificationConfig()

        try:
            return self._verify_impl(answer, context, config)
        except Exception as e:
            if isinstance(e, GroundingVerificationError):
                raise
            raise GroundingVerificationError(f"Grounding verification failed: {e!s}") from e

    def _verify_impl(
        self,
        answer: GeneratedAnswer,
        context: PackedContext,
        config: GroundingVerificationConfig,
    ) -> GroundingVerificationResult:
        context_map = {item.candidate_id: item for item in context.packed_items}

        claims = self._extract_claims_from_answer(answer.answer_text, config)
        verified_claims = []
        for claim in claims:
            verified_claim = self._verify_claim(claim, context_map, config)
            verified_claims.append(verified_claim)

        metrics = self._calculate_metrics(verified_claims)
        overall_status = self._calculate_overall_status(metrics, len(context.packed_items))

        return GroundingVerificationResult(
            answer_id=answer.metadata.get("answer_id", ""),
            claims=verified_claims,
            metrics=metrics,
            overall_status=overall_status,
        )

    def _extract_claims_from_answer(
        self,
        answer_text: str,
        config: GroundingVerificationConfig,
    ) -> list[GroundingClaim]:
        """Split text naively into sentences representing claims with appended citations."""
        claims = []
        # Naive split by period, newline, or explicit list markers.
        # This is a deterministic research baseline.
        raw_statements = [s.strip() for s in re.split(r'\n+|(?<=\.)\s+(?=[A-Z])', answer_text) if s.strip()]

        for i, text in enumerate(raw_statements):
            citations = self._extract_citations(text, config)
            # A statement without citations is an Uncited claim.
            claims.append(
                GroundingClaim(
                    claim_id=f"claim_{i}",
                    text=text,
                    order_index=i,
                    citations=citations,
                    supported_context_ids=[],
                    evidence_score=0.0,
                    status=ClaimStatus.UNVERIFIABLE,
                    reason_codes=[],
                )
            )

        return claims

    def _extract_citations(
        self,
        text: str,
        config: GroundingVerificationConfig,
    ) -> list[CitationReference]:
        """Extract citations by regex matching the pre-configured boundaries."""
        citations = []

        # Escape markers for regex execution safely
        prefix = re.escape(config.citation_marker_prefix)
        suffix = re.escape(config.citation_marker_suffix)

        # Regex example `\[CTX:(.*?)\]`
        pattern = f"{prefix}(.*?){suffix}"

        matches = re.finditer(pattern, text)
        for match in matches:
            inner_id = match.group(1).strip()
            # It's an unresolved citation physically parsed from the string.
            citations.append(
                CitationReference(
                    marker=match.group(0),
                    context_id=inner_id if inner_id else None,
                    status=CitationStatus.UNRESOLVED,
                    reason_codes=[],
                )
            )

        return citations

    def _verify_claim(
        self,
        claim: GroundingClaim,
        context_map: dict[str, PackedContextItem],
        config: GroundingVerificationConfig,
    ) -> GroundingClaim:
        """Determines factual score mapping claims against their cited context_ids."""
        if not claim.citations:
            return claim.model_copy(
                update={
                    "status": ClaimStatus.UNCITED,
                    "reason_codes": [GroundingReasonCode.UNCITED_CLAIM],
                }
            )

        verified_citations = []
        supported_context_ids = []
        total_score = 0.0

        # Keep track of reason codes per claim
        claim_reasons: set[GroundingReasonCode] = set()

        for cit in claim.citations:
            if not cit.context_id:
                verified_citations.append(
                    cit.model_copy(
                        update={
                            "status": CitationStatus.MALFORMED,
                            "reason_codes": [GroundingReasonCode.MALFORMED_CITATION],
                        }
                    )
                )
                claim_reasons.add(GroundingReasonCode.MALFORMED_CITATION)
                continue

            if cit.context_id not in context_map:
                verified_citations.append(
                    cit.model_copy(
                        update={
                            "status": CitationStatus.MISSING,
                            "reason_codes": [GroundingReasonCode.UNKNOWN_CONTEXT_ID],
                        }
                    )
                )
                claim_reasons.add(GroundingReasonCode.UNKNOWN_CONTEXT_ID)
                continue

            # Context ID exists!
            context_item = context_map[cit.context_id]
            verified_citations.append(
                cit.model_copy(
                    update={
                        "status": CitationStatus.VALID,
                        "reason_codes": [GroundingReasonCode.VALID_CITATION],
                    }
                )
            )
            claim_reasons.add(GroundingReasonCode.VALID_CITATION)

            # Now verify lexical claim matching inside this verified context.
            score, lex_reasons = self._calculate_semantic_overlap(claim.text, context_item, config)
            total_score += score
            for r in lex_reasons:
                claim_reasons.add(r)

            if score > 0:
                supported_context_ids.append(cit.context_id)

        # Average the score among all citations targeting this claim
        final_score = 0.0
        if verified_citations:
            final_score = total_score / len(verified_citations)

        final_status = ClaimStatus.UNVERIFIABLE
        if final_score >= config.supported_threshold:
            final_status = ClaimStatus.SUPPORTED
        elif final_score >= config.partial_threshold:
            final_status = ClaimStatus.PARTIALLY_SUPPORTED
            claim_reasons.add(GroundingReasonCode.PARTIAL_EVIDENCE)
        else:
            final_status = ClaimStatus.UNSUPPORTED
            claim_reasons.add(GroundingReasonCode.UNSUPPORTED_CLAIM)

        if not claim_reasons:
            claim_reasons.add(GroundingReasonCode.NO_EVIDENCE)

        return claim.model_copy(
            update={
                "citations": verified_citations,
                "supported_context_ids": list(set(supported_context_ids)),
                "evidence_score": min(1.0, final_score),
                "status": final_status,
                "reason_codes": sorted(claim_reasons),
            }
        )

    def _calculate_semantic_overlap(
        self,
        claim_text: str,
        context_item: PackedContextItem,
        config: GroundingVerificationConfig,
    ) -> tuple[float, list[GroundingReasonCode]]:
        """Measure claim-to-evidence support natively using strict lexical baselines."""

        reasons = []
        score = config.weight_citation_validity  # baseline given citation was valid

        # Normalization
        claim_lower = claim_text.lower()
        context_code_lower = context_item.formatted_code.lower()
        context_sym_lower = (context_item.symbol_name or "").lower()

        # Basic symbol match correlation bounds
        if context_sym_lower and context_sym_lower in claim_lower:
            score += 0.4
            reasons.append(GroundingReasonCode.SYMBOL_MATCH)

        # Lexical matching over meaningful identifier boundaries
        claim_tokens = {
            t.strip()
            for t in re.split(r"\W+", claim_lower)
            if len(t.strip()) >= config.lexical_min_token_length
        }

        context_tokens = {
            t.strip()
            for t in re.split(r"\W+", context_code_lower)
            if len(t.strip()) >= config.lexical_min_token_length
        }

        intersection = claim_tokens.intersection(context_tokens)
        if len(claim_tokens) > 0:
            lexical_ratio = len(intersection) / len(claim_tokens)
            score += lexical_ratio * config.weight_lexical_overlap

            if lexical_ratio > 0.3:
                reasons.append(GroundingReasonCode.LEXICAL_EVIDENCE)

        # Return bounded
        return min(1.0, score), reasons

    def _calculate_metrics(
        self,
        claims: list[GroundingClaim],
    ) -> GroundingMetrics:
        """Derive objective metrics calculating over complete claim datasets."""
        total_claims = len(claims)
        supported = 0
        partial = 0
        unsupported = 0
        uncited = 0

        total_citations = 0
        valid_cits = 0
        invalid_cits = 0

        total_score = 0.0

        for claim in claims:
            if claim.status == ClaimStatus.SUPPORTED:
                supported += 1
            elif claim.status == ClaimStatus.PARTIALLY_SUPPORTED:
                partial += 1
            elif claim.status == ClaimStatus.UNSUPPORTED:
                unsupported += 1
            elif claim.status == ClaimStatus.UNCITED:
                uncited += 1

            total_score += claim.evidence_score

            total_citations += len(claim.citations)
            for cit in claim.citations:
                if cit.status == CitationStatus.VALID:
                    valid_cits += 1
                else:
                    invalid_cits += 1

        citation_cov = (total_claims - uncited) / total_claims if total_claims > 0 else 0.0
        grounding_cov = supported / total_claims if total_claims > 0 else 0.0
        avg_score = total_score / total_claims if total_claims > 0 else 0.0

        return GroundingMetrics(
            total_claims=total_claims,
            supported_claims=supported,
            partially_supported_claims=partial,
            unsupported_claims=unsupported,
            uncited_claims=uncited,
            total_citations=total_citations,
            valid_citations=valid_cits,
            invalid_citations=invalid_cits,
            citation_coverage=citation_cov,
            grounding_coverage=grounding_cov,
            average_support_score=avg_score,
        )

    def _calculate_overall_status(
        self,
        metrics: GroundingMetrics,
        total_context_items: int,
    ) -> GroundingStatus:
        """Determines full answer macro-status logically dependent on aggregated scopes."""

        if metrics.total_claims == 0:
            return GroundingStatus.UNVERIFIABLE

        if total_context_items == 0:
            return GroundingStatus.UNVERIFIABLE

        if metrics.supported_claims == metrics.total_claims:
            return GroundingStatus.SUPPORTED

        if metrics.partially_supported_claims > 0 or metrics.supported_claims > 0:
            return GroundingStatus.PARTIALLY_SUPPORTED

        return GroundingStatus.UNSUPPORTED
