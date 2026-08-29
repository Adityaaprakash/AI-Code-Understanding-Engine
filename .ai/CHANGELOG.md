# Changelog — AI Code Understanding Engine

All notable changes to this project are recorded here.
## 2026-08-29 — Phase 3A — Code Graph Schema & Models

**Completed by:** TASK-3A

### Added
- Package `graph` providing language-independent Code Knowledge Graph data models, edge identity generation, graph container, and abstract Phase 3 component contracts.
- Enumerations in `graph/enums.py`: `NodeKind`, `EdgeKind`, and `ResolutionStatus`.
- Graph node model in `graph/nodes.py`: `GraphNode` (immutable, frozen Pydantic model) with factory method `GraphNode.from_ir_entity` deriving graph nodes directly from Phase 2 Canonical Code IR entities (`Class`, `Function`, `Method`, `Variable`, `File`, `Module`, `Repository`, `Interface`, `Parameter`, `Symbol`).
- Edge identity generator in `graph/edges.py`: `generate_edge_id` using UUID v5 and seed key format.
- Graph edge model in `graph/edges.py`: `GraphEdge` (immutable, frozen Pydantic model) with factory method `GraphEdge.from_ir_reference` mapping Canonical IR references into directed graph edges.
- Code graph container model in `graph/models.py`: `CodeGraph` supporting graph storage, inbound/outbound edge queries, neighbor retrieval (`get_neighbors`), node/edge lookups, and lossless JSON serialization.
- Phase 3 component contracts in `graph/contracts.py`: `SymbolRegistrarContract`, `ImportResolverContract`, `ReferenceResolverContract`, `RelationshipExtractorContract`, `GraphBuilderContract`, `GraphStoreContract`, `GraphQueryEngineContract`, `DependencyAnalyzerContract`, and `ImpactAnalyzerContract`.
- Package exports in `graph/__init__.py` and PEP 561 typed package marker `graph/py.typed`.
- Unit test suite `tests/test_code_graph_schema.py` (12 test cases covering node kinds, edge kinds, resolution statuses, graph node validation and immutability, IR entity derivation, edge identity determinism, graph edge validation, IR reference derivation, graph container operations, JSON serialization roundtrip, abstract contracts enforcement, and end-to-end IR topology derivation).

### Verification
- `uv sync` ✅
- `uv run ruff check .` ✅
- `uv run ruff format --check .` ✅
- `uv run mypy backend code-analyzer/code_analyzer graph` ✅
- `uv run pytest tests/ -v` ✅ (136 passed)

---

## 2026-08-28 — Phase 2G — Parser / Canonical IR Testing & Hardening (Phase 2 Complete)

**Completed by:** TASK-2G

### Added
- Phase 2 end-to-end integration and hardening test suite `tests/test_phase2_integration.py` (24 test cases).
- Multi-language end-to-end pipeline verification (Java, Python, TypeScript source → parser → AST → normalizer → Canonical IR).
- Cross-language entity consistency tests ensuring `EntityKind.CLASS`, `EntityKind.METHOD`, and `EntityKind.FUNCTION` map identically across languages.
- AST language leakage prevention tests verifying no Tree-sitter nodes or language-specific AST models leak into canonical entities.
- Deterministic ID stability and sensitivity verification across runs, entity names, file paths, and entity kinds.
- Idempotency verification confirming multi-pass normalization returns identical structures.
- Source location range correctness tests across multi-line classes, functions, methods, parameters, and nested declarations.
- Generic type representation normalization tests for Java `List<String>`, Python `list[str]`, and TypeScript `Promise<User>`.
- Malformed source fault tolerance & diagnostic preservation tests.
- Empty source (`""`) and comment-only source file handling.
- Multiple top-level declarations, nested declaration hierarchy, and duplicate name scoping tests.
- Lossless JSON round-trip serialization/deserialization tests using `model_dump_json()` and `model_validate_json()`.
- Immutability enforcement tests for frozen Pydantic IR entities.
- Public API export verification for `code_analyzer.parsers`, `code_analyzer.ir`, and `code_analyzer.normalization`.
- In-memory execution verification (no filesystem, Postgres, or server coupling required).
- Performance sanity check verifying 500-line source file normalizes in under 2 seconds.

