"""Enumerations for Phase 6 Query Intent & Query Planning layer."""

from enum import StrEnum


class QueryIntent(StrEnum):
    """Core user question intent categories in Phase 6."""

    EXPLANATION = "explanation"
    DEPENDENCY = "dependency"
    ARCHITECTURE = "architecture"
    SYMBOL = "symbol"
    IMPACT = "impact"
    DEBUGGING = "debugging"
    UNKNOWN = "unknown"


class RelationshipType(StrEnum):
    """Structural or semantic code relationship types extracted from queries."""

    CALLS = "calls"
    CALLERS = "callers"
    DEPENDENCIES = "dependencies"
    DEPENDENTS = "dependents"
    IMPLEMENTS = "implements"
    EXTENDS = "extends"
    IMPORTS = "imports"
    USES = "uses"
    REFERENCES = "references"
    IMPACT = "impact"
    NONE = "none"


class RetrievalStrategy(StrEnum):
    """Recommended retrieval engine branch strategies for downstream retrieval."""

    LEXICAL = "lexical"
    SEMANTIC = "semantic"
    GRAPH = "graph"
    HYBRID = "hybrid"


class GraphStrategy(StrEnum):
    """Recommended Code Knowledge Graph operation strategies for context expansion."""

    NONE = "none"
    CALLERS = "callers"
    CALLEES = "callees"
    DEPENDENCIES = "dependencies"
    DEPENDENTS = "dependents"
    IMPLEMENTATIONS = "implementations"
    INHERITANCE = "inheritance"
    IMPORTS = "imports"
    USAGES = "usages"
    IMPACT_RADIUS = "impact_radius"
    ARCHITECTURAL_EXPANSION = "architectural_expansion"


class QueryScope(StrEnum):
    """Granular code scope implied by user query."""

    SYMBOL = "symbol"
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    PACKAGE = "package"
    COMPONENT = "component"
    REPOSITORY = "repository"
    UNKNOWN = "unknown"


class AnswerStyle(StrEnum):
    """Expected formatting or style of answer generation downstream."""

    EXPLANATION = "explanation"
    LIST = "list"
    RELATIONSHIP = "relationship"
    ARCHITECTURE = "architecture"
    DEBUGGING_ANALYSIS = "debugging_analysis"
    IMPACT_ANALYSIS = "impact_analysis"
    CODE_LOCATION = "code_location"


class RankingReasonCode(StrEnum):
    """Structured explanation reason codes for candidate context ranking."""

    DIRECT_QUERY_TARGET = "DIRECT_QUERY_TARGET"
    PRIMARY_INTENT_MATCH = "PRIMARY_INTENT_MATCH"
    SECONDARY_INTENT_MATCH = "SECONDARY_INTENT_MATCH"
    RELATIONSHIP_MATCH = "RELATIONSHIP_MATCH"
    RETRIEVAL_EVIDENCE = "RETRIEVAL_EVIDENCE"
    GRAPH_EVIDENCE = "GRAPH_EVIDENCE"
    MULTI_SOURCE_EVIDENCE = "MULTI_SOURCE_EVIDENCE"
    GRAPH_PROXIMITY = "GRAPH_PROXIMITY"
    SCOPE_MATCH = "SCOPE_MATCH"
    SAME_SYMBOL = "SAME_SYMBOL"
    SAME_FILE = "SAME_FILE"
    SUPPORTING_CONTEXT = "SUPPORTING_CONTEXT"


class PruningReasonCode(StrEnum):
    """Structured explanation reason codes for candidate context deduplication and pruning."""

    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    LOGICAL_DUPLICATE = "LOGICAL_DUPLICATE"
    NEAR_DUPLICATE = "NEAR_DUPLICATE"
    BELOW_SCORE_THRESHOLD = "BELOW_SCORE_THRESHOLD"
    MAX_CANDIDATES_EXCEEDED = "MAX_CANDIDATES_EXCEEDED"
    REDUNDANT_SYMBOL = "REDUNDANT_SYMBOL"
    REDUNDANT_FILE = "REDUNDANT_FILE"
    REDUNDANT_EVIDENCE = "REDUNDANT_EVIDENCE"
    STRUCTURAL_COVERAGE_POLICY = "STRUCTURAL_COVERAGE_POLICY"


class ContextOverflowPolicy(StrEnum):
    """Action policy when a context candidate exceeds remaining evidence budget."""

    SKIP = "SKIP"
    TRUNCATE = "TRUNCATE"


class TokenCountMode(StrEnum):
    """Indicates whether token counts are exact model tokenizer counts or fallback estimates."""

    EXACT = "exact"
    ESTIMATED = "estimated"


class ContextPackingReasonCode(StrEnum):
    """Structured explanation reason codes for candidate context omission during budgeting."""

    TOKEN_BUDGET_EXCEEDED = "TOKEN_BUDGET_EXCEEDED"
    CANDIDATE_TOO_LARGE = "CANDIDATE_TOO_LARGE"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    TRUNCATION_DISABLED = "TRUNCATION_DISABLED"
