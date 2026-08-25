# Current State — AI Code Understanding Engine

## Active Phase

**Phase 1 — Foundation**

---

## Current Task

Repository foundation and persistent project context.

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

---

## In Progress

- [ ] Repository foundation (this task — wrapping up)

---

## Blocked / Pending

### Phase 1 Remaining
- [ ] 1B: Python runtime setup (`pyproject.toml`, `uv` / `pip-tools`, virtual env)
- [ ] 1C: Database foundation (Alembic migrations scaffold, initial schema DDL)
- [ ] 1D: FastAPI skeleton (app factory, health endpoint, CORS, error handlers)
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

2026-08-25 — Phase 1A complete (foundation files and directory structure).