### Verification
- `uv sync` ✅
- `uv run ruff check .` ✅
- `uv run ruff format --check .` ✅
- `uv run mypy backend/ code-analyzer/` ✅
- `uv run pytest tests/ -v` ✅ (120 passed, 4 skipped)

**PHASE 2 (INGESTION, AST & CANONICAL CODE IR) IS OFFICIALLY COMPLETE.**

---

## 2026-08-28 — Phase 2F — AST → Code IR Normalization

**Completed by:** TASK-2F

### Added
- Normalization boundary package `code_analyzer.normalization` translating language-specific AST models into language-independent Canonical Code IR.
- Abstract base class `ASTNormalizer[T]` in `code-analyzer/code_analyzer/normalization/base.py`.
- Concrete language normalizers:
  - `JavaNormalizer` in `code-analyzer/code_analyzer/normalization/java.py` (Java package → Module, class/interface → Class/Interface, method → Method, field → Variable, extends/implements → Reference).
  - `PythonNormalizer` in `code-analyzer/code_analyzer/normalization/python.py` (file path → Module, function → Function/Method, class → Class, bases → Reference, async/decorators preserved).
  - `TypeScriptNormalizer` in `code-analyzer/code_analyzer/normalization/typescript.py` (file path → Module, class/interface → Class/Interface, type alias → Variable/Symbol, exports/generics preserved).
- Unified normalization entry point `normalize_parse_result(parse_result, repository_id, ...)` in `code-analyzer/code_analyzer/normalization/__init__.py`.
- Result container model `NormalizationResult` in `code-analyzer/code_analyzer/normalization/result.py`.
- Type representation helper `parse_type_representation` in `code-analyzer/code_analyzer/normalization/type_helper.py` parsing generic type strings (`List<String>`, `list[str]`, `Promise<User>`) recursively.
- Location helper `to_ir_source_location` in `code-analyzer/code_analyzer/normalization/location_helper.py`.
- Comprehensive unit test suite `tests/test_normalization.py` (13 test cases covering Java, Python, TypeScript, cross-language consistency, AST isolation, and idempotency).

### Verification
- `uv sync` ✅
- `uv run ruff check code-analyzer tests` ✅
- `uv run ruff format --check code-analyzer tests` ✅
- `uv run pytest` ✅ (100 passed)

---

## 2026-08-28 — Phase 2E — Canonical Code IR

**Completed by:** TASK-2E

### Added
- Package `code_analyzer.ir` providing language-independent, strongly typed, deterministic, and serializable Canonical Code IR models.
- Enumeration models in `code_analyzer/code_analyzer/ir/enums.py`: `EntityKind`, `ReferenceKind`, and `Visibility`.
- Source location model in `code_analyzer/code_analyzer/ir/location.py`: `SourceLocation` with 1-indexed lines and 0-indexed columns validation.
- Type representation model in `code_analyzer/code_analyzer/ir/types.py`: `TypeRepresentation`.
- Deterministic identity strategy in `code-analyzer/code_analyzer/ir/identity.py`: `generate_entity_id` using UUID v5 and seed keys.
- Core IR entity models in `code-analyzer/code_analyzer/ir/entities.py`: `IREntity`, `Repository`, `File`, `Module`, `Class`, `Interface`, `Function`, `Method`, `Variable`, `Parameter`, `Reference`, `Symbol`.
- Package exports in `code-analyzer/code_analyzer/ir/__init__.py`.
- Unit test suite `tests/test_code_ir.py` (17 test cases covering entity kinds, reference kinds, source locations, repositories, files, modules, classes, interfaces, functions, methods, variables, parameters, references, deterministic identity, JSON round-trip serialization, language neutrality, and containment hierarchy).

### Verification
- `uv sync` ✅
- `uv run ruff check .` ✅
- `uv run ruff format --check .` ✅
- `uv run mypy backend/ code-analyzer/` ✅
- `uv run pytest tests/ -v` ✅ (83 passed, 4 skipped)

---

## 2026-08-27 — Phase 2C & 2D — Python AST & TypeScript AST Parsers

**Completed by:** TASK-2C & TASK-2D

