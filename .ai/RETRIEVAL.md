# Retrieval Architecture — AI Code Understanding Engine

> **Status:** Architecture documented. Implementation deferred to Phase 6.

---

## Overview

The retrieval engine answers the question: *given a natural-language query,
which code chunks and symbols are most relevant?*

A single retrieval path (e.g., pure vector similarity) is insufficient for code.
CodeLens AI uses three parallel retrieval paths, fuses their results, and then
prunes to a token budget before passing to the LLM.

---

## Pipeline Diagram

```
                    User Query (natural language)
                           │
                    ┌──────▼──────┐
                    │  Embedding  │  EmbeddingClient → query vector
                    └──────┬──────┘
                           │ (query text + query vector)
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──────┐  ┌──────▼──────┐  ┌─────▼───────┐
   │    BM25     │  │   Vector    │  │    Graph    │
   │  Retriever  │  │  Retriever  │  │  Retriever  │
   └──────┬──────┘  └──────┬──────┘  └─────┬───────┘
          │                │                │
          └────────────────┼────────────────┘
                           │ Candidate lists (chunk_id, score)
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

### BM25 Lexical Index (TASK-4D Implemented)

**Purpose:** Exact and near-exact keyword search — symbol names, qualified names, method signatures, file paths, and identifiers.

**Implementation:** Pure, deterministic, code-aware `BM25LexicalIndex` operating on `LexicalDocument` abstractions derived from `CodeChunk` contracts.

**Key Architecture Features:**
- **Code-Aware Tokenizer (`CodeTokenizer`):** Preserves original full identifiers (case-folded) while splitting camelCase, PascalCase, snake_case, SCREAMING_SNAKE_CASE, acronyms (`JWT`), qualified names (`com.example.Service`), and file paths (`src/auth/AuthService.java`).
- **Field Weighting (`LexicalTextBuilder`):** Symbol name (3.0x), qualified name (3.0x), file path (2.0x), signature (2.0x), doc comments (1.5x), and content (1.0x).
- **BM25 Formula:** Standard Robertson-Spärck Jones BM25 algorithm ($k_1=1.5, b=0.75$) with Inverse Document Frequency (IDF) +1 smoothing.
- **Repository Isolation (`RepositoryBM25Index`):** Repository data structures are isolated per `repository_id`.
- **Deterministic Tie-Breaking:** Candidate ranking sorts by `score` descending, breaking ties with `chunk_id` ascending.
- **Contract Boundary:** Exposes `LexicalIndexContract` with `add`, `add_many`, `remove`, `clear`, `search`, and `document_count`.

**Inputs:** Raw query string, `repository_id`, optional `top_k`, `language`, `chunk_type` filters  
**Outputs:** List of `LexicalSearchResult` models  

**Why it matters:** Dense vector embeddings often struggle with exact identifier matches. The BM25 lexical index guarantees reliable, deterministic precision for symbol, API, and file path searches.

---

### Vector Retriever

**Purpose:** Semantic similarity — retrieves code that is conceptually related
to the query even when the exact term is not present.

**Implementation:** pgvector cosine similarity on the `chunks.embedding` column.

**Inputs:** Query embedding vector  
**Outputs:** List of `(chunk_id, cosine_similarity)`  
**PostgreSQL query pattern:**
```sql
SELECT id, 1 - (embedding <=> :query_vector) AS score
FROM chunks
WHERE repository_id = :repo_id
ORDER BY embedding <=> :query_vector
LIMIT :k;
```

**Index:** `ivfflat` with `vector_cosine_ops`. Tune `lists` parameter based on
chunk count. Switch to `HNSW` if recall degrades.

---

### Graph Retriever

**Purpose:** Structural relevance — given an initially matched symbol, retrieve
its callers, callees, implementations, and overriders.

**Implementation:** BFS/DFS traversal of `symbol_edges` in PostgreSQL.
Uses a recursive CTE or application-level iteration.

**Inputs:** Set of seed symbol IDs from BM25/vector results  
**Outputs:** List of `(chunk_id, graph_distance)` for structurally adjacent symbols

**Why it matters:** If the user asks about `UserService.createUser`, the relevant
context includes `UserRepository.save` (callee) and `AuthController.register`
(caller) — symbols that may not appear in the nearest-neighbour embedding results.

**PostgreSQL query pattern (1-hop):**
```sql
-- Callers (incoming edges)
SELECT DISTINCT c.id AS chunk_id, 1 AS graph_distance
FROM symbol_edges se
JOIN symbols s ON s.id = se.source_id
JOIN chunks c ON c.symbol_id = s.id
WHERE se.target_id = ANY(:seed_symbol_ids)
  AND se.kind IN ('call', 'import')
LIMIT :k;
```

---

### Candidate Fusion

**Purpose:** Combine the three candidate lists into a single ranked list.

**Algorithm:** Reciprocal Rank Fusion (RRF):
```
RRF_score(d) = Σ_{r ∈ retrievers} 1 / (k + rank_r(d))
```
Default `k = 60`. Documents not retrieved by a path receive no contribution
from that path.

**Why RRF:** RRF is robust to score scale differences between BM25 and vector
similarity, requires no learned weights, and consistently outperforms simple
score averaging in hybrid retrieval benchmarks.

---

### Reranking (Optional)

**Purpose:** Cross-encoder reranking of the top-N fused candidates for higher
precision before passing to the LLM.

**Status:** Optional in MVP. If query latency budget allows, a small
cross-encoder model (e.g., `ms-marco-MiniLM-L-6-v2`) can be run locally.

**Input:** Top-N fused candidates + query text  
**Output:** Re-scored, re-ordered candidate list

---

### Graph Expansion

**Purpose:** After fusion and reranking, expand the context by adding
structurally related symbols (1–2 hops) that provide necessary context
for the LLM to reason fully.

**Example:** If `AuthService.login` is the top result, also include
`UserRepository.findByEmail` (callee) and `JWTService.generateToken` (callee)
even if they scored lower, because the LLM needs them to answer correctly.

**Token budget:** Expansion is capped by the context pruning step.

---

### Context Pruning

**Purpose:** Trim the final context to fit within the LLM's token budget.

**Strategy:**
1. Rank all included chunks by their final score.
2. Include chunks greedily until `MAX_CONTEXT_TOKENS` is reached.
3. For each included chunk, include its surrounding lines as context window.
4. Attach symbol metadata (qualified name, file path, line range) to each chunk
   for the LLM to use as citations.

**Default `MAX_CONTEXT_TOKENS`:** 8192 (configurable via env var).

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

---

## Quality Targets

| Metric | Target | Measurement |
|---|---|---|
| MRR@10 | ≥ 0.75 | Evaluation benchmark (Phase 10) |
| Recall@10 | ≥ 0.85 | Evaluation benchmark (Phase 10) |
| Query P95 latency | ≤ 8 s end-to-end | Performance profiling (Phase 10) |

---

## Implementation Notes

- All three retrievers run concurrently (Python `asyncio.gather`).
- Retrieval is always scoped to a single `repository_id`; there is no
  cross-repository retrieval in MVP.
- The `retrieval_stats` field in the API response exposes candidate counts
  from each path for debugging and monitoring.
