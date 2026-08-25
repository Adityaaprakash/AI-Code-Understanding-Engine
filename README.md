# AI Code Understanding Engine — CodeLens AI

> **Status:** Phase 1 — Foundation (active development)

---

## What Is It?

The **AI Code Understanding Engine** (working product name: **CodeLens AI**) is a
local-first, developer-facing tool that provides deep, semantically-aware
understanding of large codebases. Given a natural-language question — *"Which
services call this database table?"*, *"What breaks if I change this interface?"*
— it locates the relevant code, explains it, and reasons about the impact, all
without requiring the developer to page through the repository manually.

---

## Why Ordinary Vector RAG Is Insufficient

Standard retrieval-augmented generation pipelines embed code chunks into dense
vectors and return the nearest neighbours. This approach has three structural
weaknesses for code:

| Problem | Impact |
|---|---|
| **No structural awareness** | Related symbols (caller / callee, implementation / interface) sit in different chunks that a similarity search may never co-retrieve. |
| **No relationship traversal** | Impact analysis requires following cross-file, cross-module call graphs — vector similarity cannot do this. |
| **Sparse vocabulary mismatch** | Code uses identifiers, not natural language. BM25 term frequency often outperforms dense retrieval on symbol names and error strings. |

CodeLens AI addresses this with a **hybrid retrieval stack**: BM25 + vector
similarity + graph traversal, fused and reranked before being passed to the LLM.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  React Frontend (CodeLens UI)                               │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST / JSON
┌──────────────────────────▼──────────────────────────────────┐
│  FastAPI Backend                                            │
│   ├─ Repository API   ├─ Query API   ├─ Symbol API          │
│   └─ Impact Analysis API                                    │
└──────┬───────────────────────────────────────┬──────────────┘
       │ Async jobs (PostgreSQL queue)          │ Sync queries
┌──────▼──────────┐                   ┌────────▼──────────────┐
│  Worker Process │                   │  Retrieval Engine     │
│  ├─ Index repos │                   │  ├─ BM25              │
│  ├─ Parse ASTs  │                   │  ├─ Vector (pgvector) │
│  └─ Build graph │                   │  ├─ Graph traversal   │
└──────┬──────────┘                   │  ├─ Fusion + Rerank   │
       │                              │  └─ Context pruning   │
┌──────▼──────────────────────────────▼──────────────────────┐
│  PostgreSQL (primary store + pgvector + job queue)          │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  Provider-agnostic LLM & Embedding Interface                │
│  (OpenAI / Anthropic / Ollama / Azure OpenAI)               │
└─────────────────────────────────────────────────────────────┘
```

**Code analysis pipeline (at index time):**
```
Repository (GitHub URL or local path)
  ↓ Clone / read
AST Parser (tree-sitter — Java, Python, TypeScript)
  ↓
Canonical Code IR (repository / file / module / class /
                   function / method / variable / reference)
  ↓
Symbol graph builder      Chunk builder
  ↓                            ↓
PostgreSQL graph tables   Embeddings → pgvector
```

---

## MVP Languages

| Language | AST library |
|---|---|
| Java | tree-sitter-java |
| Python | tree-sitter-python |
| TypeScript | tree-sitter-typescript |

Additional languages can be added in later phases via a plugin-style parser registry.

---

## Local-First Philosophy

* All data (code index, embeddings, graph) is stored in a local PostgreSQL
  database.
* No telemetry, no cloud data upload required.
* LLM and embedding calls go to the provider you configure (or a local Ollama
  instance).
* The architecture is cloud-ready: the same stack runs unchanged on a VM or
  container host.

---

## Repository Targets

| Metric | Target |
|---|---|
| Maximum repository size | ≤ 1 M LOC |
| Query P95 latency | ≤ 8 seconds |

---

## Development Phases

| Phase | Description | Status |
|---|---|---|
| 1 | Foundation — repo structure, project memory, constraints | 🟡 In progress |
| 2 | Technology setup — Python runtime, DB migrations, test infra | ⬜ Pending |
| 3 | Database foundation — schema, migrations, seed data | ⬜ Pending |
| 4 | API foundation — FastAPI skeleton, auth scaffold | ⬜ Pending |
| 5 | Code analysis — AST parsing, Canonical IR | ⬜ Pending |
| 6 | Indexing pipeline — ingestion, embedding, graph | ⬜ Pending |
| 7 | Retrieval engine — BM25 + vector + graph + fusion | ⬜ Pending |
| 8 | LLM integration — provider-agnostic interface | ⬜ Pending |
| 9 | Frontend — React UI, query interface | ⬜ Pending |
| 10 | Evaluation & optimisation | ⬜ Pending |

---

## Repository Layout

```
.ai/              Project memory (AI context files)
backend/          FastAPI application
frontend/         React application
code-analyzer/    AST parsing and Canonical IR
retrieval/        BM25 / vector / graph retrieval
graph/            Symbol graph builder
llm/              Provider-agnostic LLM/embedding interface
evaluation/       Benchmarks and quality metrics
experiments/      Research notebooks and prototypes
docs/             Architecture and API documentation
docker/           Docker and docker-compose files
tests/            Cross-component integration tests
```

---

## Getting Started

> **Full setup instructions will be added in Phase 2.**

Prerequisites (planned): Python ≥ 3.12, Node ≥ 20, Docker, PostgreSQL 16.

---

*This project is actively developed. See [`.ai/CURRENT_STATE.md`](.ai/CURRENT_STATE.md) for
the live development status.*
