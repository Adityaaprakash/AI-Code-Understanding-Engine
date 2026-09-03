# Architectural Decision Records — AI Code Understanding Engine

All locked decisions are recorded here as ADR-style entries.
**Do not contradict any of these decisions** without first creating a new ADR
and having it approved by the human developer.

---

## ADR-001: Modular Monolith Architecture

**Status:** Accepted  
**Date:** 2026-08-25

### Context
The project needs a clear architectural style to guide all future structural decisions.

### Decision
Use a modular monolith: a single deployable backend process with clearly separated
Python modules (`backend/`, `code-analyzer/`, `retrieval/`, `graph/`, `llm/`).
A separate worker process handles asynchronous indexing jobs.

### Rationale
- Simpler than microservices: no inter-service networking, service discovery, or
  distributed tracing required at MVP scale.
- Modules can be extracted into separate services later if needed without
  re-architecting the logic.
- One database connection pool; no distributed transaction complexity.

### Consequences
- All modules share the PostgreSQL database.
- Module boundaries must be enforced by code organization, not network isolation.

---

## ADR-002: PostgreSQL as Sole Primary Database

**Status:** Accepted  
**Date:** 2026-08-25

### Context
The system needs persistence for repositories, symbols, embeddings, full-text
search, the job queue, and the symbol graph.

### Decision
Use PostgreSQL 16 as the single primary data store for all data.
Use the `pgvector` extension for vector similarity.
Use `tsvector` / `pg_bm25` for full-text BM25 search.
Use PostgreSQL tables for the job queue and the symbol graph.

### Rationale
- Eliminates operational complexity of running multiple data stores.
- pgvector provides production-grade ANN search within PostgreSQL.
- PostgreSQL's ACID guarantees cover both relational and vector data atomically.
- A PostgreSQL job queue avoids introducing a message broker.

### Consequences
- No Redis, Neo4j, Elasticsearch, or any external vector database.
- No external message broker (Kafka, RabbitMQ, etc.).

---

## ADR-003: PostgreSQL-Backed Job Queue (No External Broker)

**Status:** Accepted  
**Date:** 2026-08-25

### Context
Repository indexing is asynchronous and potentially long-running.
An async mechanism is needed to decouple API responses from indexing work.

### Decision
Implement the job queue as a PostgreSQL table with `SELECT FOR UPDATE SKIP LOCKED`
polling from worker processes.

### Rationale
- No additional infrastructure dependency.
- Transactional job state: a job is either claimed or not — no invisible messages.
- Sufficient throughput for MVP (indexing is not a high-frequency operation).

### Consequences
- Kafka, RabbitMQ, Celery with broker, and similar technologies are excluded.
- Worker concurrency is controlled by the number of worker processes polling.

---

## ADR-004: FastAPI as Backend Framework

**Status:** Accepted  
**Date:** 2026-08-25

### Context
The backend needs an HTTP API framework. The primary language is Python.

### Decision
Use FastAPI with async request handling (`asyncpg` / `SQLAlchemy async`).

### Rationale
- Native async support aligns with async database drivers.
- Automatic OpenAPI schema generation.
- Strong type validation via Pydantic.
- Large ecosystem for Python ML/NLP libraries needed in later phases.

### Consequences
- All API logic is in Python. No separate Go, Node, or Java API layer.

---

## ADR-005: React + TypeScript Frontend

**Status:** Accepted  
**Date:** 2026-08-25

### Context
A web UI is required for the query interface.

### Decision
Use React with TypeScript, bundled with Vite.

### Rationale
- Standard modern frontend stack with strong type safety.
- Vite provides fast development iteration.

### Consequences
- Frontend communicates with the backend exclusively via the REST API.
- No server-side rendering framework (Next.js etc.) in MVP.

---

## ADR-006: Provider-Agnostic LLM and Embedding Interfaces

**Status:** Accepted  
**Date:** 2026-08-25

### Context
LLM and embedding providers evolve rapidly. Locking to a single provider
creates migration risk.

### Decision
Implement `LLMClient` and `EmbeddingClient` as abstract interfaces with
concrete adapters for: OpenAI, Anthropic, Azure OpenAI, and Ollama.
The provider and model are selected via environment variables.

### Rationale
- Production deployments can use cloud providers; local dev can use Ollama.
- Switching providers requires only a config change, not a code change.

### Consequences
- No direct `openai.ChatCompletion.create()` calls outside the `llm/` module.

---

## ADR-007: AST-Based Code Analysis with Canonical IR

**Status:** Accepted  
**Date:** 2026-08-25

### Context
Code understanding requires structural analysis, not just text processing.

### Decision
Use `tree-sitter` to parse source code into ASTs. Transform ASTs into a
Canonical Code IR (see `CODE_IR.md`) that is language-agnostic.

### Rationale
- tree-sitter supports Java, Python, and TypeScript with production-quality grammars.
- A language-agnostic IR allows retrieval and graph logic to work uniformly
  across languages.

