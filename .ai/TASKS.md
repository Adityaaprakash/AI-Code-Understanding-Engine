# Tasks — Phase 1 (Foundation)

> Pick tasks from the **Ready** column. A task is ready when all its blockers
> are marked ✅ Done.
> Update this file after completing each task.

---

## Completed

### TASK-1A: Repository structure and `.ai/` project memory

**Status:** ✅ Done  
**Blockers:** None  
**Deliverables:**
- Top-level directories: `backend/`, `frontend/`, `code-analyzer/`, `retrieval/`,
  `graph/`, `llm/`, `evaluation/`, `experiments/`, `docs/`, `docker/`, `tests/`
- `.gitignore`
- `.env.example`
- `README.md`
- All `.ai/` project-memory files

---

### TASK-1B: Python runtime setup

**Status:** ✅ Done  
**Blockers:** TASK-1A ✅  
**Deliverables:**
- `pyproject.toml` — PEP 621 project config with all runtime + dev deps
- `.python-version` — pinned to `3.12`
- `backend/__init__.py` — package marker
- `backend/py.typed` — PEP 561 typed package marker
- `tests/__init__.py` — test package marker
- `tests/test_python_env.py` — 8-test environment smoke suite
- `uv sync` installs Python 3.12.14 + 45 packages cleanly
- Checks: `ruff check` ✅ `ruff format --check` ✅ `mypy backend/` ✅ `pytest` (8/8) ✅

---

## Ready (can be started now)

### TASK-1B: Python runtime setup

**Status:** ✅ Done  
**Blockers:** TASK-1A ✅  
**Deliverables (all criteria met):**
- [x] `pyproject.toml` with all runtime + dev deps (PEP 621 / dependency-groups)
- [x] `.python-version` pinned to `3.12`
- [x] `[tool.ruff]` configured (lint + format, py312 target)
- [x] `[tool.mypy]` configured
- [x] `backend/__init__.py` and `backend/py.typed` created
- [x] `uv sync` installs Python 3.12.14 + 45 packages, exits 0
- [x] `ruff check .` — All checks passed (0 errors)
- [x] `ruff format --check .` — 17 files already formatted
- [x] `mypy backend/` — Success: no issues found
- [x] `pytest tests/` — 8 passed in 2.56s

---

### TASK-1G: Frontend scaffold

**Status:** ⬜ Pending  
**Blockers:** TASK-1A ✅  
**Scope:** Frontend scaffold only; no UI components or API integration.

**Acceptance criteria:**
- [ ] `frontend/` contains a working Vite + React + TypeScript project
- [ ] ESLint and Prettier configured
- [ ] `npm run dev` starts the dev server without errors
- [ ] `npm run build` produces a production bundle without errors
- [ ] `npm run lint` passes with zero errors

---

## Blocked on 1B (Python runtime) — 1B is now ✅ Done; these tasks are Ready

### TASK-1C: Database foundation

**Status:** ✅ Done  
**Blockers:** TASK-1B ✅  
**Deliverables (all criteria met):**
- [x] `backend/db/` package with SQLAlchemy Base, async engine, and session factory
- [x] Alembic configured with async engine and `db_settings`
- [x] All 7 ORM models matching `DATABASE_SCHEMA.md` exactly
- [x] `0001_initial_schema` migration with `pgvector` and `pg_trgm` extensions, constraints, and indexes
- [x] Docker Compose minimal PostgreSQL 16 service in `docker/docker-compose.dev.yml`
- [x] Real PostgreSQL migration lifecycle test (`upgrade head` -> `downgrade base` -> `upgrade head`) passes
- [x] All quality checks pass: ruff check ✅ ruff format ✅ mypy ✅ pytest (11/11) ✅

---

### TASK-1D: FastAPI skeleton

**Status:** ✅ Done  
**Blockers:** TASK-1B ✅, TASK-1C ✅  
**Deliverables (all criteria met):**
- [x] `backend/main.py` — FastAPI app factory `create_app()` and module-level `app`
- [x] `GET /health` returns `{"status": "ok"}` with HTTP 200
- [x] CORS middleware configured via `settings.CORS_ORIGINS`
- [x] Global exception handlers return structured `{"error": {...}}` envelopes without stack traces in responses
- [x] Request validation errors return HTTP 422 with structured body
- [x] `uvicorn backend.main:app` starts without errors and serves `/health`, `/docs`, `/openapi.json`
- [x] `mypy backend/` passes cleanly (0 errors)

---

### TASK-1E: Test infrastructure

**Status:** ✅ Done  
**Blockers:** TASK-1B ✅, TASK-1C ✅, TASK-1D ✅  
**Deliverables (all criteria met):**
- [x] `[tool.pytest.ini_options]` in `pyproject.toml` with strict markers (`unit`, `api`, `integration`, `db`)
- [x] `tests/conftest.py` with `app_instance`, `async_client`, `sync_client`, `database_url`, `db_engine`, `db_session` fixtures
- [x] `tests/test_health.py` — smoke test: `GET /health` returns HTTP 200
- [x] `tests/test_infrastructure.py` — infrastructure test suite verifying markers, async HTTP client, and PostgreSQL transaction isolation
- [x] `scripts/ci_check.py` local/CI quality check script
- [x] `pytest tests/` passes with 27 passed, zero failures
- [x] Code coverage report generated (`pytest --cov=backend` -> 92% coverage)

