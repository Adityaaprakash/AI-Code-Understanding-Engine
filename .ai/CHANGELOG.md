# Changelog — AI Code Understanding Engine

All notable changes to this project are recorded here.
Format: `[Date] — Phase X — Summary`

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