### Added
- Dependency `tree-sitter-python>=0.21.0` and `tree-sitter-typescript>=0.21.0` to `pyproject.toml`.
- Strongly typed Python AST models and AST extraction walker in `code-analyzer/code_analyzer/parsers/python_ast.py` (`PythonModule`, `PythonClass`, `PythonFunction`, `PythonField`, `PythonImport`, `PythonDecorator`, `PythonParameter`, `SourceLocation`).
- Concrete `PythonParser` in `code-analyzer/code_analyzer/parsers/python.py` implementing `LanguageParser` interface for Python source code.
- Strongly typed TypeScript AST models and AST extraction walker in `code-analyzer/code_analyzer/parsers/typescript_ast.py` (`TypeScriptStructure`, `TypeScriptClass`, `TypeScriptInterface`, `TypeScriptFunction`, `TypeScriptField`, `TypeScriptImport`, `TypeScriptExport`, `TypeScriptType`, `TypeScriptParameter`, `SourceLocation`).
- Concrete `TypeScriptParser` in `code-analyzer/code_analyzer/parsers/typescript.py` implementing `LanguageParser` interface for TypeScript source code.
- Package exports in `code-analyzer/code_analyzer/parsers/__init__.py` for Python and TypeScript models and parsers.
- Unit test suite `tests/test_python_parser.py` (12 test cases covering module functions, classes, methods, async functions, imports, import aliases, decorators, decorated classes, nested declarations, syntax failures, source locations).
- Unit test suite `tests/test_typescript_parser.py` (13 test cases covering classes, interfaces, functions, async functions, generics, imports, exports, named export aliases, type aliases, nested members, syntax failures, source locations).

### Verification
- `uv sync` ✅
- `uv run ruff check .` ✅
- `uv run ruff format --check .` ✅
- `uv run mypy backend/ code-analyzer/` ✅
- `uv run pytest tests/ -v` ✅ (70 passed, 4 skipped)

---

## 2026-08-25 — Phase 1A — Repository Foundation

**Completed by:** Phase 1A (foundation task)

### Created

**Root files:**
- `.gitignore` — Python/Node/Java polyglot gitignore
- `.env.example` — Full environment variable template for all planned subsystems
- `README.md` — Project overview, architecture diagram, MVP languages, local-first philosophy

**Top-level directories:**
- `backend/`, `frontend/`, `code-analyzer/`, `retrieval/`, `graph/`, `llm/`,
  `evaluation/`, `experiments/`, `docs/`, `docker/`, `tests/`

**`.ai/` project-memory files:**
- `START_HERE.md` — Mandatory AI agent entry point and reading protocol
- `PROJECT_CONTEXT.md` — Goals, scope, non-goals, technology selections
- `AI_INSTRUCTIONS.md` — Behavioural rules for AI agents
- `CURRENT_STATE.md` — Live phase and task tracker
- `ARCHITECTURE.md` — Full system architecture with component map and data flows
- `DECISIONS.md` — 12 locked ADRs (ADR-001 through ADR-012)
- `ROADMAP.md` — 10-phase development roadmap
- `TASKS.md` — Phase 1 task list with granular acceptance criteria
- `CODE_IR.md` — Canonical Code IR contract (11 concepts defined)
- `DATABASE_SCHEMA.md` — Intended initial schema (7 tables with DDL)
- `API_CONTRACTS.md` — Intended REST API contracts (9 endpoints)
- `RETRIEVAL.md` — Hybrid retrieval architecture (BM25 + vector + graph)
- `CHANGELOG.md` — This file

### Architectural Decisions Locked
ADR-001 through ADR-012 (see `DECISIONS.md`).

### Next Task
TASK-1C: Database foundation (Alembic scaffold + initial schema migration)

---

## 2026-08-25 — Phase 1B — Python Runtime Setup

**Completed by:** TASK-1B

### Created

- `pyproject.toml` — PEP 621 project config; runtime deps (fastapi, uvicorn, pydantic,
  pydantic-settings, sqlalchemy[asyncio], asyncpg, alembic, httpx) and dev deps
  (pytest, pytest-asyncio, pytest-cov, ruff, mypy) via `[dependency-groups]`
- `.python-version` — pinned to `3.12`
- `backend/__init__.py` — Python package marker
- `backend/py.typed` — PEP 561 typed-package marker
- `tests/__init__.py` — test package marker
- `tests/test_python_env.py` — 8-test environment smoke suite
- `.venv/` — Python 3.12.14 virtual environment managed by uv (git-ignored)

### Tooling Established