---

## Blocked on 1B + 1C + 1D + 1E

### TASK-1F: Docker Compose foundation

**Status:** ✅ Done  
**Blockers:** TASK-1C ✅, TASK-1D ✅, TASK-1E ✅  
**Scope:** Docker Compose that brings up postgres + backend + worker; no frontend
service needed for this task.

**Acceptance criteria:**
- [x] `docker/docker-compose.yml` with services: `postgres`, `backend`, `worker`
- [x] `docker/Dockerfile.backend` — Python image, installs deps, runs uvicorn
- [x] `docker/Dockerfile.worker` — same image, runs worker entrypoint
- [x] `docker compose up` starts all services without errors
- [x] `GET http://localhost:8000/health` returns HTTP 200 when running
- [x] PostgreSQL data persisted in a named Docker volume
- [x] All secrets sourced from `.env` file / env variable defaults (not hardcoded in Compose file)

---

### TASK-1G: Frontend scaffold

**Status:** ✅ Done
**Blockers:** TASK-1D ✅, TASK-1F ✅
**Scope:** Vite + React + TypeScript scaffold with ESLint, Prettier, and API service layer foundation.

**Acceptance criteria:**
- [x] Vite + React + TypeScript project created in `frontend/`
- [x] ESLint configured and passing (`npm run lint` -> 0 errors)
- [x] Prettier configured and passing (`npm run format:check`)
- [x] `npm run build` succeeds (TypeScript compilation + Vite bundling)
- [x] Minimal CodeLens AI app shell created (`App.tsx`, `HomePage.tsx`, `Header.tsx`, `index.css`)
- [x] Directory structure established (`components/`, `pages/`, `services/`, `types/`, `hooks/`)
- [x] API client boundary in `src/services/api.ts` accessing `import.meta.env.VITE_API_BASE_URL`
- [x] Backend regression test suite passes cleanly (27/27 passed)

---

### TASK-1H: Phase 1 Final Verification

**Status:** ✅ Done
**Blockers:** TASK-1A ✅, TASK-1B ✅, TASK-1C ✅, TASK-1D ✅, TASK-1E ✅, TASK-1F ✅, TASK-1G ✅
**Scope:** Final verification gate for Phase 1 Foundation stack.

**Acceptance criteria:**
- [x] Repository structure, `.ai/` memory, and configuration files verified
- [x] Python 3.12 runtime, ruff lint, ruff format, and mypy type checks pass
- [x] PostgreSQL 16 + pgvector extension + 7 domain tables + Alembic migration lifecycle verified
- [x] FastAPI `/health`, `/openapi.json`, `/docs`, `/api/v1` endpoints verified
- [x] Worker container startup, DB check, and graceful shutdown verified
- [x] Docker Compose 3-service stack (`postgres`, `backend`, `worker`) healthy and operational
- [x] Frontend build, ESLint, Prettier, Vite dev server, and backend communication verified
- [x] All 27 pytest tests pass with zero regressions
- [x] Git workspace clean of accidental artifacts or temporary debug scripts

---

## Phase 2 — Ingestion, AST & Canonical Code IR

### TASK-2A: Parser Abstraction

**Status:** ✅ Done  
**Blockers:** Phase 1 ✅  
**Scope:** Establish language-independent parser abstraction contract, models, diagnostics, and language parser stubs.

**Acceptance criteria:**
- [x] Language-independent `LanguageParser` abstract base class contract
- [x] Strongly typed `Language` enum (`java`, `python`, `typescript`) and `DiagnosticSeverity` enum
- [x] Consistent `ParseDiagnostic` and `ParseResult` abstractions with success/failure helpers
- [x] Concrete parser stubs `JavaParser`, `PythonParser`, `TypeScriptParser` inheriting from `LanguageParser`
- [x] `code-analyzer/code_analyzer/parsers/` module structure with PEP 561 marker
- [x] Unit test suite in `tests/test_parser_abstraction.py` verifying contract, models, diagnostics, and stubs
- [x] All quality checks pass (`uv sync`, `ruff check`, `ruff format --check`, `mypy backend/ code-analyzer/`, `pytest tests/`)

---

## Ready (Phase 2)

### TASK-2B: Java AST Parser

**Status:** ✅ Done  
**Blockers:** TASK-2A ✅  
**Scope:** Implement tree-sitter AST parsing and structural extraction logic for Java source files.

