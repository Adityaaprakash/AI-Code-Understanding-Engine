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