| Tool | Version | Config location |
|---|---|---|
| Python | 3.12.14 | `.python-version`, `pyproject.toml` |
| uv | 0.12.5 | (package manager) |
| ruff | 0.16.4 | `[tool.ruff]` in `pyproject.toml` |
| mypy | 2.3.1 | `[tool.mypy]` in `pyproject.toml` |
| pytest | 9.1.1 | `[tool.pytest.ini_options]` in `pyproject.toml` |

### Checks Executed (all pass)

| Check | Result |
|---|---|
| `uv sync` | Exit 0, 45 packages installed |
| `uv run python --version` | Python 3.12.14 ✅ |
| `uv run ruff check .` | All checks passed (0 errors) ✅ |
| `uv run ruff format --check .` | 17 files already formatted ✅ |
| `uv run mypy backend/` | Success: no issues found ✅ |
| `uv run pytest tests/ -v` | 8 passed in 2.56s ✅ |

### Architectural Decisions Locked
ADR-013: Python 3.12 and uv as package manager (see `DECISIONS.md`).

### Next Task
TASK-1C: Database foundation

---

## 2026-08-25 — Phase 1C — Database Foundation

**Completed by:** TASK-1C

### Created

- `backend/db/` package: `base.py`, `config.py`, `session.py`, `models/`
- SQLAlchemy 2.0 ORM models for all 7 entities (`Repository`, `Commit`, `File`, `Symbol`, `Chunk`, `Job`, `IndexVersion`)
- `alembic/` migration environment with async PostgreSQL driver support (`alembic/env.py`, `alembic.ini`)
- `alembic/versions/0001_initial_schema.py` initial migration DDL with pgvector, pg_trgm extensions, constraints, and indexes
- `docker/docker-compose.dev.yml` minimal PostgreSQL 16 service
- `tests/test_database_metadata.py` metadata verification test suite
- `tests/test_database_migrations.py` real PostgreSQL migration lifecycle test suite

### Tooling & Verification

| Check | Result |
|---|---|
| `uv run ruff check .` | All checks passed (0 errors) ✅ |
| `uv run ruff format --check .` | 34 files already formatted ✅ |
| `uv run mypy backend/` | Success: no issues found ✅ |
| `uv run pytest tests/ -v` | 11 passed (including PostgreSQL migration lifecycle) ✅ |

### Architectural Decisions Locked
ADR-014: SQLAlchemy 2.0 async engine and Alembic migration system.

### Next Task
TASK-1D: FastAPI Foundation

---

## 2026-08-25 — Phase 1D — FastAPI Foundation

**Completed by:** TASK-1D

### Created

- `backend/main.py`: Application factory `create_app()` and module-level `app`
- `backend/core/config.py`: Environment-driven configuration Settings class with CORS origin parser
- `backend/core/errors.py`: Global exception handlers (`AppException`, validation 422, unhandled 500) and error envelope builder
- `backend/schemas/health.py`: `HealthResponse` schema
- `backend/schemas/errors.py`: `ErrorDetail` and `ErrorResponse` schemas
- `backend/api/v1/router.py`: `api_v1_router` foundation registered at `/api/v1`
- `backend/services/__init__.py`: Services layer boundary package marker
- `tests/test_fastapi_app.py`: FastAPI test suite (health, router, OpenAPI, CORS, exception handling, DB dependency boundary)

### Tooling & Verification

| Check | Result |
|---|---|
| `uv run ruff check .` | All checks passed (0 errors) ✅ |
| `uv run ruff format --check .` | 46 files already formatted ✅ |
| `uv run mypy backend/` | Success: no issues found in 17 source files ✅ |
| `uv run pytest tests/ -v` | 19 passed, 1 skipped (migration test skipped offline) ✅ |
| `uvicorn backend.main:app` | Started successfully, served `/health`, `/openapi.json`, `/docs`, `/api/v1` ✅ |

### Architectural Decisions Locked
ADR-015: FastAPI application factory, Pydantic Settings, and standardized error response envelope.

### Next Task
TASK-1E: Test Infrastructure

---

## 2026-08-26 — Phase 1E — Test Infrastructure

**Completed by:** TASK-1E

### Created

- `tests/conftest.py`: Async pytest fixture layer (`app_instance`, `async_client`, `sync_client`, `database_url`, `db_engine`, `db_session`)
- `tests/test_health.py`: Dedicated smoke tests for `/health` endpoint using async and sync clients
- `tests/test_infrastructure.py`: Infrastructure verification test suite testing custom markers, async HTTP execution, and PostgreSQL transactional rollback isolation
- `scripts/ci_check.py`: Local/CI quality gate test script executing ruff, mypy, pytest, and coverage checks

