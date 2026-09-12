# Demo & Showcase Guide

## Phase 9H: Synchronous Demo Mode

To allow for an end-to-end demonstration of the CodeLens AI Engine locally, we have introduced a synchronous indexing path designed explicitly for development and showcase environments.

### Why a Synchronous Path?
In a full production environment, the heavy task of parsing, building the canonical IR, calculating vector embeddings, creating BM25 indices, and extracting Graph vertices and edges is delegated to a separate background worker via asynchronous Jobs.

Currently, the async worker is scaffolded but not processing full production jobs yet. Thus, hitting the standard `POST /api/v1/repositories/{id}/index` endpoint triggers a background job but leaves the runtime in-memory retrieval structures empty.

To bridge this operational gap for reviewers and local testing, a new orchestrator was implemented (`DemoIndexer`) and exposed via the synchronous API endpoint:
`POST /api/v1/repositories/{id}/index-demo`

### Triggering the Demo Mode
1. Start the API backend: `uvicorn backend.main:app --reload`
2. Ensure PostgreSQL is running: `docker-compose -f docker/docker-compose.dev.yml up -d`
3. Add a local repository via the API (`POST /api/v1/repositories`) pointing to a valid source code folder.
4. Hit the demo endpoint with the created UUID:
   ```bash
   curl -X POST http://localhost:8000/api/v1/repositories/<repo_id>/index-demo
   ```
5. Or, test it using the SwaggerUI at `http://localhost:8000/docs`.

### Internal Workings
The `index-demo` orchestrator synchronously executes the existing components:
- Parses source files safely via `PythonParser`, `TypeScriptParser`, and `JavaParser`.
- Generates Canonical IR and resolves imports and symbols.
- Populates the Phase 3 global `InMemoryGraphStore` (`graph_service.store`).
- Runs the AST-aware `CodeChunker`.
- Populates the Phase 4 `BM25LexicalIndex`.
- Computes `VectorIndex` embeddings. The demo explicitly prefers the real semantic provider (`LocalSentenceTransformerProvider` using `all-MiniLM-L6-v2`) for research-grade representation. To ensure development resilience, it falls back to the `DeterministicTestEmbeddingProvider` only if the semantic provider and its dependencies are unavailable in the host environment.

Once indexed, queries like "Where is database connection configured?" or graph traversals will work seamlessly using actual retrieved codebase entities.

### Restrictions & Future Production Scope
This demo mode is **not** meant for large production codebases, as the synchronous HTTP request will block while traversing large directory trees, establishing dependency semantics, and calculating vector embeddings.
Future phases will delegate the exact orchestration payload executed by `DemoIndexer` to the production background Celery task framework (`worker.py`).
