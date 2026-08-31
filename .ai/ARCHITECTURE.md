# Architecture — AI Code Understanding Engine

## Architectural Style

**Modular monolith** with a separate **worker process** for asynchronous indexing.
All modules share a single PostgreSQL database. There is no inter-service network
communication. The worker is a separate OS process, not a separate service.

---

## Component Map

```
┌─────────────────────────────────────────────────────────────────┐
│  React Frontend  (frontend/)                                    │
│  Vite + TypeScript + React                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST/JSON  (HTTP)
┌────────────────────────────▼────────────────────────────────────┐
│  FastAPI Backend  (backend/)                                    │
│                                                                 │
│  Routers:                                                       │
│    /api/v1/repositories    — Repository CRUD + indexing         │
│    /api/v1/query           — Natural-language query             │
│    /api/v1/symbols         — Symbol lookup + dependency graph   │
│    /api/v1/impact-analysis — Blast-radius analysis              │
│                                                                 │
│  Services:                                                      │
│    RepositoryService       IndexingService                      │
│    QueryService            SymbolService                        │
│    ImpactService           JobService                           │
└──────────┬───────────────────────────────────────┬─────────────┘
           │ Enqueue job                           │ Sync queries
           │ (PostgreSQL jobs table)               │
┌──────────▼─────────────┐             ┌───────────▼─────────────┐
│  Worker Process        │             │  Retrieval Engine        │
│  (backend/worker/)     │             │  (retrieval/)            │
│                        │             │                          │
│  JobRunner             │             │  BM25Retriever           │
│  IndexingPipeline      │             │  VectorRetriever         │
│    ├─ RepoCloner       │             │  GraphRetriever          │
│    ├─ ASTParser        │             │  FusionRanker            │
│    ├─ IRBuilder        │             │  ContextPruner           │
│    ├─ GraphBuilder     │             └───────────┬─────────────┘
│    ├─ Chunker          │                         │
│    └─ Embedder         │             ┌───────────▼─────────────┐
└──────────┬─────────────┘             │  LLM Interface           │
           │                           │  (llm/)                  │
           │                           │  Provider-agnostic       │
           │                           │  LLMClient               │
           │                           │  EmbeddingClient         │
           │                           └─────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────────┐
│  PostgreSQL 16                                                  │
│                                                                 │
│  Core tables:   repositories  commits  files  symbols          │
│                 chunks  jobs  index_versions                    │
│                                                                 │
│  Extensions:    pgvector  (vector similarity)                   │
│                 pg_trgm   (fuzzy text search)                   │
│                 tsvector  (BM25 full-text)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Responsibilities

### `backend/`
FastAPI application. Owns the HTTP API, request validation, authentication
scaffold, and response formatting. Delegates business logic to services.
Does NOT contain AST parsing, retrieval logic, or LLM calls directly —
these are delegated to the respective modules.

### `code-analyzer/`
AST parsing using tree-sitter. Produces the Canonical Code IR (see
`CODE_IR.md`). Supports Java, Python, TypeScript in MVP.

### `retrieval/`
AST/IR-aware code chunking foundation and hybrid retrieval engine:
- `CodeChunker`: Language-independent AST/IR-aware chunker that transforms Canonical Code IR (`NormalizationResult`) into deterministic, semantically structured `CodeChunk` models without reparsing source code.
- `ChunkType`: Defines hierarchical chunk types (`FILE_CONTEXT`, `CLASS_CONTEXT`, `INTERFACE_CONTEXT`, `FUNCTION`, `METHOD`, `SUB_CHUNK`).
- `generate_chunk_id`: Deterministic UUID v5 chunk identity generator based on semantic context and location.
- Future components: BM25 (PostgreSQL tsvector/pg_bm25), vector similarity (pgvector cosine), graph traversal, fusion scoring, and context pruning.

### `graph/`
Builds and maintains the symbol relationship graph. Reads the Canonical
Code IR produced by `code-analyzer/` and provides graph storage (`InMemoryGraphStore`),
traversal query engine (`GraphQueryEngine`), and impact analysis engine (`ImpactAnalyzer`).
Executes reverse dependency BFS traversal to calculate direct/transitive blast radius
and deterministic explanation paths.

### `llm/`
Provider-agnostic LLM and embedding interfaces. Abstracts over
OpenAI, Anthropic, Azure OpenAI, and Ollama. Never called directly by
routers — called only by services.

### `evaluation/`
Benchmarks, retrieval quality metrics, and regression tests.
Not imported by production code.

### `experiments/`
Research notebooks and prototypes. Not imported by production code.

### `frontend/`
React + TypeScript single-page application. Communicates with the
backend exclusively over the REST API.

### `docker/`
Dockerfiles and docker-compose configuration.

### `tests/`
Cross-component integration tests.

---

## Data Flows

### Index-time flow
```
User submits repository URL/path
  → POST /api/v1/repositories (backend)
  → RepositoryService creates DB record
  → JobService enqueues "index" job (PostgreSQL jobs table)
  → Worker polls jobs table
  → IndexingPipeline:
      RepoCloner → local checkout
      ASTParser  → parse all source files
      IRBuilder  → produce Canonical Code IR
      GraphBuilder → write symbol graph to PostgreSQL
      Chunker    → split IR into retrievable chunks
      Embedder   → call EmbeddingClient → pgvector inserts
  → JobService marks job complete
  → IndexVersion record written
```

### Query-time flow
```
User submits natural-language query
  → POST /api/v1/query (backend)
  → QueryService:
      EmbeddingClient → embed query
      RetrievalEngine:
        BM25Retriever   → PostgreSQL tsvector/pg_bm25
        VectorRetriever → pgvector cosine similarity
        GraphRetriever  → symbol graph traversal
        FusionRanker    → scored candidate list
        ContextPruner   → token budget trimming
      LLMClient → generate answer with citations
  → Return answer + source references to frontend
```

---

## Indexing Strategies

| Strategy | Trigger | Scope |
|---|---|---|
| Full index | First submission; manual re-index | Entire repository |
| Incremental | Git push webhook / manual | Changed files only (git-diff) |

---

## Performance Targets

| Metric | Target |
|---|---|
| Repository size limit | ≤ 1 M LOC |
| Query P95 latency | ≤ 8 seconds end-to-end |
| Indexing throughput | Best-effort; not a hard P95 target |

---

## What This Architecture Is NOT

- Not a microservices system. The backend and worker share code and a database.
- Not event-driven. The job queue is polled, not pushed via a broker.
- Not distributed. All components run on one host in Docker Compose.