### Modified

- `pyproject.toml`: Configured strict pytest markers (`unit`, `api`, `integration`, `db`) under `[tool.pytest.ini_options]`
- `tests/test_python_env.py`: Decorated with `@pytest.mark.unit`
- `tests/test_database_metadata.py`: Decorated with `@pytest.mark.unit`
- `tests/test_database_migrations.py`: Decorated with `@pytest.mark.db` and `@pytest.mark.integration`
- `tests/test_fastapi_app.py`: Updated to use `sync_client` fixture and decorated with `@pytest.mark.api` and `@pytest.mark.unit`

### Tooling & Verification

| Check | Result |
|---|---|
| `uv run ruff check .` | All checks passed (0 errors) ✅ |
| `uv run ruff format --check .` | 50 files already formatted ✅ |
| `uv run mypy backend/` | Success: no issues found in 17 source files ✅ |
| `uv run pytest tests/ --cov=backend -v` | 27 passed in 7.83s with 92% code coverage ✅ |
| `uv run python scripts/ci_check.py` | All CI quality gates passed ✅ |

### Architectural Decisions Locked
ADR-016: Pytest async fixture architecture with transactional rollback isolation for PostgreSQL integration testing.

### Next Task
TASK-1F: Docker Compose Foundation

---

## 2026-08-26 — Phase 1F — Docker Compose Foundation

**Completed by:** TASK-1F

### Created

- `docker/docker-compose.yml`: Full development Compose file with `postgres`, `backend`, and `worker` services
- `docker/Dockerfile.backend`: Multi-stage-equivalent Dockerfile — `python:3.12-slim` + uv install + `uvicorn backend.main:app`
- `docker/Dockerfile.worker`: Dockerfile — same base image, runs `python -m backend.worker`
- `backend/worker.py`: Async worker process scaffold with graceful SIGINT/SIGTERM shutdown, PostgreSQL connectivity check on startup, no Phase 2 business logic

### Modified

- `docker/docker-compose.dev.yml`: Extended from postgres-only (TASK-1C) to include `backend` and `worker` services with health checks and dependency ordering
- `backend/core/config.py`: Replaced `BeforeValidator`-based CORS parsing with `@field_validator(mode="before")` to properly parse JSON array strings passed via Docker Compose environment variables

### Tooling & Verification

| Check | Result |
|---|---|
| `docker compose config` | Parses successfully ✅ |
| `docker compose up -d --build` | All 3 services built and started ✅ |
| `postgres` container | `healthy` (pg_isready healthcheck, pgvector/pgvector:pg16) ✅ |
| `backend` container | `running healthy` (curl `/health` healthcheck) ✅ |
| `worker` container | `running` (polling loop active) ✅ |
| `GET http://localhost:8000/health` | HTTP 200 `{"status": "ok"}` ✅ |
| pgvector extension | `vector 0.8.6` confirmed via `pg_extension` table ✅ |
| Alembic migrations | `0001_initial_schema (head)` ✅ |
| `uv run ruff check .` | All checks passed (0 errors) ✅ |
| `uv run ruff format --check .` | 51 files already formatted ✅ |
| `uv run mypy backend/` | Success: no issues found in 26 source files ✅ |
| `uv run pytest tests/ -v` | 27 passed in 4.56s ✅ |

### Architectural Decisions Locked
ADR-017: Docker Compose development environment uses `pgvector/pgvector:pg16` image to provide PostgreSQL 16 with pgvector extension. Backend and worker share the same `python:3.12-slim` + uv build pattern. `CORS_ORIGINS` accepts both comma-separated strings and JSON array strings from environment variables.

### Next Task
TASK-1G: Frontend Scaffold (Vite + React + TypeScript)

---

## 2026-08-26 — Phase 1G — Frontend Scaffold

**Completed by:** TASK-1G

### Created

