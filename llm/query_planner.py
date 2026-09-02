"""Deterministic Query Planner and Intent Classifier (Phase 6A)."""

import re
from typing import Any, ClassVar

from llm.contracts import QueryPlannerContract
from llm.enums import (
    AnswerStyle,
    GraphStrategy,
    QueryIntent,
    QueryScope,
    RelationshipType,
    RetrievalStrategy,
)
from llm.exceptions import InvalidQueryError
from llm.planner_models import QueryPlan
from retrieval.query_models import ProcessedQuery, QueryKind
from retrieval.query_processor import QueryPreprocessor


class QueryPlanner(QueryPlannerContract):
    """Deterministic, fast, non-LLM query planner.

    Transforms raw text queries or ProcessedQuery objects into immutable QueryPlan
    contracts for downstream retrieval and context engine stages.
    """

    # Common programming file extensions for file scope matching
    _FILE_EXTENSIONS = (
        ".java",
        ".py",
        ".ts",
        ".js",
        ".go",
        ".cs",
        ".kt",
        ".rs",
        ".cpp",
        ".c",
        ".h",
        ".rb",
        ".php",
        ".json",
        ".xml",
        ".yaml",
        ".yml",
        ".md",
    )

    # Negation words
    _NEGATION_WORDS = frozenset(
        {
            "not",
            "no",
            "don't",
            "dont",
            "doesnt",
            "does not",
            "never",
            "without",
            "excluding",
            "except",
        }
    )

    # Pre-compiled regex patterns for relationship and intent recognition
    _PATTERNS: ClassVar[list[dict[str, Any]]] = [
        # 1. CALLERS / INBOUND CALLS
        {
            "id": "CALLERS",
            "regex": re.compile(
                r"\b(?:who|where|which\s+(?:function|method|class|service|component|code))\s+(?:calls|is\s+calling|called|invokes|is\s+invoking|invoked)\b|\bcallers\s+of\b|\bcalled\s+by\b|\bwhere\s+is\s+[\w.]+\s+called\b",
                re.IGNORECASE,
            ),
            "primary_intent": QueryIntent.DEPENDENCY,
            "relationship_type": RelationshipType.CALLERS,
            "graph_strategy": GraphStrategy.CALLERS,
            "answer_style": AnswerStyle.RELATIONSHIP,
            "reason_code": "EXPLICIT_CALLER_PHRASE",
            "priority": 10,
        },
        # 2. CALLEES / OUTBOUND CALLS
        {
            "id": "CALLEES",
            "regex": re.compile(
                r"\bwhat\s+(?:(?:functions?|methods?|classes?|code)\s+)?(?:does|do)\s+[\w.]+\s+(?:call|invoke)\b|\bcallees\s+of\b|\bcalls\s+made\s+by\b|\boutbound\s+calls\b",
                re.IGNORECASE,
            ),
            "primary_intent": QueryIntent.DEPENDENCY,
            "relationship_type": RelationshipType.CALLS,
            "graph_strategy": GraphStrategy.CALLEES,
            "answer_style": AnswerStyle.RELATIONSHIP,
            "reason_code": "EXPLICIT_CALLEE_PHRASE",
            "priority": 10,
        },
        # 3. DEPENDENT / INBOUND DEPENDENCIES
        {
            "id": "DEPENDENTS",
            "regex": re.compile(
                r"\b(?:who|what|which\s+(?:class|classes|module|modules|component|components|service|services|package|packages))\s+(?:depends|depend)\s+on\b|\bdependents\s+of\b|\bdepending\s+on\b|\bwhich\s+components?\s+use\b",
                re.IGNORECASE,
            ),
            "primary_intent": QueryIntent.DEPENDENCY,
            "relationship_type": RelationshipType.DEPENDENTS,
            "graph_strategy": GraphStrategy.DEPENDENTS,
            "answer_style": AnswerStyle.RELATIONSHIP,
            "reason_code": "EXPLICIT_DEPENDENCY_PHRASE",
            "priority": 10,
        },
        # 4. DEPENDENCIES / OUTBOUND DEPENDENCIES
        {
            "id": "DEPENDENCIES",
            "regex": re.compile(
                r"\bwhat\s+does\s+[\w.]+\s+depend\s+on\b|\bdependencies\s+of\b|\bwhat\s+are\s+the\s+dependencies\b",
                re.IGNORECASE,
            ),
            "primary_intent": QueryIntent.DEPENDENCY,
            "relationship_type": RelationshipType.DEPENDENCIES,
            "graph_strategy": GraphStrategy.DEPENDENCIES,
            "answer_style": AnswerStyle.RELATIONSHIP,
            "reason_code": "EXPLICIT_DEPENDENCY_PHRASE",
            "priority": 10,
        },
        # 5. IMPLEMENTATIONS / INBOUND IMPLEMENTS
        {
            "id": "IMPLEMENTS",
            "regex": re.compile(
                r"\b(?:which|what|who)\s+(?:class|classes|struct|structs)?\s*(?:implement|implements|implementing)\b|\bimplementations\s+of\b|\bwho\s+implements\b",
                re.IGNORECASE,
            ),
            "primary_intent": QueryIntent.DEPENDENCY,
            "relationship_type": RelationshipType.IMPLEMENTS,
            "graph_strategy": GraphStrategy.IMPLEMENTATIONS,
            "answer_style": AnswerStyle.RELATIONSHIP,
            "reason_code": "EXPLICIT_IMPLEMENTS_PHRASE",
            "priority": 10,
        },
        # 6. INHERITANCE / EXTENDS
        {
            "id": "EXTENDS",
            "regex": re.compile(
                r"\b(?:which|what|who)\s+(?:class|classes)?\s*(?:extend|extends|inherits?\s+from|subclasses?\s+of)\b|\bsubclasses\s+of\b|\bderived\s+classes\b",
                re.IGNORECASE,
            ),
            "primary_intent": QueryIntent.DEPENDENCY,
            "relationship_type": RelationshipType.EXTENDS,
            "graph_strategy": GraphStrategy.INHERITANCE,
            "answer_style": AnswerStyle.RELATIONSHIP,
            "reason_code": "EXPLICIT_EXTENDS_PHRASE",
            "priority": 10,
        },
        # 7. IMPORTS
        {
            "id": "IMPORTS",
            "regex": re.compile(
                r"\b(?:which|what|who)\s+(?:module|modules|file|files|package|packages)?\s*(?:import|imports|imported\s+by)\b|\bimports\s+of\b|\bwhat\s+does\s+[\w.]+\s+import\b",
                re.IGNORECASE,
            ),
            "primary_intent": QueryIntent.DEPENDENCY,
            "relationship_type": RelationshipType.IMPORTS,
            "graph_strategy": GraphStrategy.IMPORTS,
            "answer_style": AnswerStyle.RELATIONSHIP,
            "reason_code": "EXPLICIT_IMPORT_PHRASE",
            "priority": 10,
        },
        # 8. USES / REFERENCES
        {
            "id": "USES",
            "regex": re.compile(
                r"\bwhere\s+is\s+[\w.]+\s+used\b|\bwho\s+uses\b|\bused\s+by\b|\breferences?\s+to\b|\busages?\s+of\b",
                re.IGNORECASE,
            ),
            "primary_intent": QueryIntent.DEPENDENCY,
            "relationship_type": RelationshipType.USES,
            "graph_strategy": GraphStrategy.USAGES,
            "answer_style": AnswerStyle.RELATIONSHIP,
            "reason_code": "EXPLICIT_USES_PHRASE",
            "priority": 10,
        },
        # 9. IMPACT ANALYSIS
        {
            "id": "IMPACT",
            "regex": re.compile(
                r"\bwhat\s+(?:would|will|could)\s+(?:break|be\s+affected|happen)\s+if\b|\bwhat\s+is\s+the\s+impact\s+of\b|\bimpact\s+radius\s+of\b|\baffect(?:s|ed|ing)?\s+if\b|\bchange\s+to\s+[\w.]+\s+(?:affects|impacts)\b",
                re.IGNORECASE,
            ),
            "primary_intent": QueryIntent.IMPACT,
            "relationship_type": RelationshipType.IMPACT,
            "graph_strategy": GraphStrategy.IMPACT_RADIUS,
            "answer_style": AnswerStyle.IMPACT_ANALYSIS,
            "reason_code": "EXPLICIT_IMPACT_PHRASE",
            "priority": 9,
        },
        # 10. DEBUGGING
        {
            "id": "DEBUGGING",
            "regex": re.compile(
                r"\bwhy\s+(?:is|does|isn't|cannot|can't|fails?|failing|error)\b|\bdebug\b|\btrace\s+error\b|\bbug\s+in\b|\bexception\b|\bfailing\b",
                re.IGNORECASE,
            ),
            "primary_intent": QueryIntent.DEBUGGING,
            "relationship_type": RelationshipType.NONE,
            "graph_strategy": GraphStrategy.NONE,
            "answer_style": AnswerStyle.DEBUGGING_ANALYSIS,
            "reason_code": "EXPLICIT_DEBUGGING_PHRASE",
            "priority": 8,
        },
        # 11. ARCHITECTURE
        {
            "id": "ARCHITECTURE",
            "regex": re.compile(
                r"\b(?:architecture|overall\s+structure|system\s+design|component\s+overview|how\s+are\s+the\s+(?:[\w.]+\s+)?components\s+organized)\b|\bhigh[\s-]level\s+overview\b",
                re.IGNORECASE,
            ),
            "primary_intent": QueryIntent.ARCHITECTURE,
            "relationship_type": RelationshipType.NONE,
            "graph_strategy": GraphStrategy.ARCHITECTURAL_EXPANSION,
            "answer_style": AnswerStyle.ARCHITECTURE,
            "reason_code": "EXPLICIT_ARCHITECTURE_PHRASE",
            "priority": 7,
        },
        # 12. SYMBOL LOCATION
        {
            "id": "SYMBOL_LOCATION",
            "regex": re.compile(
                r"\bwhere\s+is\s+[\w.]+\s+(?:defined|located|implemented)\b|\bfind\s+definition\s+of\b|\bshow\s+definition\b",
                re.IGNORECASE,
            ),
            "primary_intent": QueryIntent.SYMBOL,
            "relationship_type": RelationshipType.NONE,
            "graph_strategy": GraphStrategy.NONE,
            "answer_style": AnswerStyle.CODE_LOCATION,
            "reason_code": "SYMBOL_LOCATION_PATTERN",
            "priority": 6,
        },
        # 13. EXPLANATION
        {
            "id": "EXPLANATION",
            "regex": re.compile(
                r"\bhow\s+does\b|\bexplain\s+how\b|\bexplain\b|\bwhat\s+does\s+[\w.]+\s+do\b|\bdescribe\b|\boverview\s+of\b",
                re.IGNORECASE,
            ),
            "primary_intent": QueryIntent.EXPLANATION,
            "relationship_type": RelationshipType.NONE,
            "graph_strategy": GraphStrategy.NONE,
            "answer_style": AnswerStyle.EXPLANATION,
            "reason_code": "EXPLICIT_EXPLANATION_PHRASE",
            "priority": 5,
        },
    ]

    def __init__(self, query_preprocessor: QueryPreprocessor | None = None) -> None:
        """Initialize QueryPlanner.

        Args:
            query_preprocessor: Optional QueryPreprocessor instance for query normalization and tokenization.
        """
        self.preprocessor = query_preprocessor or QueryPreprocessor()

    def plan(self, query: str | ProcessedQuery) -> QueryPlan:
        """Transform a raw text query or ProcessedQuery into an immutable QueryPlan.

        Args:
            query: Raw query string or Phase 5 ProcessedQuery object.

        Returns:
            QueryPlan model.

        Raises:
            InvalidQueryError: If query input is invalid, empty, or whitespace-only.
        """
        # 1. Resolve and validate ProcessedQuery
        if query is None:
            raise InvalidQueryError("Query cannot be None")

        if isinstance(query, str):
            if not query or not query.strip():
                raise InvalidQueryError("Query string cannot be empty or whitespace-only")
            processed_q = self.preprocessor.process(query)
        elif isinstance(query, ProcessedQuery):
            if not query.original_query or not query.original_query.strip():
                raise InvalidQueryError("ProcessedQuery original_query cannot be empty")
            processed_q = query
        else:
            raise InvalidQueryError(f"Unsupported query type: {type(query).__name__}")

        norm_query = processed_q.normalized_query

        # 2. Extract code identifiers and natural language terms
        identifiers = list(
            dict.fromkeys(
                processed_q.identifier_tokens + list(processed_q.qualified_name_candidates)
            )
        )
        natural_language_terms = processed_q.text_tokens

        # Extract explicit target entities
        explicit_entities = self._extract_explicit_entities(processed_q)
        inferred_entities: list[str] = []

        # Target entities combination (deduplicated)
        target_entities = list(dict.fromkeys(explicit_entities + inferred_entities))

        # 3. Detect negation
        has_negation = self._detect_negation(norm_query)

        # 4. Pattern matching & Intent / Relationship classification
        matches = self._find_matching_patterns(norm_query)

        primary_intent = QueryIntent.UNKNOWN
        secondary_intents: list[QueryIntent] = []
        relationship_type = RelationshipType.NONE
        graph_strategy = GraphStrategy.NONE
        answer_style = AnswerStyle.EXPLANATION
        retrieval_strategy = RetrievalStrategy.HYBRID
        reason_codes: list[str] = []
        confidence = 0.5
        operations: list[dict[str, Any]] = []

        if matches:
            # Sort matches by priority DESC
            matches.sort(key=lambda m: m["priority"], reverse=True)
            top_match = matches[0]

            primary_intent = top_match["primary_intent"]
            relationship_type = top_match["relationship_type"]
            graph_strategy = top_match["graph_strategy"]
            answer_style = top_match["answer_style"]
            reason_codes.append(top_match["reason_code"])
            confidence = 1.0 if target_entities or explicit_entities else 0.85

            # Secondary intents
            seen_intents = {primary_intent}
            for m in matches[1:]:
                intent = m["primary_intent"]
                if intent not in seen_intents and intent != QueryIntent.UNKNOWN:
                    secondary_intents.append(intent)
                    seen_intents.add(intent)
                    reason_codes.append(m["reason_code"])

            # Operations for compound queries
            if len(matches) > 1 or len(target_entities) > 1:
                operations = self._build_operations(matches, target_entities)

        else:
            # Fallback handling when no explicit pattern matches
            if processed_q.query_kind in (
                QueryKind.IDENTIFIER,
                QueryKind.QUALIFIED_IDENTIFIER,
                QueryKind.PATH_OR_FILE,
            ) or (len(identifiers) == 1 and not natural_language_terms):
                primary_intent = QueryIntent.SYMBOL
                answer_style = AnswerStyle.CODE_LOCATION
                retrieval_strategy = RetrievalStrategy.LEXICAL
                reason_codes.append("PURE_IDENTIFIER_PATTERN")
                confidence = 0.95
            elif natural_language_terms:
                primary_intent = QueryIntent.EXPLANATION
                answer_style = AnswerStyle.EXPLANATION
                retrieval_strategy = RetrievalStrategy.HYBRID
                reason_codes.append("FALLBACK_NATURAL_LANGUAGE")
                confidence = 0.7
            else:
                primary_intent = QueryIntent.UNKNOWN
                answer_style = AnswerStyle.EXPLANATION
                retrieval_strategy = RetrievalStrategy.HYBRID
                reason_codes.append("UNKNOWN_QUERY_PATTERN")
                confidence = 0.5

        if has_negation:
            reason_codes.append("NEGATION_DETECTED")

        # 5. Scope Determination
        scope = self._determine_scope(norm_query, processed_q, target_entities, primary_intent)

        # 6. Deduplicate reason codes preserving order
        reason_codes = list(dict.fromkeys(reason_codes))

        # 7. Construct and return frozen QueryPlan
        return QueryPlan(
            query=processed_q.original_query,
            normalized_query=processed_q.normalized_query,
            processed_query=processed_q,
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            target_entities=target_entities,
            explicit_entities=explicit_entities,
            inferred_entities=inferred_entities,
            identifiers=identifiers,
            natural_language_terms=natural_language_terms,
            relationship_type=relationship_type,
            retrieval_strategy=retrieval_strategy,
            graph_strategy=graph_strategy,
            scope=scope,
            answer_style=answer_style,
            confidence=confidence,
            reason_codes=reason_codes,
            operations=operations,
            has_negation=has_negation,
            metadata={
                "query_kind": processed_q.query_kind.value,
                "token_count": len(processed_q.tokens),
            },
        )

    def _find_matching_patterns(self, norm_query: str) -> list[dict[str, Any]]:
        """Find all matching intent/relationship patterns for the normalized query."""
        matches: list[dict[str, Any]] = []
        for p in self._PATTERNS:
            if p["regex"].search(norm_query):
                matches.append(p)
        return matches

    def _extract_explicit_entities(self, processed_q: ProcessedQuery) -> list[str]:
        """Extract explicit entity and symbol names mentioned in the query."""
        entities: list[str] = []

        # 1. Qualified name candidates from processor
        for cand in processed_q.qualified_name_candidates:
            if cand and cand not in entities:
                entities.append(cand)

        # 2. Identifiers (PascalCase, camelCase, snake_case)
        for tok in processed_q.identifier_tokens:
            if tok and tok not in entities:
                entities.append(tok)

        # 3. File names in query
        for token in processed_q.tokens:
            low_tok = token.lower()
            if (
                any(low_tok.endswith(ext) for ext in self._FILE_EXTENSIONS)
                or "/" in token
                or "\\" in token
            ):
                if token not in entities:
                    entities.append(token)

        return entities

    def _detect_negation(self, norm_query: str) -> bool:
        """Check if query contains negation words."""
        query_words = set(re.findall(r"\b\w+\b", norm_query.lower()))
        return any(neg in query_words for neg in self._NEGATION_WORDS) or any(
            phrase in norm_query.lower() for phrase in ("does not", "don't", "do not")
        )

    def _determine_scope(
        self,
        norm_query: str,
        processed_q: ProcessedQuery,
        target_entities: list[str],
        primary_intent: QueryIntent,
    ) -> QueryScope:
        """Determine granular code scope from query text and target entities."""
        low_q = norm_query.lower()

        # File scope check
        if (
            any(ext in low_q for ext in self._FILE_EXTENSIONS)
            or "/" in low_q
            or "\\" in low_q
            or "file" in low_q
        ):
            return QueryScope.FILE

        # Repository / Architecture scope check
        if primary_intent == QueryIntent.ARCHITECTURE or any(
            kw in low_q
            for kw in ("architecture", "system", "repository", "codebase", "overview", "project")
        ):
            return QueryScope.REPOSITORY

        # Module / Package scope check
        if "package" in low_q:
            return QueryScope.PACKAGE
        if "module" in low_q or "directory" in low_q:
            return QueryScope.MODULE

        # Class scope check
        if "class" in low_q or "interface" in low_q or "struct" in low_q:
            return QueryScope.CLASS

        # Symbol / Method / Function scope check
        if (
            processed_q.query_kind in (QueryKind.IDENTIFIER, QueryKind.QUALIFIED_IDENTIFIER)
            or target_entities
            or primary_intent == QueryIntent.SYMBOL
        ):
            return QueryScope.SYMBOL

        return QueryScope.UNKNOWN

    def _build_operations(
        self, matches: list[dict[str, Any]], target_entities: list[str]
    ) -> list[dict[str, Any]]:
        """Construct structured bounded operations sequence for compound queries."""
        ops: list[dict[str, Any]] = []
        target = target_entities[0] if target_entities else "all"

        for m in matches:
            op_dict: dict[str, Any] = {
                "intent": m["primary_intent"].value,
                "relationship": m["relationship_type"].value,
                "target": target,
            }
            if op_dict not in ops:
                ops.append(op_dict)

        return ops
