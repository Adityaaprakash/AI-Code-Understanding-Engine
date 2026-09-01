# Retrieval Architecture — AI Code Understanding Engine

> **Status:** Phase 5 — Hybrid Retrieval Engine IN PROGRESS (Phase 5A Query Preprocessing & Phase 5B Lexical Retrieval COMPLETE).

---

## Overview

The retrieval engine answers the question: *given a natural-language query,
which code chunks and symbols are most relevant?*

A single retrieval path (e.g., pure vector similarity) is insufficient for code.
CodeLens AI uses three parallel retrieval paths (Lexical/BM25, Vector, and Graph), fuses their results, and then
prunes to a token budget before passing to the LLM.

---

## Pipeline Diagram

```
                    User Query (raw text)
                           │
                    ┌──────▼──────┐
                    │    Query    │  QueryPreprocessor → ProcessedQuery
                    │Preprocessor │  (Normalization, Tokenization, QueryKind)
                    └──────┬──────┘
                           │ ProcessedQuery
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──────┐  ┌──────▼──────┐  ┌─────▼───────┐
   │   Lexical   │  │   Vector    │  │    Graph    │
   │  Retriever  │  │  Retriever  │  │  Retriever  │
   └──────┬──────┘  └──────┬──────┘  └─────┬───────┘
          │ (BM25)         │                │
          └────────────────┼────────────────┘
                           │ Candidate lists (chunk_id, score, rank)
                    ┌──────▼──────┐
                    │  Candidate  │
                    │   Fusion    │  Reciprocal Rank Fusion (RRF)
                    └──────┬──────┘
                           │ Fused + scored candidate list
                    ┌──────▼──────┐
                    │  Reranking  │  Cross-encoder reranker (optional)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Graph     │
                    │  Expansion  │  Add structurally related symbols
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Context    │
                    │  Pruning    │  Enforce token budget
                    └──────┬──────┘
                           │ Final context (chunks + metadata)
                    ┌──────▼──────┐
                    │     LLM     │  Generate answer with citations
                    └─────────────┘
```

---

## Retrieval Components

### Query Preprocessing (TASK-5A Implemented & Hardened)

**Purpose:** Clean, normalize, tokenize, extract code identifiers, and deterministically classify user queries before executing retrieval paths.

**Key Architecture Features:**
- **Immutable Query Model (`ProcessedQuery`):** Preserves un-mutated `original_query`, normalized `normalized_query`, `tokens`, `identifier_tokens`, `text_tokens`, `qualified_name_candidates`, `query_kind`, and `metadata`.
- **Query Classification (`QueryKind`):**
  - `IDENTIFIER`: Pure code symbol / function name (e.g. `PaymentService`, `processPayment`, `get_user_by_id`, `JWTAuthenticationFilter`).
  - `QUALIFIED_IDENTIFIER`: Dot-separated identifier (e.g. `PaymentService.processPayment`, `com.example.payment.PaymentService`).
  - `PATH_OR_FILE`: File path or code file name (e.g. `src/auth/AuthService.java`, `AuthService.java`).
  - `RELATIONSHIP`: Intent phrases like "who calls", "which classes implement", "depends on" + identifier.
  - `NATURAL_LANGUAGE`: Prose question without code symbols (e.g. "How does authentication work?").
  - `MIXED`: Combination of prose question and code identifiers (e.g. "How does PaymentService process payments?").
  - `UNKNOWN`: Fallback.
- **Normalization:** Unicode NFC normalization, whitespace collapsing, casing preservation.
- **Input Validation:** Raises `LexicalQueryError` on empty or whitespace-only queries.

---

### Lexical BM25 Retrieval Service (`LexicalRetriever`) (TASK-5B Implemented & Hardened)

**Purpose:** Service layer for exact and near-exact keyword search — symbol names, qualified names, method signatures, file paths, and identifiers. Consumes Phase 4 BM25 index primitives.

**Implementation:** Pure, deterministic `LexicalRetriever` implementing `LexicalRetrieverContract`.

**Key Architecture Features:**
- **Single Source of Identity:** `RetrievalResult.chunk_id` strictly maps to canonical `CodeChunk.id` from Phase 4.
- **Repository Isolation Boundary:** Search calls must provide a non-empty `repository_id`. Search results are strictly isolated per repository.
- **Metadata Filtering:** Supports optional filtering by `language`, `chunk_type`, `file_path`, and `commit_sha`.
- **Adversarial Symbol Advantage:** Symbol matches rank #1 over body term repetition due to field weighting (symbol name 10.0x, qualified name 5.0x).
- **Latency Observability:** Measures and reports `preprocessing_latency_ms`, `retrieval_latency_ms`, and `total_latency_ms`.
- **Immutability & Determinism:** Search calls do not mutate index document counts or state. Results sort deterministically by `score` DESC, `chunk_id` ASC.

**Inputs:** Raw query string or `ProcessedQuery`, `repository_id`, optional `top_k`, `language`, `chunk_type`, `file_path`, `commit_sha` filters.  
**Outputs:** `RetrievalResultSet` model containing `ProcessedQuery`, ordered `RetrievalResult` candidates, and latency metrics.

---

### Vector Retrieval Service (`VectorRetriever`) (TASK-5C Implemented & Hardened)

**Purpose:** Service layer for semantic vector search — natural language query understanding, concept matching, and cross-language semantic similarity. Consumes Phase 4 `EmbeddingProviderContract` and in-memory `VectorIndex`.

