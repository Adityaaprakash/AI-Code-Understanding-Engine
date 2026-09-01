# Current State — AI Code Understanding Engine

## Active Phase

**Phase 5 — Hybrid Retrieval Engine IN PROGRESS** (TASK-5A + TASK-5B + TASK-5C COMPLETE)

---

## Current Task

TASK-5C (Vector Retrieval) complete. Next task is TASK-5D (Graph Retrieval).


---

## Completed

- [x] Project specification established
- [x] Architecture established
- [x] Core constraints established
- [x] Top-level directory structure created
- [x] `.gitignore` created
- [x] `.env.example` created
- [x] `README.md` created
- [x] `.ai/` project-memory files created and populated
- [x] TASK-1B: Python runtime setup complete
- [x] TASK-1C: Database foundation complete
- [x] TASK-1D: FastAPI foundation complete
- [x] TASK-1E: Test infrastructure complete
- [x] TASK-1F: Docker Compose Foundation complete
- [x] TASK-1G: Frontend Scaffold complete
- [x] TASK-1H: Phase 1 Verification complete
- [x] TASK-2A: Parser Abstraction complete
- [x] TASK-2B: Java AST complete
- [x] TASK-2C: Python AST complete
- [x] TASK-2D: TypeScript AST complete
- [x] TASK-2E: Canonical Code IR complete
- [x] TASK-2F: AST → Code IR Normalization complete
- [x] TASK-2G: Parser / Canonical IR Testing & Hardening complete
- [x] TASK-3A: Code Graph Schema & Models complete
- [x] TASK-3B/3C: Symbol, Import & Reference Resolution complete
- [x] TASK-3D: Relationship Extraction complete
- [x] TASK-3E/3F: Graph Storage Engine & Traversal Query Engine complete
- [x] TASK-3G: Code Knowledge Graph Testing & Hardening complete
- [x] TASK-3H: Initial Impact Analysis complete
- [x] TASK-4A: AST/IR-Aware Code Chunking complete
- [x] TASK-4B: Code Chunk Metadata Enrichment complete
- [x] TASK-4C: Dense Vector Embedding Infrastructure complete
- [x] TASK-4D: Code-Aware Lexical Indexing (BM25) complete
- [x] TASK-4E: Phase 4 Index Testing & Hardening complete
- [x] TASK-5A: Query Preprocessing complete
- [x] TASK-5B: BM25 / Lexical Retrieval complete
- [x] TASK-5C: Vector Retrieval complete
  - Defined `VectorIndexContract` and `VectorRetrieverContract` interfaces in `retrieval/contracts.py`.
  - Created `VectorDocument` and `VectorSearchResult` models in `retrieval/vector_models.py`.
  - Created `VectorIndex` and `RepositoryVectorIndex` in `retrieval/vector_index.py` performing exact cosine similarity vector search with repository isolation and metadata filtering (`language`, `chunk_type`, `file_path`, `commit_sha`).
  - Added `VectorIndexError`, `VectorConfigurationError`, `VectorDocumentError`, `VectorQueryError` in `retrieval/exceptions.py`.
  - Implemented `VectorRetriever` service in `retrieval/vector_retriever.py` orchestrating `ProcessedQuery` input, query vector generation via `EmbeddingProviderContract` (`DeterministicTestEmbeddingProvider` by default), vector search execution, latency tracking, and candidate result mapping into standard `RetrievalResultSet`.
  - Built comprehensive unit & integration test suite `tests/test_vector_retriever.py` containing 18 tests covering basic retrieval, semantic queries, identifier/mixed queries, filter behavior, mandatory cross-repository isolation, referential integrity (`RetrievalResult.chunk_id` == `CodeChunk.id`), input validation, zero-result handling, top-k limiting, deterministic ordering & repeated query stability, index immutability, query vector dimension validation, no chunk re-embedding during search, scale performance (1,000+ chunks sub-second), JSON serialization roundtripping, and duplicate ID prevention.
