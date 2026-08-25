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
TASK-1B: Python runtime setup (`pyproject.toml`, virtual env, `ruff`, `mypy`)
