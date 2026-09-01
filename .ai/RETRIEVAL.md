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

### Candidate Fusion Service (`CandidateFusionEngine`) (TASK-5E Implemented & Hardened)

**Purpose:** Hybrid retrieval fusion layer — merges independent candidate lists from Lexical (BM25), Vector (Semantic), and Graph (Structural) retrievers into a single, deterministic, deduplicated candidate set using Reciprocal Rank Fusion (RRF).

**Implementation:** Pure, deterministic `CandidateFusionEngine` implementing `CandidateFusionContract`.

**Key Architecture Features:**
- **Reciprocal Rank Fusion (RRF):** Calculates rank-based fusion score using $RRF(c) = \sum_{s \in S} \frac{1}{k + rank_s(c)}$ with configurable smoothing constant $k$ (default $k=60$). Raw scores from retrievers are never directly added or normalized.
- **Canonical Candidate Identity & Deduplication:** Merges candidates strictly by canonical `chunk_id`. Multiple occurrences of a chunk across branches accumulate RRF contributions into a single fused candidate.
- **Source Evidence Preservation:** Each fused candidate retains complete provenance evidence:
  - `sources`: List of branch sources that retrieved it (`[RetrievalSource.BM25, RetrievalSource.VECTOR, RetrievalSource.GRAPH]`).
  - `bm25_rank`, `vector_rank`, `graph_rank`: 1-indexed ranks from respective retrievers.
  - `bm25_score`, `vector_score`, `graph_score`: Raw scores from respective retrievers.
  - `fused_score`: Total accumulated RRF score (also mirrored in `score`).
- **Single & Multi-Source Eligibility:** Candidates retrieved by only 1 branch remain fully eligible and survive fusion alongside multi-source candidates.
- **100% Deterministic Tie-Breaking:** Candidate ranking strictly sorts by `(fused_score DESC, chunk_id ASC)`. Results are 100% repeatable regardless of dict/set iteration or branch execution order.
- **Strict Boundary Isolation & Validation:**
  - **Repository Isolation:** Input result sets MUST belong to the same repository. Conflicting `repository_id` values raise `FusionRepositoryError`.
  - **Version Isolation:** Conflicting `commit_sha` values across result sets raise `FusionVersionError`.
  - **Query Consistency:** Result sets MUST correspond to the same query text. Conflicting queries raise `FusionQueryError`.
  - **Parameter Safety:** `top_k <= 0` or `rrf_k <= 0` raise `FusionQueryError`.
- **Latency & Observability:** Measures `fusion_latency_ms` and computes `total_latency_ms = max(upstream_total_latencies) + fusion_latency_ms`.
- **Immutability & Safety:** Inputs and candidate objects are never mutated. No external network or LLM calls are executed during fusion.

**Inputs:** `lexical_results`, `vector_results`, `graph_results` (`RetrievalResultSet | None`), `top_k: int = 10`.  
**Outputs:** Fused `RetrievalResultSet` model containing unified `ProcessedQuery`, ordered fused `RetrievalResult` candidates with source evidence, total match counts, and latency metrics.


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
