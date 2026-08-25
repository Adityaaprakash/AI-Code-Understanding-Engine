# Current State — AI Code Understanding Engine

## Active Phase

**Phase 1 — Foundation**

---

## Current Task

TASK-1D (FastAPI Foundation) complete. Next: TASK-1E — Test Infrastructure.

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

---

## In Progress

- [ ] TASK-1E: Test Infrastructure (pytest fixtures, test database setup, CI script)

---

## Blocked / Pending

### Phase 1 Remaining
- [x] 1B: Python runtime setup — ✅ Done
- [x] 1C: Database foundation — ✅ Done
- [x] 1D: FastAPI skeleton — ✅ Done
- [ ] 1E: Test infrastructure (pytest config, test database fixture, CI script)
- [ ] 1F: Docker Compose foundation (postgres, backend, frontend, worker services)
- [ ] 1G: Frontend scaffold (Vite + React + TypeScript, ESLint, Prettier)

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

2026-08-25 — Phase 1D complete (FastAPI application factory, CORS, error handling, health endpoint, settings, tests).
