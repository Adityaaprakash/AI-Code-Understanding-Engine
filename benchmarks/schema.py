"""Phase 9A - Benchmark Schema."""

from enum import IntEnum, StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RelevanceGrade(IntEnum):
    IRRELEVANT = 0
    MARGINAL = 1
    RELEVANT = 2
    ESSENTIAL = 3


class QueryCategory(StrEnum):
    SYMBOL_DEFINITION = "SYMBOL_DEFINITION"
    SYMBOL_USAGE = "SYMBOL_USAGE"
    EXPLANATION = "EXPLANATION"
    CALL_RELATIONSHIP = "CALL_RELATIONSHIP"
    DEPENDENCY = "DEPENDENCY"
    IMPLEMENTATION = "IMPLEMENTATION"
    INHERITANCE = "INHERITANCE"
    IMPACT = "IMPACT"
    ARCHITECTURE = "ARCHITECTURE"
    FILE_PATH = "FILE_PATH"
    IDENTIFIER_HEAVY = "IDENTIFIER_HEAVY"
    AMBIGUOUS = "AMBIGUOUS"


class DifficultyLevel(StrEnum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class GraphRelationship(StrEnum):
    CALLS = "CALLS"
    USES = "USES"
    IMPLEMENTS = "IMPLEMENTS"
    EXTENDS = "EXTENDS"


class SymbolFixture(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol_id: str
    name: str
    qualified_name: str
    kind: str
    file_path: str
    start_line: int
    end_line: int
    language: str


class CodeChunkFixture(BaseModel):
    model_config = ConfigDict(frozen=True)
    chunk_id: str
    repository_id: str
    symbol_id: str | None = None
    file_path: str
    language: str
    chunk_type: str
    symbol_name: str | None = None
    qualified_name: str | None = None
    start_line: int
    end_line: int
    content: str
    doc_comment: str | None = None


class GraphEdgeFixture(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_symbol_id: str
    relationship: GraphRelationship
    target_symbol_id: str


class BenchmarkRepository(BaseModel):
    model_config = ConfigDict(frozen=True)
    repository_id: str
    name: str
    language: str
    description: str
    file_count: int
    approximate_loc: int
    symbol_count: int
    chunk_count: int
    symbols: list[SymbolFixture] = Field(default_factory=list)
    chunks: list[CodeChunkFixture] = Field(default_factory=list)
    graph_edges: list[GraphEdgeFixture] = Field(default_factory=list)


class RelevanceJudgment(BaseModel):
    model_config = ConfigDict(frozen=True)
    chunk_id: str
    grade: RelevanceGrade
    rationale: str

    @property
    def grade_value(self) -> int:
        return self.grade.value


class ExpectedFact(BaseModel):
    model_config = ConfigDict(frozen=True)
    fact_id: str
    claim: str
    supporting_chunk_ids: list[str]


class MultiHopPathStep(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol_id: str
    relationship: GraphRelationship
    next_symbol_id: str


class MultiHopPath(BaseModel):
    model_config = ConfigDict(frozen=True)
    path_id: str
    description: str
    steps: list[MultiHopPathStep]


class GraphGroundTruth(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_symbol_id: str
    relationship: GraphRelationship
    target_symbol_id: str
    description: str | None = None


class BenchmarkQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    query_id: str
    repository_id: str
    language: str
    category: QueryCategory
    difficulty: DifficultyLevel
    query_text: str
    query_variants: list[str] = Field(default_factory=list)
    relevance_judgments: list[RelevanceJudgment] = Field(default_factory=list)
    relevant_symbol_ids: list[str] = Field(default_factory=list)
    relevant_file_paths: list[str] = Field(default_factory=list)
    hard_negative_chunk_ids: list[str] = Field(default_factory=list)
    expected_facts: list[ExpectedFact] = Field(default_factory=list)
    graph_ground_truth: list[GraphGroundTruth] = Field(default_factory=list)
    multi_hop_paths: list[MultiHopPath] = Field(default_factory=list)


class BenchmarkMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)
    dataset_version: str = "9A.1"
    languages: list[str]
    repository_count: int
    total_file_count: int
    total_symbol_count: int
    total_chunk_count: int
    total_graph_edges: int
    query_count: int
    query_count_by_category: dict[str, int]
    query_count_by_difficulty: dict[str, int]
    query_count_by_language: dict[str, int]


class BenchmarkDataset(BaseModel):
    model_config = ConfigDict(frozen=True)
    metadata: BenchmarkMetadata
    repositories: list[BenchmarkRepository] = Field(default_factory=list)
    queries: list[BenchmarkQuery] = Field(default_factory=list)

    def get_repository(self, repository_id: str) -> BenchmarkRepository | None:
        for r in self.repositories:
            if r.repository_id == repository_id:
                return r
        return None

    def get_chunk(self, repository_id: str, chunk_id: str) -> CodeChunkFixture | None:
        repo = self.get_repository(repository_id)
        if repo:
            for c in repo.chunks:
                if c.chunk_id == chunk_id:
                    return c
        return None

    def get_symbol(self, repository_id: str, symbol_id: str) -> SymbolFixture | None:
        repo = self.get_repository(repository_id)
        if repo:
            for s in repo.symbols:
                if s.symbol_id == symbol_id:
                    return s
        return None
