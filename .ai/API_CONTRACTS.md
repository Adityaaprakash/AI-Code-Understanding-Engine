# API Contracts — AI Code Understanding Engine

> **Status:** Contracts documented. Implementation deferred to Phases 2–8.
>
> Base URL: `http://localhost:8000/api/v1` (configurable via env var)  
> All request and response bodies are JSON (`application/json`).  
> All timestamps are ISO 8601 UTC strings.  
> All IDs are UUIDs.

---

## Common Response Shapes

### Error Response
```json
{
  "error": "Human-readable error message",
  "code": "MACHINE_READABLE_CODE"
}
```

HTTP status codes:
- `400` — Bad request / validation error
- `404` — Resource not found
- `409` — Conflict (e.g., repository already exists)
- `422` — Unprocessable entity (FastAPI validation)
- `500` — Internal server error

### Paginated Response
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

---

## Repositories

### `POST /api/v1/repositories`

Register a new repository for indexing.

**Request:**
```json
{
  "name": "my-service",
  "source_type": "github",
  "url": "https://github.com/org/repo",
  "default_branch": "main"
}
```

`source_type` is `"github"` or `"local"`.  
For `"local"`, provide `"local_path"` instead of `"url"`.

**Response:** `201 Created`
```json
{
  "id": "a1b2c3d4-...",
  "name": "my-service",
  "source_type": "github",
  "url": "https://github.com/org/repo",
  "default_branch": "main",
  "status": "pending",
  "total_loc": null,
  "created_at": "2026-08-25T12:00:00Z",
  "updated_at": "2026-08-25T12:00:00Z"
}
```

**Errors:** `400` if neither `url` nor `local_path` is provided. `409` if the
repository (by URL or path) already exists.

---

### `GET /api/v1/repositories/{id}`

Retrieve repository metadata.

**Response:** `200 OK`
```json
{
  "id": "a1b2c3d4-...",
  "name": "my-service",
  "source_type": "github",
  "url": "https://github.com/org/repo",
  "default_branch": "main",
  "status": "indexed",
  "total_loc": 42000,
  "last_indexed_at": "2026-08-25T12:05:00Z",
  "created_at": "2026-08-25T12:00:00Z",
  "updated_at": "2026-08-25T12:05:00Z"
}
```

**Errors:** `404` if not found.

---

### `POST /api/v1/repositories/{id}/index`

Trigger a (re-)indexing job for a repository.

**Request:** _(empty body or optional payload)_
```json
{
  "force_full": false
}
```
`force_full: true` forces a full re-index even if an incremental index is possible.

**Response:** `202 Accepted`
```json
{
  "job_id": "d4e5f6...",
  "kind": "incremental_index",
  "status": "pending",
  "scheduled_at": "2026-08-25T12:06:00Z"
}
```

**Errors:** `404` if repository not found. `409` if an indexing job is already
running for this repository.

---

### `GET /api/v1/repositories/{id}/index-status`

Poll the current indexing status of a repository.

**Response:** `200 OK`
```json
{
  "repository_id": "a1b2c3d4-...",
  "status": "indexing",
  "current_job": {
    "id": "d4e5f6...",
    "kind": "full_index",
    "status": "running",
    "started_at": "2026-08-25T12:06:05Z",
    "attempts": 1
  },
  "last_successful_index": {
    "id": "b2c3d4...",
    "commit_sha": "abc123",
    "files_indexed": 512,
    "symbols_indexed": 8400,
    "chunks_indexed": 3200,
    "created_at": "2026-08-24T09:00:00Z"
  }
}
```

**Errors:** `404` if repository not found.

---

## Query

### `POST /api/v1/query`

Submit a natural-language question about an indexed repository.

**Request:**
```json
{
  "repository_id": "a1b2c3d4-...",
  "question": "Which services call the UserRepository.findByEmail method?",
  "max_results": 5,
  "include_sources": true
}
```