**Acceptance criteria:**
- [x] Tree-sitter Java dependencies added (`tree-sitter>=0.22.0`, `tree-sitter-java>=0.21.0`)
- [x] Strongly typed Java extraction models (`JavaStructure`, `JavaClass`, `JavaMethod`, `JavaField`, `JavaImport`, `JavaPackage`, `JavaParameter`, `SourceLocation`)
- [x] `JavaParser` concrete implementation returning `ParseResult` with language `Language.JAVA`
- [x] Structural extraction of package declarations, normal/static/wildcard imports, classes, interfaces, constructors, methods, fields, nested declarations, and generic declarations
- [x] Source locations preserved (1-indexed start/end lines, 0-indexed start/end columns)
- [x] Graceful error handling for syntax errors via `ParseDiagnostic` without crashing
- [x] Dedicated test suite in `tests/test_java_parser.py` (11 passing tests)
- [x] All quality checks pass (`uv sync`, `ruff check`, `ruff format --check`, `mypy backend/ code-analyzer/`, `pytest tests/`)

---

### TASK-2C: Python AST Parser

**Status:** ✅ Done  
**Blockers:** TASK-2B ✅  
**Scope:** Implement tree-sitter AST parsing and structural extraction logic for Python source files.

**Acceptance criteria:**
- [x] Tree-sitter Python dependency added (`tree-sitter-python>=0.21.0`)
- [x] Strongly typed Python extraction models (`PythonModule`, `PythonClass`, `PythonFunction`, `PythonField`, `PythonImport`, `PythonDecorator`, `PythonParameter`, `SourceLocation`)
- [x] `PythonParser` concrete implementation returning `ParseResult` with language `Language.PYTHON`
- [x] Structural extraction of imports, module functions, classes, methods, async functions, import aliases, decorators, decorated classes, and nested declarations
- [x] Source locations preserved (1-indexed start/end lines, 0-indexed start/end columns)
- [x] Graceful error handling for syntax errors via `ParseDiagnostic` without crashing
- [x] Dedicated test suite in `tests/test_python_parser.py` (12 passing tests)
- [x] All quality checks pass (`uv sync`, `ruff check`, `ruff format --check`, `mypy backend/ code-analyzer/`, `pytest tests/`)

---

### TASK-2D: TypeScript AST Parser

**Status:** ✅ Done  
**Blockers:** TASK-2C ✅  
**Scope:** Implement tree-sitter AST parsing and structural extraction logic for TypeScript source files.

**Acceptance criteria:**
- [x] Tree-sitter TypeScript dependency added (`tree-sitter-typescript>=0.21.0`)
- [x] Strongly typed TypeScript extraction models (`TypeScriptStructure`, `TypeScriptClass`, `TypeScriptInterface`, `TypeScriptFunction`, `TypeScriptField`, `TypeScriptImport`, `TypeScriptExport`, `TypeScriptType`, `TypeScriptParameter`, `SourceLocation`)
- [x] `TypeScriptParser` concrete implementation returning `ParseResult` with language `Language.TYPESCRIPT`
- [x] Structural extraction of imports, exports, classes, interfaces, functions, async functions, generics, named export aliases, type aliases, constructors, fields, methods
- [x] Source locations preserved (1-indexed start/end lines, 0-indexed start/end columns)
- [x] Graceful error handling for syntax errors via `ParseDiagnostic` without crashing
- [x] Dedicated test suite in `tests/test_typescript_parser.py` (13 passing tests)
- [x] All quality checks pass (`uv sync`, `ruff check`, `ruff format --check`, `mypy backend/ code-analyzer/`, `pytest tests/`)

---

### TASK-2E: Canonical Code IR Definition

**Status:** ✅ Done  
**Blockers:** TASK-2D ✅  
**Scope:** Design and implement language-independent, strongly typed, deterministic, and serializable Canonical Code IR models.

**Acceptance criteria:**
- [x] Package structure `code_analyzer/ir/` (`enums.py`, `location.py`, `types.py`, `identity.py`, `entities.py`, `__init__.py`)
- [x] Strongly typed Pydantic frozen models for all 10 core entities (`Repository`, `File`, `Module`, `Class`, `Interface`, `Function`, `Method`, `Variable`, `Parameter`, `Reference`, `Symbol`)
- [x] Strongly typed `EntityKind`, `ReferenceKind`, and `Visibility` enums
- [x] Deterministic entity identity generator (`generate_entity_id`) using UUID v5 and logical key components
- [x] Canonical source location model (`SourceLocation`) with 1-indexed line and 0-indexed column range validation
- [x] Lightweight type representation model (`TypeRepresentation`)
- [x] Full JSON round-trip serialization and deserialization support
- [x] Dedicated unit test suite `tests/test_code_ir.py` (17 passing tests)
- [x] All quality checks pass (`uv sync`, `ruff check`, `ruff format --check`, `mypy backend/ code-analyzer/`, `pytest tests/`)

---

### TASK-2F: AST → Code IR Normalization

**Status:** ✅ Done  
**Blockers:** TASK-2E ✅  
**Scope:** Implement language-specific normalizers translating Java, Python, and TypeScript AST models into language-independent Canonical Code IR.

