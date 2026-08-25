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

## Ready (can be started now)

### TASK-1B: Python runtime setup

**Status:** ⬜ Pending  
**Blockers:** TASK-1A ✅  
**Scope:** Backend Python package configuration only; no business logic.

**Acceptance criteria:**
- [ ] `pyproject.toml` at repository root with project metadata and dev dependencies
      (`fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`,
       `pydantic-settings`, `ruff`, `mypy`, `pytest`, `pytest-asyncio`,
       `httpx`, `pytest-cov`)
- [ ] `.python-version` file pinning Python ≥ 3.12
- [ ] `ruff.toml` or `[tool.ruff]` section in `pyproject.toml` configured
- [ ] `mypy.ini` or `[tool.mypy]` section configured (strict mode)
- [ ] `backend/__init__.py` exists (empty package marker)
- [ ] `uv sync` or `pip install -e ".[dev]"` succeeds without errors
- [ ] `ruff check .` passes with zero errors on the empty codebase
- [ ] `mypy backend/` passes with zero errors on the empty package

**Files to create/modify:**
```
pyproject.toml
.python-version
backend/__init__.py
backend/py.typed
```

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

## Blocked on 1B (Python runtime)

### TASK-1C: Database foundation

**Status:** ⬜ Pending  
**Blockers:** TASK-1B ⬜  
**Scope:** Alembic scaffold and initial migration; no ORM models yet.

**Acceptance criteria:**
- [ ] `backend/db/` package with Alembic configuration
- [ ] `alembic.ini` configured with async SQLAlchemy URL
- [ ] First Alembic migration: create all tables in `DATABASE_SCHEMA.md`
      (`repositories`, `commits`, `files`, `symbols`, `chunks`, `jobs`,
       `index_versions`)
- [ ] `CREATE EXTENSION IF NOT EXISTS vector` included in migration
- [ ] Migration applies cleanly against a fresh PostgreSQL 16 database
- [ ] Migration rolls back cleanly

---

### TASK-1D: FastAPI skeleton

**Status:** ⬜ Pending  
**Blockers:** TASK-1B ⬜  
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
