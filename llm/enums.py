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