**Acceptance criteria:**
- [x] Concrete normalizer classes for Java (`JavaNormalizer`), Python (`PythonNormalizer`), and TypeScript (`TypeScriptNormalizer`) implementing abstract `ASTNormalizer` base class
- [x] Unified normalization entry point `normalize_parse_result(parse_result, repository_id, ...)`
- [x] Mapping language-specific AST structures to canonical entities (`File`, `Module`, `Class`, `Interface`, `Function`, `Method`, `Variable`, `Parameter`, `Reference`, `Symbol`)
- [x] Generic type representation parser (`parse_type_representation`) converting generic type annotations into `TypeRepresentation`
- [x] Location helper (`to_ir_source_location`) mapping parser line/column positions to IR `SourceLocation`
- [x] Deterministic identity generation via `generate_entity_id` across all entities and references
- [x] Hierarchical containment without language-specific model leakage
- [x] Dedicated unit test suite `tests/test_normalization.py` (13 passing tests)
- [x] All quality checks pass (`uv sync`, `ruff check`, `ruff format --check`, `pytest tests/`)

---

### TASK-2G: Parser / Canonical IR Testing & Hardening

**Status:** ✅ Done  
**Blockers:** TASK-2F ✅  
**Scope:** Thoroughly test and harden the complete multi-language parsing and normalization pipeline across Java, Python, and TypeScript.

**Acceptance criteria:**
- [x] End-to-end integration tests for Java, Python, and TypeScript pipelines in `tests/test_phase2_integration.py`
- [x] Cross-language entity consistency verified (`EntityKind.CLASS`, `EntityKind.METHOD`, `EntityKind.FUNCTION`)
- [x] Language leakage protection verified (no Tree-sitter nodes or language ASTs exposed)
- [x] Deterministic identity stability & sensitivity verified across runs, names, file paths, and kinds
- [x] Normalization idempotency verified
- [x] Source location line/column correctness verified
- [x] Generic type representation normalization verified across Java, Python, and TypeScript
- [x] Malformed source fault tolerance & parser diagnostic preservation verified
- [x] Empty file and comment-only file handling verified
- [x] Multiple declarations, nested structures, and duplicate name scoping verified
- [x] Lossless JSON round-trip serialization (`model_dump_json()` / `model_validate_json()`) verified
- [x] Immutability of frozen Pydantic IR entities verified
- [x] Public API exports verified (`code_analyzer.parsers`, `code_analyzer.ir`, `code_analyzer.normalization`)
- [x] In-memory execution without filesystem or external server dependency verified
- [x] Performance sanity check verified (< 2s for 500-line source)
- [x] Full regression suite passing (124 tests passed)
- [x] All quality gates pass (`uv sync`, `ruff check .`, `ruff format --check .`, `mypy backend/ code-analyzer/`, `pytest tests/`)

**PHASE 2 IS NOW OFFICIALLY COMPLETE.**

---

## Phase 3 — Symbol Resolution & Code Knowledge Graph

### TASK-3A: Code Graph Schema & Models

**Status:** ✅ Done  
**Blockers:** Phase 2 ✅  
**Scope:** Establish the foundational data model and contracts for the Code Knowledge Graph derived from Canonical Code IR.

**Acceptance criteria:**
- [x] Package structure `graph/` (`enums.py`, `nodes.py`, `edges.py`, `models.py`, `contracts.py`, `__init__.py`, `py.typed`)
- [x] Strongly typed `NodeKind`, `EdgeKind`, and `ResolutionStatus` enums
- [x] Immutable, frozen `GraphNode` model with factory method `GraphNode.from_ir_entity` converting Canonical Code IR entities
- [x] Deterministic edge identity generator `generate_edge_id` using UUID v5 and edge attributes
- [x] Immutable, frozen `GraphEdge` model with factory method `GraphEdge.from_ir_reference` converting IR references into graph edges
- [x] `CodeGraph` container model supporting graph manipulation, neighbor retrieval, inbound/outbound edge lookups, and lossless JSON serialization
- [x] Abstract contracts defined in `contracts.py` for symbol registration (`SymbolRegistrarContract`), import resolution (`ImportResolverContract`), reference resolution (`ReferenceResolverContract`), relationship extraction (`RelationshipExtractorContract`), graph construction (`GraphBuilderContract`), graph persistence (`GraphStoreContract`), and query analysis (`GraphQueryEngineContract`)
- [x] Dedicated unit test suite in `tests/test_code_graph_schema.py` (12 passing tests)
- [x] All quality gates pass (`uv sync`, `ruff check .`, `ruff format --check .`, `mypy backend code-analyzer/code_analyzer graph`, `pytest tests/`)

### TASK-3B/3C: Symbol, Import & Reference Resolution

**Status:** ✅ Done  
**Blockers:** TASK-3A ✅  
**Scope:** Implement deterministic symbol registration, language-specific import resolution, and reference resolution for Java, Python, and TypeScript.

