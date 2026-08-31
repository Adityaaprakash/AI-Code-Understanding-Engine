# Current State — AI Code Understanding Engine

## Active Phase

**Phase 4 — Code Chunking & Indexing**

---

## Current Task

TASK-4D — Code-Aware Lexical Indexing (BM25) complete. Phase 4 Indexing and Chunking complete.

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
  - Defined `LexicalIndexContract` in `retrieval/contracts.py` for indexing and search contracts.
  - Implemented immutable Pydantic models `LexicalDocument`, `LexicalSearchResult`, and `LexicalSearchResultSet` in `retrieval/lexical_models.py`.
  - Created code-aware `CodeTokenizer` in `retrieval/tokenizer.py` handling camelCase, PascalCase, snake_case, SCREAMING_SNAKE_CASE, acronyms, qualified names, file paths, and code keywords.
  - Implemented `LexicalTextBuilder` in `retrieval/lexical_text_builder.py` with field weighting (symbol names 3x, qualified names 3x, file paths 2x, signatures 2x, doc comments 1.5x, content 1x).
  - Implemented `BM25LexicalIndex` and `RepositoryBM25Index` in `retrieval/lexical_index.py` featuring Robertson-Spärck Jones BM25 algorithm ($k_1=1.5, b=0.75$), IDF smoothing, strict repository isolation, metadata filtering, and deterministic tie-breaking.
  - Added exception hierarchy `LexicalIndexError`, `LexicalConfigurationError`, `LexicalDocumentError`, `LexicalQueryError` in `retrieval/exceptions.py`.
  - Built comprehensive unit test suite `tests/test_lexical_index.py` covering tokenization, exact matching, field weighting, repository isolation, lifecycle management, BM25 math properties, cross-language parity (Java, Python, TypeScript), scale performance, and immutability.
  - All 331/331 tests pass cleanly with 100% ruff check, ruff format, and mypy compliance.
  - Defined provider abstraction `EmbeddingProviderContract` in `retrieval/contracts.py`.
  - Implemented immutable input and result models (`EmbeddingInput`, `EmbeddingResult`, `EmbeddingFailure`, `EmbeddingBatchResult`) in `retrieval/embedding_models.py` with vector dimension and numeric sanity validation (no NaN/Inf).
  - Created `EmbeddingTextBuilder` in `retrieval/text_builder.py` prioritizing source code while enriching with language, symbol name, qualified name, signature, parent entity, and doc comment headers, with fallback for empty source bodies.
  - Implemented `DeterministicTestEmbeddingProvider` in `retrieval/providers.py` using SHA-256 digest hashing to produce deterministic, normalized vectors with zero external network or GPU dependencies.
  - Implemented pluggable `HostedAPIEmbeddingProvider` in `retrieval/providers.py` using `httpx` for optional external/remote embedding services.
  - Created `EmbeddingPipeline` in `retrieval/embedding_pipeline.py` providing batch execution, batch boundary processing, duplicate chunk ID detection, retry policies for transient errors, and vector dimension verification.
  - Built comprehensive test suite `tests/test_embedding_pipeline.py` covering text builder formatting, deterministic provider output, pipeline batching, duplicate chunk ID rejection, fault injection retries, cross-language parity (Java, Python, TypeScript), performance batch ratio verification, and IR/chunk immutability.
  - All 304/304 tests pass cleanly with 100% ruff check, ruff format, and mypy compliance.

---

## In Progress

- TASK-4D — BM25 & Hybrid Indexing Foundation (Next)

---

## Blocked / Pending

### Phase 1 (Foundation & Core Infrastructure) — ✅ Phase Complete
- [x] 1B: Python runtime setup — ✅ Done
- [x] 1C: Database foundation — ✅ Done
- [x] 1D: FastAPI skeleton — ✅ Done
- [x] 1E: Test infrastructure — ✅ Done
- [x] 1F: Docker Compose foundation — ✅ Done
- [x] 1G: Frontend scaffold — ✅ Done
- [x] 1H: Phase 1 verification — ✅ Done

### Phase 2 (Ingestion, AST & Canonical Code IR) — ✅ Phase Complete
- [x] 2A: Parser Abstraction — ✅ Done
- [x] 2B: Java AST — ✅ Done
- [x] 2C: Python AST — ✅ Done
- [x] 2D: TypeScript AST — ✅ Done
- [x] 2E: Canonical Code IR Definition — ✅ Done
- [x] 2F: AST → Code IR Normalization — ✅ Done
- [x] 2G: Parser / Canonical IR Testing & Hardening — ✅ Done

### Phase 3 (Symbol Resolution & Code Knowledge Graph)
- [x] 3A: Code Graph Schema & Models — ✅ Done
- [x] 3B/3C: Symbol, Import & Reference Resolution — ✅ Done
- [x] 3D: Symbol Relationship Extraction — ✅ Done
- [ ] 3E: Graph Persistence & Querying
- [ ] 3F: Dependency & Impact Analysis

---

## Known Decisions Made This Phase

- Graph architecture operates purely on derived entities from Canonical Code IR without modifying Phase 2 IR models.
- Abstract contract interfaces (`contracts.py`) specify signatures for Phase 3 symbol resolution, import resolution, reference resolution, relationship extraction, persistence, and traversal engines.
- Symbol resolution is strictly high-precision and deterministic: when evidence is insufficient or multiple candidates exist, `UNRESOLVED` or `AMBIGUOUS` is returned rather than guessing.
- Relationship extraction strictly filters for `RESOLVED` status: unresolved, ambiguous, builtin, or external references yield no repository-local graph edges.

---

## Last Updated

2026-08-29 — TASK-3D complete. RelationshipExtractor implemented with language integration tests for Java, Python, and TypeScript, full end-to-end CodeGraph pipeline verification, and 201/201 tests passing. Next task is TASK-3E — Graph Persistence & Querying.