### Consequences
- No regular-expression-based code parsing in production code.
- IR definition is locked in `CODE_IR.md` and changes require an ADR.

---

## ADR-008: Hybrid Retrieval — BM25 + Vector + Graph

**Status:** Accepted  
**Date:** 2026-08-25

### Context
Pure vector similarity retrieval is insufficient for code (see `README.md`,
`RETRIEVAL.md`).

### Decision
Retrieve candidates via three parallel paths — BM25, vector similarity, and
graph traversal — then fuse and rerank.

### Rationale
- BM25 handles exact symbol name and error-string matches.
- Vector handles semantic similarity.
- Graph traversal retrieves structurally related symbols (callers/callees).
- Fusion compensates for the weaknesses of each individual retriever.

### Consequences
- All three retrievers must be implemented before the query pipeline goes live.

---

## ADR-009: MVP Language Support — Java, Python, TypeScript

**Status:** Accepted  
**Date:** 2026-08-25

### Context
The system must support multiple programming languages.

### Decision
Support Java, Python, and TypeScript as MVP languages via tree-sitter parsers.

### Rationale
- These three languages cover the majority of enterprise, data/ML, and web codebases.
- tree-sitter grammars for all three are mature and maintained.

### Consequences
- Other languages can be added later via the parser registry without changing
  the Canonical IR or retrieval pipeline.

---

## ADR-010: Local-First Deployment via Docker Compose

**Status:** Accepted  
**Date:** 2026-08-25

### Context
The product must be usable by a developer on a laptop without cloud dependencies.

### Decision
All services (PostgreSQL, backend, worker, frontend) are defined in Docker Compose
and run locally. No cloud services are required.

### Rationale
- Privacy: code never leaves the developer's machine by default.
- Reproducibility: identical environment across developer machines.

### Consequences
- Kubernetes is not used in MVP.
- The same Docker images must be cloud-deployable with minimal config change.

---

## ADR-011: Incremental Indexing via Git Diff

**Status:** Accepted  
**Date:** 2026-08-25

### Context
Full re-indexing of a 1 M LOC repository on every change is prohibitively slow.

### Decision
Implement incremental indexing by computing the git diff between the last indexed
commit and the current HEAD, then re-parsing and re-embedding only changed files.

### Rationale
- Minimises indexing time for ongoing workflows.
- git diff is reliable and language-agnostic.

### Consequences
- The `index_versions` table must track the last successfully indexed commit SHA.
- Incremental indexing is scoped to file-level changes; symbol-level diffing is
  a future optimisation.

---

## ADR-012: Repository Size Limit — ≤ 1 M LOC

**Status:** Accepted  
**Date:** 2026-08-25

### Context
Very large repositories impose unbounded indexing time and storage requirements.

### Decision
Reject repositories larger than 1 M LOC at submission time. Surface a clear
error to the user.

### Rationale
- Sets a predictable capacity contract for MVP.
- Most real-world codebases that a single developer navigates fall within this
  limit.

### Consequences
- Monolithic repositories (e.g., large open-source monorepos) may require
  sub-directory scoping, which is a future feature.

---

## ADR-013: Python 3.12 and uv as Package Manager

**Status:** Accepted  
**Date:** 2026-08-25

### Context
The project needs a pinned Python version and a reproducible dependency management
workflow for the backend and code-analysis modules.

### Decision
Use **Python 3.12** as the minimum and pinned runtime version (`.python-version` = `3.12`).
Use **uv** as the package manager and virtual environment tool.
All dependencies are declared in `pyproject.toml` using PEP 621 (`[project]`) and
PEP 735 (`[dependency-groups]`).

### Rationale
- Python 3.12 is the current stable LTS release with improved performance and
  better typing support (`TypeVarTuple`, improved `TypeAlias`, etc.).
- `uv` is a fast, reproducible package manager that:
  - Downloads and manages Python versions automatically (no separate pyenv required)
  - Produces a `uv.lock` lockfile for reproducible installs
  - Is compatible with PEP 621 `pyproject.toml`
  - Is significantly faster than pip for CI/CD use cases

### Consequences
- All developers and CI environments use `uv sync` to install dependencies.
- The pinned version in `.python-version` is read by uv automatically.
- Do not commit `.venv/` (already in `.gitignore`).
- Do commit `uv.lock` (to be generated — guarantees reproducible installs).

---

## ADR-014: Impact Analysis via Reverse Dependency Traversal

**Status:** Accepted  
**Date:** 2026-08-30

### Context
The Code Knowledge Graph must answer blast-radius and impact analysis questions ("Who depends on symbol X?", "What code is affected if symbol X changes?").