- [x] TASK-5D: Graph Retrieval complete
  - Defined `GraphRetrieverContract` interface in `retrieval/contracts.py`.
  - Added `GraphRetrievalError`, `GraphQueryError`, `GraphStoreNotFoundError` in `retrieval/exceptions.py`.
  - Implemented `GraphRetriever` service in `retrieval/graph_retriever.py` orchestrating structural relationship query interpretation (CALLS, CALLEES, IMPLEMENTS, EXTENDS, DEPENDENT, DEPENDENCY, IMPORTS, USES, IMPACT, IDENTIFIER) using `QueryPreprocessor` output and regex pattern matching.
  - Integrated `GraphRetriever` with Phase 3 `GraphQueryEngine` and `ImpactAnalyzer` for cycle-safe, depth-bounded graph traversals.
  - Mapped Phase 3 graph nodes into standard Phase 5 `RetrievalResult` candidates, enriching metadata with `graph_relationship`, `graph_direction`, and `graph_depth` while preserving canonical `CodeChunk` identities.
  - Enforced strict repository-level isolation, deterministic candidate ranking (score DESC, depth ASC, symbol_name ASC, chunk_id ASC), metadata filtering (`language`, `chunk_type`, `file_path`, `commit_sha`), latency metrics tracking, and immutability of the underlying Phase 3 graph.
  - Built comprehensive unit & integration test suite in `tests/test_graph_retriever.py` with 19 test cases.
- [x] TASK-5E: Candidate Fusion complete
  - Defined `CandidateFusionContract` interface in `retrieval/contracts.py`.
  - Created `RetrievalSource` StrEnum in `retrieval/enums.py` (`BM25`, `VECTOR`, `GRAPH`).
  - Added `CandidateFusionError`, `FusionQueryError`, `FusionRepositoryError`, `FusionVersionError` in `retrieval/exceptions.py`.
  - Enhanced `RetrievalResult` and `RetrievalResultSet` in `retrieval/retrieval_models.py` with optional source evidence attributes (`sources`, `bm25_rank`, `vector_rank`, `graph_rank`, `bm25_score`, `vector_score`, `graph_score`, `fused_score`, `fusion_latency_ms`) while maintaining 100% backwards compatibility with Phase 5B/5C/5D retrievers.
  - Implemented `CandidateFusionEngine` service in `retrieval/candidate_fusion.py` implementing Reciprocal Rank Fusion ($RRF(c) = \sum 1 / (k + rank)$ with $k=60$ default).
  - Enforced canonical candidate identity merging strictly by `chunk_id`, cross-retriever deduplication, single-source candidate survival, multi-source contribution accumulation, 100% deterministic tie-breaking (`fused_score DESC`, `chunk_id ASC`), repository boundary isolation validation, version/commit_sha consistency validation, query text consistency validation, and latency tracking (`fusion_latency_ms`).
  - Built comprehensive unit & integration test suite in `tests/test_candidate_fusion.py` containing 16 test cases validating exact RRF math, deduplication, evidence preservation, single/multi-source handling, empty branches, top-k limiting, determinism (100 repetitions), tie-breaking, repository isolation, commit SHA version isolation, query consistency, Pydantic JSON roundtripping, and sub-second performance scaling on 1,000+ candidates per branch.

  - All 429 tests pass cleanly with 100% ruff check, ruff format, and mypy compliance.

---

## In Progress

- TASK-5F — Reranking (Next)

---

## Blocked / Pending

### Phase 5 (Hybrid Retrieval Engine)
- [x] 5A: Query Preprocessing — ✅ Done
- [x] 5B: Lexical / BM25 Retrieval — ✅ Done
- [x] 5C: Vector Retrieval — ✅ Done
- [x] 5D: Graph Retrieval — ✅ Done
- [x] 5E: Candidate Fusion — ✅ Done
- [ ] 5F: Reranking
- [ ] 5G: Retrieval Evaluation & Benchmarking


---

## Known Decisions Made This Phase

- Phase 5 is an orchestration and retrieval layer consuming Phase 4 indexing infrastructure without duplicating or re-indexing documents during search.
- Preprocessing and retrieval contracts enforce immutability (`frozen=True`) and strict repository isolation (`repository_id`).
- Lexical retrieval preserves the exact canonical chunk identity created in Phase 4 (`RetrievalResult.chunk_id` == `CodeChunk.id`).

---

## Last Updated

2026-08-31 — TASK-5A and TASK-5B complete. `QueryPreprocessor` and `LexicalRetriever` implemented with 376/376 tests passing, 100% lint and type compliance. Next task is TASK-5C — Vector Retrieval.