**Acceptance criteria:**
- [x] Created `code_analyzer.resolution` package (`symbol_table.py`, `import_resolver.py`, `reference_resolver.py`, `context.py`, `result.py`, `__init__.py`, `py.typed`)
- [x] In-memory `SymbolTable` with deterministic lookups by ID, qualified name, scope, simple name, and suffix; enforced repository isolation
- [x] Language-aware `ImportResolver` supporting Java (direct, wildcard, external stdlib), Python (from-import, module, aliases), and TypeScript (named, relative paths, external specifiers)
- [x] Deterministic `ReferenceResolver` with strict resolution precedence (exact QName → import alias → method on type → scope simple name → file simple name → repo simple name → suffix fallback), returning `RESOLVED`, `UNRESOLVED`, `AMBIGUOUS`, `EXTERNAL`, or `BUILTIN` without guessing
- [x] Multi-file end-to-end integration tests for Java, Python, and TypeScript
- [x] Dedicated unit test suite in `tests/test_resolution.py` (49 tests) bringing full test suite to 181 passing tests (4 skipped)
- [x] All quality gates pass (`uv sync`, `ruff check .`, `ruff format --check .`, `mypy backend code-analyzer/code_analyzer graph`, `pytest tests/`)

### TASK-3D: Relationship Extraction

**Status:** ✅ Done  
**Blockers:** TASK-3B/3C ✅  
**Scope:** Implement semantic relationship extraction engine mapping Canonical IR entities and resolved references to directed Code Knowledge Graph relationships.

**Acceptance criteria:**
- [x] Created `code_analyzer.resolution.relationship_extractor.RelationshipExtractor` implementing `RelationshipExtractorContract`
- [x] Structural `DECLARES` edge generation mapping parent-child entity ownership (File → Class, Class → Method, Method → Parameter, etc.)
- [x] Signature type `USES` edge generation for variable declared types, function return types, and parameter types matched against `SymbolTable`
- [x] Semantic `ReferenceKind` mapping to directed graph edges (`CALLS`, `IMPORTS`, `EXTENDS`, `IMPLEMENTS`, `USES`, `OVERRIDES`, `READS`, `REFERENCES`)
- [x] Strict resolution filtering: `UNRESOLVED`, `AMBIGUOUS`, `BUILTIN`, and `EXTERNAL` references produce zero repository-local graph edges
- [x] Deterministic identity generation via `generate_edge_id` (UUID v5) guaranteeing idempotency and deduplication
- [x] Multi-file language integration tests for Java, Python, and TypeScript
- [x] End-to-end `CodeGraph` container pipeline assembly and JSON roundtrip serialization
- [x] Dedicated test suite in `tests/test_relationship_extractor.py` (16 passing tests)
- [x] All quality gates pass (`uv run ruff check .`, `uv run mypy code-analyzer graph`, `uv run pytest tests/` (201 passed))

### TASK-3E/3F: Graph Storage Engine & Traversal Query Engine

**Status:** ✅ Done  
**Blockers:** TASK-3D ✅  
**Scope:** Implement production-grade in-memory graph storage and deterministic BFS traversal query engine for callers/callees/dependency/dependent analysis.

