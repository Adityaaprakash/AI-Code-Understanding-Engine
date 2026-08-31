"""Query preprocessing, normalization, identifier detection, and classification engine."""

import re
import unicodedata
from typing import Any

from retrieval.exceptions import LexicalQueryError
from retrieval.query_models import ProcessedQuery, QueryKind
from retrieval.tokenizer import CodeTokenizer, default_tokenizer

# Regex patterns for query structure detection
MULTIPLE_SPACES_PATTERN = re.compile(r"\s+")
QUALIFIED_NAME_PATTERN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b")
PATH_PATTERN = re.compile(
    r"(?:[A-Za-z0-9_\-\.]+[\/\\])+[A-Za-z0-9_\-\.]+|\b[A-Za-z0-9_\-]+\.(?:java|py|ts|js|json|md|cpp|cs|go|rs|c|h|hpp|kt|swift)\b",
    re.IGNORECASE,
)

# Identifier sub-patterns
ACRONYM_PATTERN = re.compile(r"\b[A-Z]{2,}\b")
CAMEL_CASE_PATTERN = re.compile(r"\b[a-z0-9]+[A-Z][a-zA-Z0-9]*\b")
PASCAL_CASE_PATTERN = re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+\b")
SNAKE_CASE_PATTERN = re.compile(r"\b[a-zA-Z0-9]+_[a-zA-Z0-9_]+\b")
CAPITALIZED_WORD_PATTERN = re.compile(r"\b[A-Z][a-zA-Z0-9]*\b")

PUNCTUATION_STRIP_PATTERN = re.compile(r"^[^\w]+|[^\w]+$")

# Relationship intent phrases
RELATIONSHIP_KEYWORDS = (
    "who calls",
    "who called",
    "calls",
    "called by",
    "which classes implement",
    "which class implements",
    "implements",
    "implementing",
    "which classes depend",
    "depends on",
    "depending on",
    "inherits",
    "overrides",
    "references",
    "referenced by",
)

# Natural language question / prose indicators (lowercase)
PROSE_INDICATORS = {
    "how",
    "where",
    "what",
    "why",
    "who",
    "which",
    "does",
    "do",
    "is",
    "are",
    "can",
    "should",
    "work",
    "works",
    "handled",
    "handles",
    "processed",
    "created",
    "implemented",
    "defined",
    "used",
    "authenticated",
    "validates",
    "process",
    "payments",
    "service",
    "classes",
}

# Stop words to exclude from text tokens
STOP_WORDS = {
    "a",
    "an",
    "the",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "and",
    "or",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
}


