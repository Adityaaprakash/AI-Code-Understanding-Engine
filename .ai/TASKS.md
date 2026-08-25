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

**Status:** ⬜ Pending  
**Blockers:** TASK-1B ✅, TASK-1C ✅  
**Scope:** App factory, lifespan, CORS, error handlers, health endpoint only.

**Acceptance criteria:**
- [ ] `backend/main.py` — FastAPI app factory with lifespan context
- [ ] `GET /health` returns `{"status": "ok"}` with HTTP 200
- [ ] CORS middleware configured (allow origins from env var)
- [ ] Global exception handler returns `{"error": "<message>"}` — no
      stack traces in responses
- [ ] Request validation errors return HTTP 422 with structured body
- [ ] `uvicorn backend.main:app --reload` starts without errors
- [ ] `mypy backend/main.py` passes

---

### TASK-1E: Test infrastructure

**Status:** ⬜ Pending  
**Blockers:** TASK-1B ⬜, TASK-1D ⬜  
**Scope:** pytest configuration and one smoke test; no feature tests yet.

**Acceptance criteria:**
- [ ] `pytest.ini` or `[tool.pytest.ini_options]` in `pyproject.toml`
- [ ] `tests/conftest.py` with async test client fixture
- [ ] `tests/test_health.py` — smoke test: `GET /health` returns HTTP 200
- [ ] `pytest tests/` passes with zero failures
- [ ] Coverage report generated (`pytest --cov=backend`)

---

## Blocked on 1B + 1C + 1D + 1E

### TASK-1F: Docker Compose foundation

**Status:** ⬜ Pending  
**Blockers:** TASK-1C ⬜, TASK-1D ⬜, TASK-1E ⬜  
**Scope:** Docker Compose that brings up postgres + backend + worker; no frontend
service needed for this task.

**Acceptance criteria:**
- [ ] `docker/docker-compose.yml` with services: `postgres`, `backend`, `worker`
- [ ] `docker/Dockerfile.backend` — Python image, installs deps, runs uvicorn
- [ ] `docker/Dockerfile.worker` — same image, runs worker entrypoint
- [ ] `docker compose up` starts all services without errors
- [ ] `GET http://localhost:8000/health` returns HTTP 200 when running
- [ ] PostgreSQL data persisted in a named Docker volume
- [ ] All secrets sourced from `.env` file (not hardcoded in Compose file)

---

## Notes for AI Agents

- Each task above is independently implementable; do not merge tasks.
- "Acceptance criteria" is the definition of done; do not mark a task complete
  unless all criteria are met.
- After completing a task: update `CURRENT_STATE.md`, `CHANGELOG.md`,
  and this file.