- `frontend/package.json`: Vite + React 18 + TypeScript + ESLint + Prettier project definition
- `frontend/tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`: TypeScript configuration
- `frontend/vite.config.ts`: Vite bundler configuration with React plugin and dev server port 3000
- `frontend/eslint.config.js`: ESLint flat config with `typescript-eslint` and `react-hooks` rules
- `frontend/.prettierrc`: Prettier formatting rules
- `frontend/.env.example`: Environment variable template (`VITE_API_BASE_URL`)
- `frontend/index.html`: Main HTML entry point
- `frontend/src/vite-env.d.ts`: TypeScript module declarations for `ImportMetaEnv` and `ImportMeta`
- `frontend/src/types/index.ts`: Common frontend type interfaces (`HealthResponse`)
- `frontend/src/services/api.ts`: API service client (`fetchHealth()`) connecting to FastAPI backend
- `frontend/src/hooks/useHealthCheck.ts`: Custom hook managing API health state
- `frontend/src/components/Header.tsx`: Header component displaying project identity
- `frontend/src/pages/HomePage.tsx`: Main landing page with system status card
- `frontend/src/App.tsx` & `main.tsx`: React application root shell
- `frontend/src/index.css`: Vanilla CSS design system with custom dark theme, glassmorphism, and status indicators

### Tooling & Verification

| Check | Result |
|---|---|
| `npm run build` | Bundled 31 modules cleanly (0 TS errors) ✅ |
| `npm run lint` | ESLint passed with 0 errors and 0 warnings ✅ |
| `npm run format:check` | All matched files use Prettier code style ✅ |
| Vite dev server (`npm run dev`) | Ready in 373 ms on `http://localhost:3000/` ✅ |
| Backend ruff check | All checks passed (0 errors) ✅ |
| Backend ruff format | 51 files already formatted ✅ |
| Backend mypy check | Success: no issues found in 26 source files ✅ |
| Backend pytest suite | 27 passed in 4.25s (no regressions) ✅ |

### Architectural Decisions Locked
ADR-018: Frontend scaffold established with Vite, React 18, TypeScript, ESLint (flat config), and Prettier. Service layer uses environment-configured `VITE_API_BASE_URL` to interact with FastAPI `/api/v1` backend endpoints.

### Next Task
Phase 2 — Repository Ingestion & Code Analysis (TASK-2A: Repository Ingestion Engine)

---

## 2026-08-26 — Phase 1H — Phase 1 Final Verification

**Completed by:** TASK-1H

### Verified Stack Matrix

| Section | Target | Verification Command | Result |
|---|---|---|---|
| A | Repository Foundation | Directory listing & `.ai/` memory audit | 14 top-level dirs, no debug files ✅ |
| B | Python Runtime | `uv run python --version` | Python 3.12.14 ✅ |
| B | Linting & Formatting | `uv run ruff check .` & `format --check .` | 0 errors, 51 files formatted ✅ |
| B | Type Safety | `uv run mypy backend/` | 0 issues in 26 source files ✅ |
| C | PostgreSQL & Vector | `pgvector/pgvector:pg16` & `SELECT extversion` | PostgreSQL 16.15, `vector 0.8.6` ✅ |
| C | Database Schema | Table count & Alembic migration lifecycle | 7 domain tables, `downgrade base` -> `upgrade head` (0001_initial_schema head) ✅ |
| D | FastAPI Endpoints | `/health`, `/openapi.json`, `/docs`, `/api/v1` | All return HTTP 200 OK ✅ |
| E | Worker Process | `codelens_worker_dev` container | Startup DB connection ok, active polling loop ✅ |
| F | Docker Compose | `docker compose -f docker/docker-compose.yml` | 3 services (`postgres`, `backend`, `worker`) healthy & running ✅ |
| G | Frontend Build & Quality | `npm run build`, `npm run lint`, `npm run format:check` | Built 31 modules, 0 lint errors, 0 format issues ✅ |
| H | Frontend -> Backend | Vite dev server & CORS configuration | Port 3000 -> `Access-Control-Allow-Origin: http://localhost:3000` ✅ |
| I | Test Suite | `uv run pytest tests/ -v` | 27 passed in 3.94s ✅ |
| K | Git Cleanliness | `git status` & `git diff --check` | 0 untracked debug files, workspace clean ✅ |

### Phase 1 Completion Lock
All 8 Phase 1 tasks (1A through 1H) are 100% complete and fully verified. The local-first Docker Compose infrastructure, PostgreSQL pgvector database foundation, FastAPI application factory & routers, background worker process, pytest test isolation framework, and Vite React TypeScript frontend scaffold are operational.

### Next Task
TASK-2A: Parser Abstraction (Phase 2 — Ingestion, AST & Canonical Code IR)

