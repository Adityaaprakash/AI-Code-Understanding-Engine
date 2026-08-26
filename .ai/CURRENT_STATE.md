# Current State — AI Code Understanding Engine

## Active Phase

**Phase 1 — Foundation**

---

## Current Task

TASK-1G (Frontend Scaffold) complete. Phase 1 (Foundation) is 100% complete! Next: Phase 2 — Repository Ingestion & Code Analysis.

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
  - Python 3.12.14 (managed by uv)
  - `pyproject.toml` with all planned runtime and dev dependencies
  - `.python-version` pinned to 3.12
  - Ruff (lint + format), mypy, pytest configured
  - `backend/__init__.py` and `backend/py.typed` created
  - All checks pass: ruff check ✅ ruff format ✅ mypy ✅ pytest (8/8) ✅
- [x] TASK-1C: Database foundation complete
  - Async-first SQLAlchemy 2.0 ORM models for all 7 entities
  - Declarative Base, async engine, and session factory in `backend/db/`
  - Alembic migrations environment initialized with async driver support
  - Initial migration `0001_initial_schema` with pgvector, pg_trgm extensions, constraints, and indexes
  - PostgreSQL dev container configured in `docker/docker-compose.dev.yml`
  - All checks pass: ruff check ✅ ruff format ✅ mypy ✅ pytest (11/11 against PostgreSQL) ✅
- [x] TASK-1D: FastAPI foundation complete
  - Application factory `create_app()` in `backend/main.py`
  - `/health` endpoint returning `{"status": "ok"}`
  - Pydantic Settings layer in `backend/core/config.py` with environment variable driven configuration & CORS origin parsing
  - Standardized error response envelope & handlers (`AppException`, validation HTTP 422, unhandled 500)
  - `api_v1_router` foundation registered under `/api/v1`
  - Database session dependency boundary `get_db_session` wired for FastAPI `Depends()`
  - OpenAPI `/docs`, `/redoc`, `/openapi.json` exposed
  - All checks pass: ruff check ✅ ruff format ✅ mypy ✅ pytest (19 passed, 1 skipped) ✅
- [x] TASK-1E: Test infrastructure complete
  - Reusable pytest fixtures in `tests/conftest.py` (`app_instance`, `async_client`, `sync_client`, `database_url`, `db_engine`, `db_session`)
  - Strict pytest markers registered in `pyproject.toml` (`unit`, `api`, `integration`, `db`)
  - Smoke tests in `tests/test_health.py` and test infrastructure verification in `tests/test_infrastructure.py`
  - Transactional AsyncSession fixture with auto-rollback for 100% test isolation against PostgreSQL
  - Local/CI verification runner `scripts/ci_check.py`
  - All checks pass: ruff check ✅ ruff format ✅ mypy ✅ pytest (27 passed, 92% coverage) ✅
- [x] TASK-1F: Docker Compose Foundation complete
  - `docker/docker-compose.dev.yml` extended with `backend` and `worker` services (was postgres-only)
  - `docker/docker-compose.yml` created as primary Compose file (identical to dev variant)
  - `docker/Dockerfile.backend` — builds FastAPI app using `uv sync`, runs `uvicorn backend.main:app`
  - `docker/Dockerfile.worker` — builds worker process using `uv sync`, runs `python -m backend.worker`
  - `backend/worker.py` — async polling scaffold with graceful shutdown, PostgreSQL connectivity check, no business logic
  - `backend/core/config.py` — CORS_ORIGINS field_validator updated to accept JSON string from env vars
  - PostgreSQL uses `pgvector/pgvector:pg16` image; pgvector 0.8.6 confirmed available
  - All 3 services start via `docker compose up -d` with correct dependency ordering
  - All checks pass: ruff check ✅ ruff format ✅ mypy (26 sources) ✅ pytest (27 passed) ✅
- [x] TASK-1G: Frontend Scaffold complete
  - Vite + React 18 + TypeScript scaffold initialized under `frontend/`
  - ESLint (flat config `eslint.config.js` with react-hooks and typescript-eslint) configured
  - Prettier (`.prettierrc`) configured with `format` and `format:check` scripts
  - Clean directory architecture: `components/`, `pages/`, `services/`, `types/`, `hooks/`
  - App shell with Header component, HomePage, and System Status card displaying live/stub backend status
  - Environment-driven API client boundary (`fetchHealth()` in `src/services/api.ts` using `import.meta.env.VITE_API_BASE_URL`)
  - `vite-env.d.ts` module declarations for `ImportMetaEnv` and `ImportMeta`
  - All checks pass: `npm run build` ✅ `npm run lint` ✅ `npm run format:check` ✅ Vite dev server (port 3000) ✅ Backend regression (27/27 passed) ✅

---

## In Progress

- [ ] Phase 2 — Repository Ingestion & Code Analysis (TASK-2A: Repository Ingestion Engine)

---

## Blocked / Pending

### Phase 1 Remaining
- [x] 1B: Python runtime setup — ✅ Done
- [x] 1C: Database foundation — ✅ Done
- [x] 1D: FastAPI skeleton — ✅ Done
- [x] 1E: Test infrastructure — ✅ Done
- [x] 1F: Docker Compose foundation — ✅ Done
- [x] 1G: Frontend scaffold — ✅ Done

### Phase 2+
- [ ] AST parsing and Canonical IR
- [ ] Repository ingestion pipeline
- [ ] Embedding and vector indexing
- [ ] Symbol graph construction
- [ ] BM25 + vector + graph retrieval
- [ ] Retrieval fusion and reranking
- [ ] Provider-agnostic LLM interface
- [ ] React query UI
- [ ] Evaluation framework

---

## Known Decisions Made This Phase

See `DECISIONS.md` for full ADR list.

---

## Last Updated

2026-08-26 — Phase 1G complete (Vite + React + TypeScript frontend scaffold established under `frontend/` with ESLint, Prettier, API client service boundary, health check hook, and clean dark mode UI shell. Phase 1 Foundation complete!).