**Acceptance criteria:**
- [x] Created `InMemoryGraphStore` in `graph/store.py` implementing `GraphStoreContract` with $O(1)$ adjacency indexing (`outbound_index`, `inbound_index`, and kind-filtered indices)
- [x] Enforced graph consistency checks, idempotent entity re-insertion, conflict detection, cascading node removal, and async snapshot persistence (`save_graph`, `load_graph`, `delete_graph`)
- [x] Created `GraphQueryEngine` in `graph/query_engine.py` implementing `GraphQueryEngineContract` for deterministic, language-independent graph traversal
- [x] Implemented direct callers (`get_callers`), direct callees (`get_callees`), dependency closure (`get_dependencies`), dependent closure (`get_dependents`), and reverse impact radius (`get_impact_radius`) queries
- [x] Implemented `DEPENDENCY_EDGE_KINDS` edge-kind policy filtering out structural containment edges (`DECLARES`, `CONTAINS`, `EXPORTS`) from dependency analysis by default
- [x] BFS traversal with cycle prevention (`visited` set and `queue`) and depth limiting (`max_depth`)
- [x] Deterministic node sorting key `(node.kind.value, node.qualified_name, node.id)`
- [x] Dedicated unit and integration test suites in `tests/test_graph_store.py` (22 tests) and `tests/test_graph_traversal.py` (10 tests) including 1,000-node synthetic benchmark tests and full end-to-end pipeline verification
- [x] All quality gates pass (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy graph tests`, `uv run pytest` (224 passed))

### TASK-3G: Code Knowledge Graph Testing & Hardening

**Status:** ✅ Done  
**Blockers:** TASK-3E/3F ✅  
**Scope:** Aggregate, harden, and stress test the entire Phase 3 Code Knowledge Graph pipeline.

**Acceptance criteria:**
- [x] Created `tests/test_graph_hardening.py` covering 11 critical categories of graph invariants
- [x] Verified schema immutability, ID constraints, and JSON round-tripping
- [x] Validated false-positive and false-negative prevention in symbol resolution and alias handling
- [x] Enforced storage engine invariants: O(1) indexing, cascading removal, and duplicate/conflict detection
- [x] Validated traversal safety: directionality, cycle safety, depth-limited traversals, and self-loop handling
- [x] Confirmed sub-second traversal scalability across synthetic 5,000-node adversarial topologies (large fan-in/fan-out star graphs)
- [x] Validated end-to-end multi-file, cross-language pipeline integrity
- [x] All quality gates pass (`uv run ruff check .`, `uv run mypy .`, `uv run pytest` (239 passed))

### TASK-3H: Initial Impact Analysis

**Status:** ✅ Done  
**Blockers:** TASK-3G ✅  
**Scope:** Implement production-grade impact analysis capability calculating direct/transitive impact radii and structured explanation paths.

**Acceptance criteria:**
- [x] Defined `ImpactAnalyzerContract` in `graph/contracts.py` and exported public API in `graph/__init__.py`
- [x] Implemented `ImpactAnalyzer` in `graph/impact_analyzer.py` executing deterministic reverse dependency BFS traversal
- [x] Created structured Pydantic models: `ImpactAnalysisResult`, `ImpactedNode`, `ImpactPath`, and `ImpactPathStep` with immutability (`frozen=True`) and lossless JSON serialization
- [x] Supported direct vs transitive impact categorization, minimum-depth calculation (`minimum_depth`), path step edge direction preservation, self-loop exclusion, cycle safety, and custom/default edge kind filtering (`DEPENDENCY_EDGE_KINDS`)
- [x] Built comprehensive test suite `tests/test_impact_analysis.py` covering all 32 required categories: depth limits (0, 1, 2, None), minimum depth shortest-path calculation, path step directionality, structural edge exclusion, missing root KeyError handling, multi-language E2E pipelines (Java, Python, TypeScript), large fan-in (500 callers), 5,000 synthetic node performance, and adversarial topology correctness
- [x] All quality gates pass (`uv run ruff check .`, `uv run mypy .`, `uv run pytest` (251 passed))

### TASK-4A: AST/IR-Aware Code Chunking

**Status:** ✅ Done  
**Blockers:** Phase 3 ✅  
**Scope:** Implement language-independent AST/IR-aware code chunking engine transforming Canonical Code IR (`NormalizationResult`) into deterministic, semantically structured `CodeChunk` models.

**Acceptance criteria:**
- [x] Package structure `retrieval/` created with `enums.py`, `models.py`, `identity.py`, `contracts.py`, `chunker.py`, `__init__.py`, `py.typed`
- [x] Created `CodeChunker` in `retrieval/chunker.py` implementing `CodeChunkerContract` in `retrieval/contracts.py`
- [x] Defined structured immutable models `CodeChunk` and `CodeChunkCollection` with field validation and lookup indices
- [x] Created `generate_chunk_id` in `retrieval/identity.py` generating deterministic UUID v5 chunk IDs based on stable semantic seed keys (`repo|file|type|entity|loc|sub_index`)
- [x] Semantic chunk hierarchy implemented: `FILE_CONTEXT`, `CLASS_CONTEXT`, `INTERFACE_CONTEXT`, `FUNCTION`, `METHOD`, `SUB_CHUNK`
- [x] Preserved semantic context (`parent_entity_id`, `parent_chunk_id`, doc comments, signatures, metadata) without duplicating full file content in child chunks
- [x] Oversized entity fallback policy: entities exceeding `max_lines_per_chunk` split into primary header chunk (`sub_chunk_index=0`) and line-range sub-chunks (`ChunkType.SUB_CHUNK`, `sub_chunk_index=1..N`) preserving parent entity identity and source order
- [x] Preserved exact source ranges (`start_line`, `start_column`, `end_line`, `end_column`) from Canonical IR `SourceLocation`
- [x] Implemented deterministic source ordering (`FILE_CONTEXT` priority -> `start_line` -> `start_column` -> `chunk_type` -> `entity_id` -> `sub_chunk_index`)
- [x] Duplicate prevention via `(entity_id, chunk_type, sub_chunk_index)` deduplication tracking
- [x] Canonical IR immutability and graph separation maintained (no IR mutation, no graph edges added)
- [x] Added comprehensive test suite `tests/test_chunking.py` covering all 28 required test categories and validation scenarios across Java, Python, and TypeScript fixtures, empty files, nested symbols, duplicate prevention, synthetic scale (1,000 entities in <1s), IR immutability, and graph separation
- [x] All quality gates pass (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest tests/` (276 passed))

### TASK-4B: Code Chunk Metadata Enrichment

**Status:** ✅ Done  
**Blockers:** TASK-4A ✅  
**Scope:** Harden and complete the metadata layer surrounding the AST/IR-aware `CodeChunk` implementation to support embedding vector storage, BM25 indexing, hybrid retrieval, source citations, filtering, revision tracking, and incremental indexing.

