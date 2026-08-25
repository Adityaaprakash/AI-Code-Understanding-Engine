# Database Schema — AI Code Understanding Engine

> **Status:** Schema documented. Implementation deferred to Phase 2 (Alembic migrations).
>
> Migrations will live in `backend/db/migrations/`.

---

## Extensions Required

```sql
CREATE EXTENSION IF NOT EXISTS vector;   -- pgvector
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- fuzzy text search
```

---

## Entity Overview

```
repositories
    ↓ one-to-many
commits
    ↓ one-to-many
files
    ↓ one-to-many
symbols ──────────────────────→ symbol_edges (graph)
    ↓ one-to-many
chunks ────→ chunk_embeddings (pgvector)

repositories ↓ one-to-many
jobs
index_versions
```

---

## Table Definitions

### `repositories`

Stores metadata about each indexed repository.

```sql
CREATE TABLE repositories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    source_type     TEXT NOT NULL CHECK (source_type IN ('github', 'local')),
    url             TEXT,                   -- GitHub repository URL (nullable for local)
    local_path      TEXT,                   -- Absolute local path (nullable for GitHub)
    default_branch  TEXT NOT NULL DEFAULT 'main',
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'cloning', 'indexing',
                                      'indexed', 'error', 'stale')),
    error_message   TEXT,
    total_loc       BIGINT,                 -- Populated after first index
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### `commits`

Tracks commit SHAs that have been indexed, enabling incremental re-indexing.

```sql
CREATE TABLE commits (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id   UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    sha             TEXT NOT NULL,
    committed_at    TIMESTAMPTZ,
    indexed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (repository_id, sha)
);

CREATE INDEX idx_commits_repository_id ON commits(repository_id);
```

---

### `files`

One row per source file per repository.

```sql
CREATE TABLE files (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id   UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    relative_path   TEXT NOT NULL,
    language        TEXT NOT NULL CHECK (language IN ('java', 'python', 'typescript')),
    content_hash    TEXT NOT NULL,          -- SHA-256 of file content
    loc             INTEGER NOT NULL DEFAULT 0,
    indexed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (repository_id, relative_path)
);

CREATE INDEX idx_files_repository_id ON files(repository_id);
CREATE INDEX idx_files_language ON files(language);
```

---

### `symbols`

One row per named symbol (class, interface, function, method, variable).

```sql
CREATE TABLE symbols (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id   UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    file_id         UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    qualified_name  TEXT NOT NULL,
    simple_name     TEXT NOT NULL,
    kind            TEXT NOT NULL
                    CHECK (kind IN ('class', 'interface', 'function',
                                    'method', 'variable', 'parameter')),
    language        TEXT NOT NULL CHECK (language IN ('java', 'python', 'typescript')),
    start_line      INTEGER NOT NULL,
    end_line        INTEGER NOT NULL,
    doc_comment     TEXT,
    signature       TEXT,                   -- Stringified signature for display
    -- Full-text search
    search_vector   TSVECTOR
                    GENERATED ALWAYS AS (
                        to_tsvector('english',
                            coalesce(qualified_name, '') || ' ' ||
                            coalesce(simple_name, '') || ' ' ||
                            coalesce(doc_comment, ''))
                    ) STORED,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (repository_id, qualified_name)
);

CREATE INDEX idx_symbols_repository_id    ON symbols(repository_id);
CREATE INDEX idx_symbols_file_id          ON symbols(file_id);
CREATE INDEX idx_symbols_kind             ON symbols(kind);
CREATE INDEX idx_symbols_qualified_name   ON symbols USING gin(qualified_name gin_trgm_ops);
CREATE INDEX idx_symbols_search_vector    ON symbols USING gin(search_vector);
```

---

### `symbol_edges`

Directed edges in the symbol relationship graph.

```sql
CREATE TABLE symbol_edges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id   UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    source_id       UUID NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    target_id       UUID NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL
                    CHECK (kind IN ('call', 'import', 'extends',
                                    'implements', 'type_use',
                                    'field_access', 'override')),
    source_line     INTEGER,
    UNIQUE (source_id, target_id, kind)
);

CREATE INDEX idx_symbol_edges_source    ON symbol_edges(source_id);
CREATE INDEX idx_symbol_edges_target    ON symbol_edges(target_id);
CREATE INDEX idx_symbol_edges_repo      ON symbol_edges(repository_id);
```

---

### `chunks`

Retrievable text chunks derived from source files and symbols.

```sql
CREATE TABLE chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id   UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    file_id         UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    symbol_id       UUID REFERENCES symbols(id) ON DELETE SET NULL,
    content         TEXT NOT NULL,          -- Raw chunk text
    start_line      INTEGER NOT NULL,
    end_line        INTEGER NOT NULL,
    token_count     INTEGER NOT NULL,
    -- Full-text search
    search_vector   TSVECTOR
                    GENERATED ALWAYS AS (
                        to_tsvector('english', content)
                    ) STORED,
    -- Vector embedding (added after embedding is computed)
    embedding       VECTOR(1536),           -- Dimension matches EMBEDDING_DIMENSIONS env var
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_chunks_repository_id  ON chunks(repository_id);
CREATE INDEX idx_chunks_file_id        ON chunks(file_id);
CREATE INDEX idx_chunks_symbol_id      ON chunks(symbol_id);
CREATE INDEX idx_chunks_search_vector  ON chunks USING gin(search_vector);
-- Vector index (IVFFlat — tune lists based on dataset size)
CREATE INDEX idx_chunks_embedding      ON chunks USING ivfflat (embedding vector_cosine_ops)
                                        WITH (lists = 100);
```

---

### `jobs`

PostgreSQL-backed job queue for asynchronous indexing work.

```sql
CREATE TABLE jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id   UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL
                    CHECK (kind IN ('full_index', 'incremental_index')),
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'running', 'done', 'failed')),
    payload         JSONB NOT NULL DEFAULT '{}',
    error_message   TEXT,
    attempts        INTEGER NOT NULL DEFAULT 0,
    max_attempts    INTEGER NOT NULL DEFAULT 3,
    scheduled_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for worker polling: pending jobs ordered by scheduled_at
CREATE INDEX idx_jobs_pending ON jobs(scheduled_at)
    WHERE status = 'pending';
```

---

### `index_versions`

Tracks each successful indexing run, enabling rollback and history queries.

```sql
CREATE TABLE index_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id   UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    job_id          UUID NOT NULL REFERENCES jobs(id),
    commit_sha      TEXT NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('full', 'incremental')),
    files_indexed   INTEGER NOT NULL DEFAULT 0,
    symbols_indexed INTEGER NOT NULL DEFAULT 0,
    chunks_indexed  INTEGER NOT NULL DEFAULT 0,
    duration_ms     BIGINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_index_versions_repository_id ON index_versions(repository_id);
```

---

## Notes for Implementation

- All `TIMESTAMPTZ` columns default to `now()` — do not set them in application code.
- `embedding VECTOR(1536)` dimension must match `EMBEDDING_DIMENSIONS` env var.
  If you change the embedding model, create a new migration to ALTER the column.
- The `SELECT FOR UPDATE SKIP LOCKED` pattern for job polling is implemented in
  `backend/services/job_service.py` (Phase 2).
- `search_vector` columns are `GENERATED ALWAYS AS … STORED` — no manual
  tsvector update triggers needed.