class QueryPreprocessor:
    """Deterministic search query preprocessor preserving original queries and extracting code metadata."""

    def __init__(self, tokenizer: CodeTokenizer | None = None) -> None:
        self.tokenizer = tokenizer if tokenizer is not None else default_tokenizer

    def process(self, query: str) -> ProcessedQuery:
        """Preprocess, normalize, tokenize, and classify a raw search query.

        Args:
            query: Raw user query string.

        Returns:
            Immutable ProcessedQuery containing normalized query, tokens, identifier details, and QueryKind classification.

        Raises:
            LexicalQueryError: If the query is empty or whitespace-only.
        """
        if not isinstance(query, str):
            raise LexicalQueryError(f"Query must be a string, got {type(query).__name__}")

        raw_query = query
        normalized = self._normalize_query(query)

        if not normalized:
            raise LexicalQueryError("Query string cannot be empty or whitespace")

        # 1. Extract lexical tokens using code-aware tokenizer
        all_tokens = self.tokenizer.tokenize(normalized)

        # 2. Extract qualified name candidates
        qualified_candidates = QUALIFIED_NAME_PATTERN.findall(normalized)

        # 3. Detect identifier-like tokens
        identifiers = self._extract_identifiers(normalized, qualified_candidates)

        # 4. Extract natural language text tokens
        text_tokens = self._extract_text_tokens(all_tokens, identifiers)

        # 5. Classify query kind
        query_kind = self._classify_query(
            normalized=normalized,
            identifiers=identifiers,
            qualified_candidates=qualified_candidates,
            text_tokens=text_tokens,
        )

        metadata: dict[str, Any] = {
            "token_count": len(all_tokens),
            "identifier_count": len(identifiers),
            "qualified_candidate_count": len(qualified_candidates),
            "has_path": query_kind == QueryKind.PATH_OR_FILE
            or bool(PATH_PATTERN.search(normalized)),
        }

        return ProcessedQuery(
            original_query=raw_query,
            normalized_query=normalized,
            tokens=all_tokens,
            identifier_tokens=identifiers,
            text_tokens=text_tokens,
            qualified_name_candidates=qualified_candidates,
            query_kind=query_kind,
            metadata=metadata,
        )

    def _normalize_query(self, text: str) -> str:
        """Apply deterministic normalization (unicode NFC, whitespace collapsing, stripping)."""
        if not text:
            return ""
        norm = unicodedata.normalize("NFC", text)
        norm = MULTIPLE_SPACES_PATTERN.sub(" ", norm)
        return norm.strip()

    def _extract_identifiers(self, normalized: str, qualified_candidates: list[str]) -> list[str]:
        """Extract unique identifier-like tokens preserving original casing."""
        identifiers: list[str] = []
        seen: set[str] = set()

        # Add qualified candidates
        for q in qualified_candidates:
            if q not in seen:
                seen.add(q)
                identifiers.append(q)

        # Add camelCase
        for match in CAMEL_CASE_PATTERN.findall(normalized):
            if match not in seen and match.lower() not in PROSE_INDICATORS:
                seen.add(match)
                identifiers.append(match)

        # Add PascalCase
        for match in PASCAL_CASE_PATTERN.findall(normalized):
            if match not in seen and match.lower() not in PROSE_INDICATORS:
                seen.add(match)
                identifiers.append(match)

        # Add snake_case
        for match in SNAKE_CASE_PATTERN.findall(normalized):
            if match not in seen and match.lower() not in PROSE_INDICATORS:
                seen.add(match)
                identifiers.append(match)

        # Add acronyms (e.g. JWT, HTTP)
        for match in ACRONYM_PATTERN.findall(normalized):
            if match not in seen and match.lower() not in PROSE_INDICATORS:
                seen.add(match)
                identifiers.append(match)

        # Add capitalized words (e.g. AuthService, PaymentService, Auth) if not prose
        for match in CAPITALIZED_WORD_PATTERN.findall(normalized):
            clean_m = PUNCTUATION_STRIP_PATTERN.sub("", match)
            if clean_m and clean_m not in seen and clean_m.lower() not in PROSE_INDICATORS:
                seen.add(clean_m)
                identifiers.append(clean_m)

        return identifiers

    def _extract_text_tokens(self, all_tokens: list[str], identifiers: list[str]) -> list[str]:
        """Extract natural language text tokens excluding pure identifiers and stop words."""
        id_subwords: set[str] = set()
        for ident in identifiers:
            id_subwords.add(ident.lower())
            for sub in re.split(r"[\s\._\-\/]+", ident):
                if sub:
                    id_subwords.add(sub.lower())

        text_tokens: list[str] = []
        for t in all_tokens:
            clean_t = PUNCTUATION_STRIP_PATTERN.sub("", t)
            if not clean_t:
                continue
            t_lower = clean_t.lower()
            if t_lower not in STOP_WORDS and t_lower not in id_subwords:
                text_tokens.append(clean_t)
        return text_tokens

    def _classify_query(
        self,
        normalized: str,
        identifiers: list[str],
        qualified_candidates: list[str],
        text_tokens: list[str],
    ) -> QueryKind:
        """Deterministically classify query kind based on structural evidence."""
        norm_lower = normalized.lower()

        # 1. Path or filename query
        if PATH_PATTERN.search(normalized):
            return QueryKind.PATH_OR_FILE

        # 2. Qualified identifier query
        if qualified_candidates:
            raw_words = [
                PUNCTUATION_STRIP_PATTERN.sub("", w).lower() for w in normalized.split() if w
            ]
            if not any(w in PROSE_INDICATORS for w in raw_words):
                return QueryKind.QUALIFIED_IDENTIFIER

        # 3. Relationship query
        if any(rel_phrase in norm_lower for rel_phrase in RELATIONSHIP_KEYWORDS):
            return QueryKind.RELATIONSHIP

        # 4. Pure Identifier query
        raw_words = [PUNCTUATION_STRIP_PATTERN.sub("", w) for w in normalized.split() if w]
        prose_word_count = sum(1 for w in raw_words if w.lower() in PROSE_INDICATORS)

        if identifiers and prose_word_count == 0:
            return QueryKind.IDENTIFIER

        if len(raw_words) == 1 and prose_word_count == 0:
            return QueryKind.IDENTIFIER

        # 5. Natural Language query
        if prose_word_count > 0 and not identifiers:
            return QueryKind.NATURAL_LANGUAGE

        # 6. Mixed query
        if identifiers and (prose_word_count > 0 or text_tokens):
            return QueryKind.MIXED

        if prose_word_count > 0:
            return QueryKind.NATURAL_LANGUAGE

        if identifiers:
            return QueryKind.IDENTIFIER

        return QueryKind.UNKNOWN