**Implementation:** Pure, deterministic `VectorRetriever` implementing `VectorRetrieverContract`.

**Key Architecture Features:**
- **Single Source of Identity:** `RetrievalResult.chunk_id` strictly maps to canonical `CodeChunk.id` from Phase 4 (`VectorHit.chunk_id` == `RetrievalResult.chunk_id` == `CodeChunk.id`).
- **No Document Re-embedding:** Search query execution ONLY embeds the single query string (1 call to `EmbeddingProviderContract`), reusing pre-indexed chunk vectors.
- **Repository Isolation Boundary:** Search calls must provide a non-empty `repository_id`. Search results are strictly isolated per repository.
- **Metadata Filtering:** Supports optional filtering by `language`, `chunk_type`, `file_path`, and `commit_sha`.
- **Raw Cosine Similarity Scores:** Calculates exact cosine similarity score $u \cdot v / (\|u\|_2 \|v\|_2)$ in the range $[-1.0, 1.0]$. Preserves raw native score for downstream fusion (5E).
- **Latency Observability:** Measures and reports `preprocessing_latency_ms`, `retrieval_latency_ms`, and `total_latency_ms`.
- **Immutability & Determinism:** Search calls do not mutate index document counts or vectors. Results sort deterministically by `score` DESC, `chunk_id` ASC.

**Inputs:** Raw query string or `ProcessedQuery`, `repository_id`, optional `top_k`, `language`, `chunk_type`, `file_path`, `commit_sha` filters.  
**Outputs:** `RetrievalResultSet` model containing `ProcessedQuery`, ordered `RetrievalResult` candidates, and latency metrics.


---

### Graph Retrieval Service (`GraphRetriever`) (TASK-5D Implemented & Hardened)

**Purpose:** Structural retrieval layer — retrieves code candidates based on explicit code relationships (callers, callees, dependents, dependencies, implementations, inheritance, imports, references, and impact radius). Consumes `ProcessedQuery` and integrates with Phase 3 `GraphQueryEngine`, `ImpactAnalyzer`, and `CodeGraph`.

**Implementation:** Pure, deterministic `GraphRetriever` implementing `GraphRetrieverContract`.

**Key Architecture Features:**
- **Natural Language Intent Interpretation:** Interprets relationship intents from `ProcessedQuery` metadata and regex patterns:
  - `CALLS` (Inbound callers vs outbound callees)
  - `IMPLEMENTS` (Inbound implementations vs outbound interfaces)
  - `EXTENDS` (Inbound subclasses vs outbound base class)
  - `DEPENDENT` / `DEPENDENCY` (Inbound dependents vs outbound dependencies)
  - `IMPORTS` (Inbound importing modules vs outbound imported modules)
  - `USES` (Inbound usages / references)
  - `IMPACT` (Transitive impact radius via Phase 3 `ImpactAnalyzer` BFS)
  - `IDENTIFIER` (Target symbol node + 1-hop structural neighbors)
- **Single Source of Identity:** Maps graph node identities strictly to canonical `CodeChunk.id` from Phase 4/5 (`RetrievalResult.chunk_id` == `CodeChunk.id`). If a registered `CodeChunk` is not in lookup, direct node property extraction builds a compatible `RetrievalResult`.
- **Cycle-Safe & Depth-Bounded Traversals:** Leverages cycle-safe graph algorithms from Phase 3, avoiding infinite recursion on cyclic code graphs (e.g. `A -> B -> C -> A`).
- **Repository Isolation Boundary:** Graph search calls must specify a target `repository_id`. Graph traversal strictly operates within the target repository's code graph container.
- **Metadata Preservation:** Enriches result metadata with `graph_relationship`, `graph_direction`, and `graph_depth`, preserving line locations and symbol names for explainability.
- **Deterministic Candidate Sorting:** Ranks candidates deterministically using `(score DESC, graph_depth ASC, symbol_name ASC, chunk_id ASC)`.
- **Latency Observability:** Measures and reports `preprocessing_latency_ms`, `retrieval_latency_ms`, and `total_latency_ms`.
- **Graph Immutability:** Search execution never mutates node or edge structures in the Phase 3 Code Knowledge Graph.

**Inputs:** Raw query string or `ProcessedQuery`, `repository_id`, optional `top_k`, `language`, `chunk_type`, `file_path`, `commit_sha` filters.  
**Outputs:** `RetrievalResultSet` model containing `ProcessedQuery`, ordered `RetrievalResult` candidates, and latency metrics.


---

### Candidate Fusion (TASK-5E Planned)

**Purpose:** Combine candidate lists from BM25, Vector, and Graph retrievers into a single ranked list using Reciprocal Rank Fusion (RRF).

---

## Configuration

| Parameter | Env Var | Default |
|---|---|---|
| BM25 candidates (k) | `RETRIEVAL_BM25_K` | 20 |
| Vector candidates (k) | `RETRIEVAL_VECTOR_K` | 20 |
| Graph seed depth | `RETRIEVAL_GRAPH_DEPTH` | 2 |
| Graph candidates (k) | `RETRIEVAL_GRAPH_K` | 10 |
| RRF k constant | `RETRIEVAL_RRF_K` | 60 |
| Max context tokens | `RETRIEVAL_MAX_CONTEXT_TOKENS` | 8192 |
| Enable reranker | `RETRIEVAL_RERANKER_ENABLED` | false |
