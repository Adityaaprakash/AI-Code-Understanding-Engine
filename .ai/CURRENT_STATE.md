# Current State — AI Code Understanding Engine

## Active Phase

**Phase 5 — Hybrid Retrieval Engine IN PROGRESS** (TASK-5A Query Preprocessing + TASK-5B Lexical Retrieval COMPLETE)

---

## Current Task

TASK-5A (Query Preprocessing) & TASK-5B (BM25 / Lexical Retrieval) complete. Next task is TASK-5C (Vector Retrieval).

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
  - Implemented `QueryKind` enum and `ProcessedQuery` immutable Pydantic model (`frozen=True`) in `retrieval/query_models.py`.
  - Implemented `QueryPreprocessor` in `retrieval/query_processor.py` featuring unicode NFC normalization, whitespace collapsing, casing preservation, camelCase/PascalCase/snake_case/acronym detection, qualified identifier extraction, path detection, prose indicator filtering, and deterministic `QueryKind` classification (`IDENTIFIER`, `QUALIFIED_IDENTIFIER`, `PATH_OR_FILE`, `RELATIONSHIP`, `NATURAL_LANGUAGE`, `MIXED`, `UNKNOWN`).
  - Added empty query validation raising `LexicalQueryError`.
  - Built unit test suite `tests/test_query_preprocessing.py` validating 24 test cases covering query matrix, normalization, immutability, and JSON roundtrip serialization.
- [x] TASK-5B: BM25 / Lexical Retrieval complete
  - Defined `LexicalRetrieverContract` interface in `retrieval/contracts.py`.
  - Implemented immutable `LexicalRetrievalRequest`, `RetrievalResult`, and `RetrievalResultSet` models in `retrieval/retrieval_models.py` with score/rank validation, single-source identity (`RetrievalResult.chunk_id` == `CodeChunk.id`), and latency metrics (`preprocessing_latency_ms`, `retrieval_latency_ms`, `total_latency_ms`).
  - Updated `BM25LexicalIndex` and `RepositoryBM25Index` in `retrieval/lexical_index.py` with support for optional `file_path` and `commit_sha` filtering and full metadata preservation (`qualified_name`, `start_line`, `end_line`, `metadata`).
  - Implemented `LexicalRetriever` service in `retrieval/lexical_retriever.py` orchestrating query preprocessing, repository isolation boundary checks, BM25 index search, and candidate result ranking.
  - Built comprehensive unit & integration test suite `tests/test_lexical_retriever.py` verifying end-to-end flow, strict cross-repository isolation (Repo A vs Repo B), adversarial symbol field-weighting advantage (symbol name matches beat content term repetition), metadata preservation, zero-result handling, invalid input validation, scale performance (1,000+ chunks sub-second execution), index immutability, and JSON serialization.
  - All 376 tests (376 active, 4 skipped) pass cleanly with 100% ruff check, ruff format, and mypy compliance.

---

## In Progress

- TASK-5C — Vector Retrieval (Next)

---

## Blocked / Pending

### Phase 5 (Hybrid Retrieval Engine)
- [x] 5A: Query Preprocessing — ✅ Done
- [x] 5B: BM25 / Lexical Retrieval — ✅ Done
- [ ] 5C: Vector Retrieval
- [ ] 5D: Graph Retrieval
- [ ] 5E: Candidate Fusion (RRF / Hybrid)
- [ ] 5F: Cross-Encoder Reranking
- [ ] 5G: Retrieval Evaluation & Benchmarking

---

## Known Decisions Made This Phase

- Phase 5 is an orchestration and retrieval layer consuming Phase 4 indexing infrastructure without duplicating or re-indexing documents during search.
- Preprocessing and retrieval contracts enforce immutability (`frozen=True`) and strict repository isolation (`repository_id`).
- Lexical retrieval preserves the exact canonical chunk identity created in Phase 4 (`RetrievalResult.chunk_id` == `CodeChunk.id`).

---

## Last Updated

2026-08-31 — TASK-5A and TASK-5B complete. `QueryPreprocessor` and `LexicalRetriever` implemented with 376/376 tests passing, 100% lint and type compliance. Next task is TASK-5C — Vector Retrieval.