---

## 2026-08-26 — Phase 2A — Parser Abstraction

**Completed by:** TASK-2A

### Created

- `code-analyzer/code_analyzer/parsers/models.py`: Strongly typed `Language` enum (`JAVA`, `PYTHON`, `TYPESCRIPT`), `DiagnosticSeverity` enum, `ParseDiagnostic` model, and `ParseResult` container model.
- `code-analyzer/code_analyzer/parsers/base.py`: `LanguageParser` abstract base class contract defining `language` property and `parse(source_code, source_path)` method.
- `code-analyzer/code_analyzer/parsers/java.py`: `JavaParser` concrete implementation stub for Java files.
- `code-analyzer/code_analyzer/parsers/python.py`: `PythonParser` concrete implementation stub for Python files.
- `code-analyzer/code_analyzer/parsers/typescript.py`: `TypeScriptParser` concrete implementation stub for TypeScript files.
- `code-analyzer/code_analyzer/parsers/__init__.py`: Package exports for parser abstractions.
- `code-analyzer/code_analyzer/__init__.py` & `code-analyzer/code_analyzer/py.typed`: Package marker and PEP 561 type annotation marker.
- `tests/test_parser_abstraction.py`: Focused unit test suite for language representations, contract enforcement, success/failure result models, diagnostics, and parser stubs.

### Modified

- `pyproject.toml`: Included `code-analyzer/code_analyzer` in hatchling wheel build packages target.

### Tooling & Verification

| Check | Result |
|---|---|
| `uv sync` | Resolved & synced `code_analyzer` package cleanly ✅ |
| `uv run ruff check .` | All checks passed (0 errors) ✅ |
| `uv run ruff format --check .` | 59 files already formatted ✅ |
| `uv run mypy backend/ code-analyzer/` | Success: no issues found in 33 source files ✅ |
| `uv run pytest tests/ -v` | 34 passed in 4.38s (27 backend + 7 parser unit tests) ✅ |

### Architectural Decisions
Parser abstraction contract established under `code_analyzer.parsers`. Language AST parsers inherit from `LanguageParser` and produce standardized `ParseResult` objects containing strongly-typed `Language`, AST handle, diagnostics list, and success status.

### Next Task
TASK-2B — Java AST

---

## 2026-08-27 — Phase 2B — Java AST Parser

**Completed by:** TASK-2B

### Created

- `code-analyzer/code_analyzer/parsers/java_ast.py`: Strongly typed Java extraction models (`JavaStructure`, `JavaClass`, `JavaMethod`, `JavaField`, `JavaImport`, `JavaPackage`, `JavaParameter`, `SourceLocation`) and Tree-sitter AST extraction walker.
- `tests/test_java_parser.py`: Dedicated unit test suite covering 11 specific scenarios (basic parsing, package extraction, import extraction, class extraction, interface extraction, method extraction, field extraction, nested declarations, generic declarations, syntax failures, and source locations).

### Modified

- `pyproject.toml`: Added `tree-sitter>=0.22.0` and `tree-sitter-java>=0.21.0` runtime dependencies.
- `code-analyzer/code_analyzer/parsers/java.py`: Implemented concrete `JavaParser` subclassing `LanguageParser` using `tree-sitter-java` and `java_ast.py` extraction walker.
- `code-analyzer/code_analyzer/parsers/__init__.py`: Exported `JavaParser` and Java AST extraction models.

### Tooling & Verification

| Check | Result |
|---|---|
| `uv sync` | Installed `tree-sitter` (0.26.0) & `tree-sitter-java` (0.23.5) cleanly ✅ |
| `uv run ruff check .` | All checks passed (0 errors) ✅ |
| `uv run ruff format --check .` | 61 files already formatted ✅ |
| `uv run mypy backend/ code-analyzer/` | Success: no issues found in 34 source files ✅ |
| `uv run pytest tests/ -v` | 45 passed (27 backend + 7 TASK-2A parser abstraction + 11 TASK-2B Java AST tests) ✅ |

### Architectural Decisions
Tree-sitter Java parser integrated cleanly inside the `code-analyzer` layer. Exposes typed `JavaStructure` objects via `ParseResult.ast`. Error/missing token nodes are gracefully converted into `ParseDiagnostic` entries without throwing raw parser exceptions.

### Next Task
TASK-2C — Python AST