**Response:** `200 OK`
```json
{
  "answer": "The following services call UserRepository.findByEmail: ...",
  "sources": [
    {
      "chunk_id": "c1d2e3...",
      "file_path": "src/services/AuthService.java",
      "start_line": 42,
      "end_line": 58,
      "symbol_qualified_name": "com.example.AuthService.login",
      "relevance_score": 0.91,
      "content_excerpt": "userRepository.findByEmail(email)"
    }
  ],
  "retrieval_stats": {
    "bm25_candidates": 12,
    "vector_candidates": 15,
    "graph_candidates": 4,
    "final_context_tokens": 3200
  },
  "latency_ms": 3450
}
```

**Errors:** `404` if repository not found. `400` if repository is not yet indexed.

---

## Symbols

### `GET /api/v1/symbols/{id}`

Retrieve a symbol by its ID.

**Response:** `200 OK`
```json
{
  "id": "s1s2s3...",
  "repository_id": "a1b2c3d4-...",
  "qualified_name": "com.example.UserRepository.findByEmail",
  "simple_name": "findByEmail",
  "kind": "method",
  "language": "java",
  "file_path": "src/repositories/UserRepository.java",
  "start_line": 15,
  "end_line": 22,
  "signature": "public Optional<User> findByEmail(String email)",
  "doc_comment": "Finds a user by their email address."
}
```

**Errors:** `404` if not found.

---

### `GET /api/v1/symbols/{id}/dependencies`

Return symbols that this symbol directly depends on (outgoing edges).

**Query params:** `kind` (optional, filter by edge kind), `depth` (optional, default 1)

**Response:** `200 OK`
```json
{
  "symbol_id": "s1s2s3...",
  "depth": 1,
  "dependencies": [
    {
      "symbol": { "id": "...", "qualified_name": "...", "kind": "method" },
      "relationship_kind": "call",
      "source_line": 18
    }
  ]
}
```

---

### `GET /api/v1/symbols/{id}/dependents`

Return symbols that depend on this symbol (incoming edges — who calls/uses this?).

**Query params:** `kind` (optional), `depth` (optional, default 1)

**Response:** `200 OK`
```json
{
  "symbol_id": "s1s2s3...",
  "depth": 1,
  "dependents": [
    {
      "symbol": { "id": "...", "qualified_name": "...", "kind": "method" },
      "relationship_kind": "call",
      "source_line": 42
    }
  ]
}
```

---

## Impact Analysis

### `POST /api/v1/impact-analysis`

Given a symbol, compute the blast radius: all symbols that would be affected
if this symbol's signature or behaviour changed.

**Request:**
```json
{
  "symbol_id": "s1s2s3...",
  "max_depth": 3
}
```

**Response:** `200 OK`
```json
{
  "root_symbol": {
    "id": "s1s2s3...",
    "qualified_name": "com.example.UserRepository.findByEmail"
  },
  "affected_symbols": [
    {
      "symbol": { "id": "...", "qualified_name": "...", "kind": "method" },
      "depth": 1,
      "path": ["s1s2s3...", "..."]
    }
  ],
  "total_affected": 14,
  "affected_files": [
    "src/services/AuthService.java",
    "src/services/ProfileService.java"
  ]
}
```

**Errors:** `404` if symbol not found.

---

## System

### `GET /health`

_(Not versioned — lives at root)_

**Response:** `200 OK`
```json
{ "status": "ok" }
```

---

## Notes for Implementation

- All IDs in path parameters are validated as UUIDs; return `422` on invalid format.
- The `retrieval_stats` field in the query response is informational and may be
  omitted in production (controlled by a feature flag or env var).
- The `depth` parameter in dependency/impact endpoints must be capped server-side
  to prevent runaway graph traversals (suggested max: `5`).
- Pagination (`page` / `page_size`) is required on any list endpoint that can
  return unbounded results.