### Decision
Implement `ImpactAnalyzer` using Breadth-First Search (BFS) reverse dependency traversal over the Code Knowledge Graph:
1. Inbound traversal (`dependent_id -> dependency_id`) following semantic dependency edge kinds (`CALLS`, `USES`, `EXTENDS`, `IMPLEMENTS`, `OVERRIDES`, `READS`, `REFERENCES`, `IMPORTS`).
2. Minimum depth computation (`minimum_depth`) ensuring that if a symbol is reachable via multiple paths, its reported distance is the shortest hop distance from the root.
3. Path explanation reconstruction (`ImpactPath` and `ImpactPathStep`) preserving original stored edge transition directionality (`source_id -> target_id via kind`).
4. Strict cycle safety preventing infinite recursion on recursive or cyclic graph structures.
5. Self-loop and structural containment edge exclusion (`DECLARES` edge filtering).

### Rationale
- Pure graph-derived traversal operates on pre-extracted semantic relationships without reparsing source code or fuzzy string matching.
- BFS naturally discovers shortest paths for distance calculation.
- Explanatory path structures enable downstream LLMs and UI components to explain *why* a symbol is impacted.

### Consequences
- Requires valid symbol resolution and relationship extraction.
- Graph queries must use `InMemoryGraphStore` or PostgreSQL index lookup for reverse edges (`inbound_index`).

---

## ADR-015: AST/IR-Aware Code Chunking Strategy

**Status:** Accepted  
**Date:** 2026-08-31

### Context
Phase 4 (Chunking & Indexing) requires partitioning raw source code into retrievable, semantically meaningful units for vector embedding, BM25 indexing, and context construction. Arbitrary fixed-token or character window splitting destroys code semantics, breaks function boundaries, and degrades retrieval precision.

### Decision
Implement a single, language-independent `CodeChunker` in `retrieval/` that operates on the Canonical Code IR (`NormalizationResult`):
1. **No Reparation**: Consumes existing `NormalizationResult` entities (`File`, `Class`, `Interface`, `Function`, `Method`) without re-parsing source code via tree-sitter.
2. **Semantic Chunk Hierarchy**: Emits `FILE_CONTEXT`, `CLASS_CONTEXT`, `INTERFACE_CONTEXT`, `FUNCTION`, and `METHOD` chunks while preserving parent-child relationships (`parent_entity_id`, `parent_chunk_id`).
3. **Deterministic Chunk Identity**: Uses UUID v5 generated from a stable seed key (`repo|file|type|entity|loc|sub_index`) under a fixed `CODELENS_CHUNK_NAMESPACE`.
4. **Minimum Sufficient Context**: Classes emit structural outlines (`CLASS_CONTEXT`) rather than duplicating all method bodies; child methods link to their parent class without repeating the file header.
5. **Oversized Entity Fallback Policy**: When a method or class exceeds `max_lines_per_chunk` (default 150 lines), the chunker emits a primary chunk (`sub_chunk_index=0`) for the header/overview, followed by contiguous line-range sub-chunks (`ChunkType.SUB_CHUNK`, `sub_chunk_index=1..N`) preserving parent identity and exact source order.
6. **Deterministic Source Ordering**: Chunks are sorted by `FILE_CONTEXT` priority, followed by `start_line`, `start_column`, `chunk_type`, `entity_id`, and `sub_chunk_index`.
7. **Canonical IR Immutability & Graph Separation**: The chunking process treats the Canonical IR as strictly immutable and does NOT modify the Code Knowledge Graph or add graph edges.

### Rationale
- Language independence: Normalizing parsing details into Canonical IR allows one chunker to support Java, Python, TypeScript, and future languages seamlessly.
- Semantic preservation: Method and function boundaries are preserved intact, preventing fragmented code snippets.
- Determinism: Identical IR inputs produce identical chunk IDs and collections across runs and environments.

### Consequences
- Requires valid `NormalizationResult` and `SourceLocation` bounds from Phase 2 normalizers.
- Phase 4B (Metadata Enrichment) will augment `CodeChunk.metadata` without modifying `CodeChunk` core structure or identity.

---

## ADR-016: Application Shell & CSS Design System

**Status:** Accepted  
**Date:** 2026-09-03

### Context
Phase 7 requires a modern, accessible, developer-focused web UI to showcase the codebase intelligence engine.

### Decision
Implement a pure Vanilla CSS layout and token system (`index.css`), utilizing native CSS variables for typography, spacing, surfaces, and semantic colors. Establish a persistent layout (`AppShell`) with React Router for routing without imposing external UI libraries like Tailwind or Material UI.

### Rationale
- Pure CSS minimizes dependencies and establishes an independent visual identity aligned with developer products (Linear / GitHub / Modern IDE).
- CSS variables trivially support dynamic theming (Dark/Light/System) managed via a React Context.
- Reusable React components (`Button`, `Badge`, `EmptyState`) encapsulate style and accessibility logic securely.

### Consequences
- Components must be built from the established design tokens.
- No utility frameworks (like tailwind) will pollute the JSX, keeping logic separated from styling.

