# Development Roadmap — AI Code Understanding Engine

> **Current phase: Phase 1 — Foundation** 🟡

---

## Phase 1 — Foundation ← CURRENT

**Goal:** Establish the repository structure, persistent project memory, and
all core architectural constraints before any implementation begins.

| Task ID | Task | Status |
|---|---|---|
| 1A | Repository structure + `.ai/` project memory | ✅ Done |
| 1B | Python runtime setup (`pyproject.toml`, virtual env, `ruff`, `mypy`) | ⬜ Pending |
| 1C | Database foundation (Alembic scaffold, initial DDL) | ⬜ Pending |
| 1D | FastAPI skeleton (app factory, health endpoint, CORS, error handlers) | ⬜ Pending |
| 1E | Test infrastructure (pytest config, test DB fixture, CI script) | ⬜ Pending |
| 1F | Docker Compose foundation (postgres, backend, frontend, worker services) | ⬜ Pending |
| 1G | Frontend scaffold (Vite + React + TypeScript, ESLint, Prettier) | ⬜ Pending |

---

## Phase 2 — Database & API Foundation

**Goal:** Working PostgreSQL schema with Alembic migrations and a functional
FastAPI app with stubs for all planned endpoints.

| Task ID | Task |
|---|---|
| 2A | Alembic migration: `repositories`, `commits`, `files` tables |
| 2B | Alembic migration: `symbols`, `chunks` tables + pgvector extension |
| 2C | Alembic migration: `jobs`, `index_versions` tables |
| 2D | SQLAlchemy ORM models for all entities |
| 2E | Repository API endpoints (`POST`, `GET`) — stub implementations |
| 2F | Job enqueueing service |
| 2G | API contract tests (HTTP-level) |

---

## Phase 3 — Code Analysis — Canonical IR

**Goal:** A working AST parser for Java, Python, and TypeScript that produces
a Canonical Code IR stored in PostgreSQL.

| Task ID | Task |
|---|---|
| 3A | tree-sitter integration and parser registry |
| 3B | Python AST parser → Canonical IR |
| 3C | TypeScript AST parser → Canonical IR |
| 3D | Java AST parser → Canonical IR |
| 3E | IR → PostgreSQL writer (symbols, files) |
| 3F | IR unit tests for each language |

---

## Phase 4 — Symbol Graph

**Goal:** Populate the symbol relationship graph from the Canonical IR.

| Task ID | Task |
|---|---|
| 4A | Graph schema (symbol_edges table) |
| 4B | Graph builder — extract call/import/inheritance relationships |
| 4C | GraphRetriever — BFS/DFS traversal queries |
| 4D | Graph unit tests |

---

## Phase 5 — Indexing Pipeline

**Goal:** End-to-end repository ingestion: clone → parse → embed → index.

| Task ID | Task |
|---|---|
| 5A | RepoCloner — GitHub URL and local path support |
| 5B | Chunker — split IR into retrievable chunks |
| 5C | EmbeddingClient — provider-agnostic interface |
| 5D | Embedder — chunk → embedding → pgvector insert |
| 5E | IndexingPipeline — orchestrate clone→parse→graph→chunk→embed |
| 5F | Worker process — poll jobs table, run pipeline |
| 5G | `POST /api/v1/repositories/{id}/index` wired to job enqueue |
| 5H | `GET /api/v1/repositories/{id}/index-status` |
| 5I | Incremental indexing — git-diff based re-index |
| 5J | Repository size limit enforcement (≤ 1 M LOC) |

---

## Phase 6 — Retrieval Engine

**Goal:** Working hybrid retrieval — BM25, vector, graph — with fusion and reranking.

| Task ID | Task |
|---|---|
| 6A | BM25Retriever — PostgreSQL tsvector / pg_bm25 |
| 6B | VectorRetriever — pgvector cosine similarity |
| 6C | FusionRanker — reciprocal rank fusion or weighted score |
| 6D | ContextPruner — token budget enforcement |
| 6E | Retrieval integration tests |

---

## Phase 7 — LLM Integration

**Goal:** Working query pipeline — retrieval → LLM → cited answer.

| Task ID | Task |
|---|---|
| 7A | LLMClient — provider-agnostic interface |
| 7B | OpenAI adapter |
| 7C | Anthropic adapter |
| 7D | Ollama adapter |
| 7E | QueryService — wire retrieval + LLM |
| 7F | `POST /api/v1/query` endpoint |
| 7G | LLM integration tests (with mocked provider) |

---

## Phase 8 — Symbol & Impact APIs

**Goal:** Symbol lookup and impact analysis endpoints.

| Task ID | Task |
|---|---|
| 8A | `GET /api/v1/symbols/{id}` |
| 8B | `GET /api/v1/symbols/{id}/dependencies` |
| 8C | `GET /api/v1/symbols/{id}/dependents` |
| 8D | `POST /api/v1/impact-analysis` |
| 8E | ImpactService — graph traversal for blast-radius |

---

## Phase 9 — React Frontend

**Goal:** A working query UI connected to the backend API.

| Task ID | Task |
|---|---|
| 9A | Vite + React + TypeScript project scaffold |
| 9B | API client layer |
| 9C | Repository management UI (add, list, index) |
| 9D | Query UI (input, results, source citations) |
| 9E | Symbol browser |
| 9F | Index status polling |

---

## Phase 10 — Evaluation & Optimisation

**Goal:** Measure retrieval quality and query latency; optimise to hit targets.

| Task ID | Task |
|---|---|
| 10A | Retrieval benchmark dataset |
| 10B | MRR / NDCG evaluation harness |
| 10C | Query latency profiling (P95 target: ≤ 8 s) |
| 10D | Reranker implementation (if fusion alone is insufficient) |
| 10E | pgvector index tuning (IVFFlat vs HNSW) |