**Acceptance criteria:**
- [x] Extended `CodeChunk` and `CodeChunkCollection` models to include optional `commit_id` and `commit_sha` fields for version revision tracking
- [x] Added convenience property aliases `symbol_name` (alias for `name`) and `symbol_id` (alias for `entity_id`) to support indexing consumers
- [x] Implemented `to_index_dict()` method on `CodeChunk` providing complete, normalized metadata payloads for downstream vector embedding (4C) and BM25 indexing (4D) without duplicating Canonical IR
- [x] Added robust field validators for core identity strings, forward-slash file path normalization, valid line ranges, sub-chunk index bounds, and sub-chunk parent linkages
- [x] Updated `CodeChunkerContract` and `CodeChunker` builder methods to propagate revision metadata (`commit_id` and `commit_sha`)
- [x] Maintained strict model immutability (`frozen=True`) and determinism without modifying Canonical IR models or coupling to indexing engines
- [x] Built comprehensive test suite `tests/test_chunk_metadata.py` covering repository/commit tracking, path normalization, property aliases, parent hierarchy linkages, sub-chunk metadata, validation rules, immutability, determinism, and index consumer readiness
- [x] All quality gates pass (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest tests/` (287 passed))

### TASK-4C: Dense Vector Embedding Infrastructure

**Status:** ✅ Done  
**Blockers:** TASK-4B ✅  
**Scope:** Implement provider-agnostic, batch-aware, deterministic embedding pipeline transforming `CodeChunk` representations into dense vector embeddings.

**Acceptance criteria:**
- [x] Defined provider contract `EmbeddingProviderContract` in `retrieval/contracts.py`
- [x] Implemented immutable Pydantic models `EmbeddingInput`, `EmbeddingResult`, `EmbeddingFailure`, and `EmbeddingBatchResult` in `retrieval/embedding_models.py`
- [x] Implemented `EmbeddingTextBuilder` in `retrieval/text_builder.py` prioritizing source code while incorporating language, symbol name, signature, parent context, and doc comment headers with empty source fallback
- [x] Implemented `DeterministicTestEmbeddingProvider` in `retrieval/providers.py` using SHA-256 digest hashing to produce deterministic, normalized vectors without network or GPU dependencies
- [x] Implemented `HostedAPIEmbeddingProvider` in `retrieval/providers.py` using `httpx` for optional external API embedding integration
- [x] Implemented `EmbeddingPipeline` in `retrieval/embedding_pipeline.py` executing batch boundary slicing, duplicate chunk ID detection, retry policies for transient errors, and vector dimension verification
- [x] Enforced vector dimension and numeric sanity validation (no NaN/Inf)
- [x] Built comprehensive unit test suite `tests/test_embedding_pipeline.py` covering text builder formatting, deterministic provider output, batch processing, duplicate ID rejection, fault injection retries, cross-language parity (Java, Python, TypeScript), performance batch ratio verification, and IR/chunk immutability
- [x] All quality gates pass (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest tests/` (304 passed))

### TASK-4D: Code-Aware Lexical Indexing (BM25)

**Status:** ✅ Done  
**Blockers:** TASK-4B ✅  
**Scope:** Implement production-quality, code-aware lexical retrieval index based on BM25 algorithm independent of vector and graph retrieval pipelines.

**Acceptance criteria:**
- [x] Defined `LexicalIndexContract` in `retrieval/contracts.py` specifying `add`, `add_many`, `remove`, `clear`, `search`, and `document_count`
- [x] Implemented immutable Pydantic models `LexicalDocument`, `LexicalSearchResult`, and `LexicalSearchResultSet` in `retrieval/lexical_models.py`
- [x] Implemented `CodeTokenizer` in `retrieval/tokenizer.py` supporting code-aware decomposition (camelCase, PascalCase, snake_case, SCREAMING_SNAKE_CASE, acronyms, qualified names, file paths) while preserving exact case-folded original identifiers and code keywords
- [x] Implemented `LexicalTextBuilder` in `retrieval/lexical_text_builder.py` with explicit field weighting (symbol name 3.0x, qualified name 3.0x, file path 2.0x, signature 2.0x, doc comments 1.5x, content 1.0x)
- [x] Implemented `BM25LexicalIndex` and `RepositoryBM25Index` in `retrieval/lexical_index.py` with Robertson-Spärck Jones BM25 algorithm ($k_1=1.5, b=0.75$), IDF smoothing, strict repository isolation, and deterministic tie-breaking (score DESC, chunk_id ASC)
- [x] Implemented custom exception hierarchy in `retrieval/exceptions.py` (`RetrievalError`, `LexicalIndexError`, `LexicalConfigurationError`, `LexicalDocumentError`, `LexicalQueryError`)
- [x] Built comprehensive unit test suite `tests/test_lexical_index.py` covering tokenization, exact identifier matching, field weighting, repository isolation, index lifecycle (add/remove/clear/replacement), edge cases, BM25 math properties, cross-language parity (Java, Python, TypeScript), scale performance, and immutability
- [x] All quality gates pass (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest tests/` (331 passed))

### TASK-4E: Index Testing & Hardening

**Status:** ✅ Done  
**Blockers:** TASK-4A ✅, TASK-4B ✅, TASK-4C ✅, TASK-4D ✅  
**Scope:** Final integration testing, correctness validation, determinism verification, regression testing, and hardening of the entire Phase 4 retrieval and indexing foundation.

**Acceptance criteria:**
- [x] Implemented end-to-end integration test suite `tests/test_indexing_hardening.py` connecting Canonical IR -> `CodeChunker` -> `CodeChunkCollection` -> `EmbeddingPipeline` & `BM25LexicalIndex`
- [x] Verified chunk identity determinism (UUID v5), identity input sensitivity, metadata propagation, and forward-slash path normalization across all 3 MVP languages (Java, Python, TypeScript)
- [x] Verified sub-chunk parent-child indexing linkage and granularity hierarchy (`FILE_CONTEXT`, `CLASS_CONTEXT`, `INTERFACE_CONTEXT`, `FUNCTION`, `METHOD`, `SUB_CHUNK`)
- [x] Amplified symbol name field weight to 10.0x in `LexicalTextBuilder` to guarantee exact symbol matches rank #1 over long body term repetition (adversarial test passed)
- [x] Verified cross-layer immutability (Pydantic `frozen=True`) with deep-copy snapshot equality checks before and after indexing
- [x] Verified BM25 mathematical properties (rare vs common terms, TF saturation, doc length normalization, multiple query terms, zero-result handling)
- [x] Verified strict repository isolation, insertion-order independent search results (rebuild equivalence), deterministic tie-breaking (score DESC, `chunk_id` ASC), and referential integrity
- [x] Verified performance scale on 1,000+ chunks, batch call reduction ($\lceil N / B \rceil$), and exception failure injection
- [x] All quality gates pass (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest tests/` (340 passed))

### TASK-5A: Query Preprocessing

**Status:** ✅ Done  
**Blockers:** TASK-4E ✅  
**Scope:** Implement query normalization, identifier extraction, qualified name detection, and language-neutral classification engine.

**Acceptance criteria:**
- [x] Defined `QueryKind` enum and immutable `ProcessedQuery` Pydantic model (`frozen=True`) in `retrieval/query_models.py`
- [x] Implemented `QueryPreprocessor` in `retrieval/query_processor.py` supporting unicode NFC normalization, whitespace collapsing, casing preservation, identifier extraction (camelCase, PascalCase, snake_case, acronyms), qualified name candidates, path structure detection, and deterministic `QueryKind` classification (`IDENTIFIER`, `QUALIFIED_IDENTIFIER`, `PATH_OR_FILE`, `RELATIONSHIP`, `NATURAL_LANGUAGE`, `MIXED`, `UNKNOWN`)
- [x] Added empty/whitespace query validation raising `LexicalQueryError`
- [x] Built comprehensive unit test suite `tests/test_query_preprocessing.py` validating normalization, matrix query classification, immutability, and JSON serialization
- [x] All quality gates pass (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest tests/`)

### TASK-5B: BM25 / Lexical Retrieval

**Status:** ✅ Done  
**Blockers:** TASK-5A ✅  
**Scope:** Implement Phase 5 BM25 Lexical Retrieval Service (`LexicalRetriever`) orchestrating query preprocessing, repository isolation, metadata filtering, and candidate ranking.

**Acceptance criteria:**
- [x] Defined `LexicalRetrieverContract` interface in `retrieval/contracts.py`
- [x] Implemented immutable `LexicalRetrievalRequest`, `RetrievalResult`, and `RetrievalResultSet` models in `retrieval/retrieval_models.py`
- [x] Updated `BM25LexicalIndex` and `RepositoryBM25Index` in `retrieval/lexical_index.py` with support for optional `file_path` and `commit_sha` filtering and full metadata preservation (`qualified_name`, `start_line`, `end_line`, `metadata`)
- [x] Implemented `LexicalRetriever` service in `retrieval/lexical_retriever.py` orchestrating query preprocessing, repository isolation boundary checks, BM25 index search, and candidate result ranking
- [x] Built comprehensive unit & integration test suite `tests/test_lexical_retriever.py` verifying end-to-end flow, strict cross-repository isolation (Repo A vs Repo B), adversarial symbol field-weighting advantage (symbol name matches beat content term repetition), metadata preservation, zero-result handling, invalid input validation, scale performance (1,000+ chunks sub-second execution), index immutability, and JSON serialization
- [x] All quality gates pass (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest tests/` (376 passed))

## Notes for AI Agents

- Each task above is independently implementable; do not merge tasks.
- "Acceptance criteria" is the definition of done; do not mark a task complete
  unless all criteria are met.
- After completing a task: update `CURRENT_STATE.md`, `CHANGELOG.md`,
  and this file.

