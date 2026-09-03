# Phase 7 UI Architecture & Contract Audit

## 1. Phase 7 Objective
The objective of Phase 7 is to design and implement the product UI & showcase for the AI Code Understanding Engine. This involves building a responsive, developer-focused frontend that exposes the capabilities achieved in Phases 1-6 (AST Parsing, Graph, Indexing, Retrieval, and Grounded Answering). The architecture must rely strictly on available backend contracts and establish a clean, aesthetic React application shell capable of exploring codebases, navigating code graphs, searching dependencies, and answering codebase queries with fully grounded citations.

## 2. Current Frontend Architecture (ACTUAL)
- **Framework:** React 18.3.1
- **Build Tool:** Vite 6.0.5
- **Language:** TypeScript 5.6.2
- **Styling:** Vanilla CSS (`index.css` exists), no Tailwind or CSS-in-JS framework installed.
- **Routing:** NOT PRESENT. (No react-router-dom or similar installed).
- **State Management:** NOT PRESENT. (No Redux, Zustand, React Query installed).
- **API/Client Layer:** NOT PRESENT.
- **Icons:** `lucide-react` is installed.
- **Components:** Empty directory structure (`src/components/`, `src/hooks/`, `src/pages/`, `src/services/`, `src/types/`).
- **Tests:** No testing framework installed for the frontend (no Jest/Vitest/Cypress). 
- **Linting & Formatting:** ESLint 9 and Prettier installed and configured natively via `eslint.config.js`. 

## 3. Current Backend/API Architecture Relevant to UI (ACTUAL)
- **Framework:** FastAPI
- **Routers:** The application mounts `api_v1_router` under `API_V1_STR` but it currently contains NO business logic endpoints.
- **Health Check:** `GET /health` mapped in `main.py`.
- **Root Ping:** `GET /api/v1/` or `GET /api/v1` returning `{ "status": "active" }` is the only route defined in `backend/api/v1/router.py`.
- **Conclusion:** There are **NO EXPOSED ENDPOINTS** for any Phase 2-6 functionalities. The backend has the underlying mechanisms (database, LLM services, graph nodes) but has not mapped them to a REST boundary for the frontend.

## 4. API Contract Inventory
| METHOD | PATH | REQUEST | RESPONSE | STATUS / SOURCE |
| --- | --- | --- | --- | --- |
| GET | `/health` | None | `HealthResponse(status="ok")` | ACTIVELY EXPOSED (`backend/main.py`) |
| GET | `/api/v1/` | None | `{message, status, version}` | ACTIVELY EXPOSED (`api/v1/router.py`) |

**NO OTHER ENDPOINTS EXIST.**

## 5. Phase 7 Feature/API Matrix

| Feature | Frontend Requirement | Existing Backend Support | Endpoint | Missing Contract | Notes |
| --- | --- | --- | --- | --- | --- |
| **7A Repository Dashboard** | List repos, show indexing status | Database models (`Repository`, `Job`) exist. | MISSING | `GET /api/v1/repositories` | Blocked until API is exposed |
| **7B Codebase Chat** | Send queries, get grounded answers | Pipeline exists in `llm/` | MISSING | `POST /api/v1/chat/ask` | Blocked until API is exposed |
| **7C Symbol Explorer** | Fetch symbol context and source | API `backend/api/v1/symbols.py` exists | ACTIVELY EXPOSED | None | Ready for Frontend |
| **7D Graph Visualization** | Fetch nodes & edges | API `backend/api/v1/graph.py` exists | ACTIVELY EXPOSED | None | Ready for Frontend |
| **7E Impact Analysis** | Calculate impact radius | API `backend/api/v1/impact.py` exists | ACTIVELY EXPOSED | None | Ready for Frontend |
| **7F Search** | BM25/Vector RRF search | `candidate_fusion` exists | MISSING | `GET /api/v1/search?q={query}` | Blocked until API is exposed |
| **7G UI Polish** | N/A | N/A | READY | N/A | Purely Frontend |
| **7H Showcase Flow** | Deterministic demo flow data | Needs repository ingestion APIs | MISSING | Repository Injection APIs | Blocked until API is exposed |
| **7I Frontend Testing** | Component/E2E tests | N/A | MISSING | Cypress / Vitest | Setup required |

## 6. Phase 6 Frontend Contract (Context Assembly & Grounded Answering)
While API endpoints do not exist, the internal models dictating the future contract are:
- **Query Definition:** `QueryIntent` (e.g. EXPLANATION, DEPENDENCY).
- **Answer Output:** `GeneratedAnswer` containing `answer_text`, `query`, `intent`, `provider_name`, `metadata`, etc.
- **Grounding/Citation:** 
  - `CitationReference`: Extracted marker strings representing cited items, mapped to `CitationStatus`.
  - `GroundingClaim`: Specific factual claims, mapping to `support_context_ids`, evaluated into a `ClaimStatus` (e.g., supported, partially_supported).
  - `GroundingVerificationResult`: Comprehensive output packing metrics (claims, coverage) and `GroundingStatus`.
- **Gap:** These internal structures lack a unified REST wrapper merging Chat and Grounding into an asynchronous streaming response or single comprehensive REST response. 

## 7. Phase 5 Retrieval Frontend Contract
Available internal structures corresponding to what the frontend should visualize:
- **Retrieval Engine:** `CodeChunk` and `CodeChunkCollection`.
- **Exposed Meta:** A `CodeChunk` provides `chunk_type`, `repository_id`, `file_path`, `language`, `source_location`, `content`, `signature`, and `doc_comment`.
- **Search Metadata:** Fusion algorithms are present (`retrieval/enums.py` defines `RetrievalSource.BM25`, `VECTOR`, `GRAPH`), allowing explanations of whence a chunk originated.

## 8. Graph Contract
Actual Implementation models from `graph/models.py`:
- **Nodes (`GraphNode`):** Identifiable via `id` and `kind` (e.g., REPOSITORY, FILE, CLASS, FUNCTION).
- **Edges (`GraphEdge`):** Directional (`source_id`, `target_id`) typed via `EdgeKind` (e.g., CALLS, EXPORTS, IMPLEMENTS, READS, WRITES) and `ResolutionStatus`.
- **Graph Containers (`CodeGraph`):** Supports `get_neighbors`, `get_outbound_edges`, etc.
- **Frontend Strategy:** A graph endpoint should serialize `CodeGraph.to_dict()` focused on a defined origin node up to `N` layers deep to prevent massive payload over-fetching.

## 9. Repository/Indexing Contract
Actual implementation in Postgres (`backend/db/models/repository.py` and `job.py`):
- **Repository:** Fields include `id`, `name`, `source_type` (`github` or `local`), `url`, `local_path`, `default_branch`, `status` (`pending`, `cloning`, `indexing`, `indexed`, `error`, `stale`), `error_message`, and `total_loc`.
- **Job (Indexing):** Represents indexing states with `kind` (`full_index`, `incremental_index`) and `status` (`pending`, `running`, `done`, `failed`).
- **Frontend Application:** The UI must display repository status based on these exact enums. No custom enums should be invented.

## 10. Frontend Domain Models (Recommended)
Map directly to the backend Pydantic/SQLAlchemy abstractions via typed TS interfaces:
```typescript
type RepositoryStatus = 'pending' | 'cloning' | 'indexing' | 'indexed' | 'error' | 'stale';

interface Repository {
  id: string;
  name: string;
  url?: string;
  localPath?: string;
  status: RepositoryStatus;
  errorMessage?: string;
  totalLoc?: number;
}

interface CodeChunk {
  id: string;
  chunkType: string;
  filePath: string;
  language: string;
  name?: string;
  signature?: string;
  content: string;
  sourceLocation: { startLine: number; endLine: number; };
}

interface GroundedAnswer {
  answerId: string;
  answerText: string;
  verificationResult: {
    overallStatus: 'supported' | 'partially_supported' | 'unsupported' | 'unverifiable';
    metrics: any;
    claims: any[];
  }
}
```

## 11. API Client Architecture (Recommended)
UI -> Custom React Hooks (`useRepository`, `useChat`, `useGraph`) -> Strongly Typed REST API Client (`services/api.ts`) -> Fetch -> FastAPI.
- Implement central error normalization and Axios/Fetch instance configuration to handle timeouts.
- Standardize a `LoadingState` interface (`idle`, `loading`, `success`, `error`).
- Use signal-based cancellation (AbortController) for chat generation and graph fetching.

## 12. Frontend Routing Architecture (Recommended)
Suggested setup using `react-router-dom`:
- Layout: `/` (Redirects to `/repositories`)
- `/repositories` — Dashboard of repositories (7A)
- `/repositories/:repoId/search` — Search interface (7F)
- `/repositories/:repoId/chat` — Codebase Chat (7B)
- `/repositories/:repoId/symbol/:symbolId` — Symbol explorer (7C)
- `/repositories/:repoId/graph/:nodeId?` — Graph Explorer (7D) & Impact (7E)

## 13. Application Shell (Recommended)
A neutral-toned, dual-panel or side-navigated layout:
- **Sidebar (Left):** Repository switcher, Navigation (Overview, Semantic Search, Chat, Graph Explorer).
- **Main Content (Center/Right):** The primary data view (Search Results, Code Viewer, Graph Canvas).
- **Status Bar (Bottom):** Repository Indexing Status, active model, latency metrics, DB connection state.

## 14. UI Information Architecture
Avoid isolated pages. Navigation should be densely connected:
1. Search queries return `CodeChunk` results.
2. Clicking a `CodeChunk` navigates to the Symbol Explorer.
3. Symbol Explorer provides links to "View in Graph" (Graph Route) and "Check Dependents" (Impact Analysis).
4. Graph interactions allow right-clicking nodes to jump into "Ask AI about this entity" (Chat Route).

## 15. Navigation Relationships
- **Chunk → Symbol:** 1:1 logical shift.
- **Symbol → Graph:** Explores dependencies visually.
- **Chat Citation → Source View:** Inline expandable view or quick-jump to file/line.
- **Graph Node → Chat:** Passes node context ID into chat session.

## 16. Visual Design Principles
- Minimalist, developer-tool aesthetic inspired by modern IDEs and tools like Linear/GitHub.
- **Tone:** Professional, monotone background (blacks/dark grays) with high-contrast accent colors strictly used for syntax highlighting or primary actions.
- Avoid glowing effects, excess glassmorphism, or AI consumer-grade UI. Code legibility is the absolute priority.

## 17. Design System
- **Typography:** Sans-serif for UI (e.g., Inter, system-ui), Monospace for code (e.g., Fira Code, JetBrains Mono).
- **Colors:** Deep dark mode default. Semantic colors for statuses (Green = Indexed, Yellow = Indexing, Red = Error).
- **Components:** Basic implementations of `Button`, `Input`, `Card` (for citations), `Badge` (for `ChunkType`), `Dialog`.
- All developed minimally in vanilla CSS mapping to CSS variables (e.g. `--color-bg-primary`).

## 18. UI State Architecture
Consistent union state mapping for asynchronous views:
- `LOADING`: Skeleton loaders reproducing the shape of the data.
- `EMPTY`: Meaningful minimal explanation (e.g., "No repositories indexed yet. Connect one.").
- `SUCCESS`: Render component.
- `ERROR`: Neutral, non-alarming error cards with action to retry.

## 19. Accessibility Strategy
- High contrast syntax highlighting (WCAG AA).
- Keyboard navigable symbol lists and search result pagination.
- Meaningful ARIA labels on graph nodes and chat inputs.
- Focus rings for accessibility explicitly maintained via CSS `:focus-visible`.

## 20. Responsive Strategy
Desktop-first priority.
The workspace assumes wide aspect ratios to fit Code Graph canvases alongside sidebars. On tablet/smaller viewports, gracefully collapse sidebars to hamburger menus or bottom sheets, but do not compromise the code space.

## 21. Security Considerations
- Ensure internal pipeline metrics (internal LLM system prompts, raw budget calculations) aren't leaked to users directly unless purposefully included in explainability cards.
- Sanitize rendered Markdown inside Chat output to prevent DOM XSS.
- Ensure any Local File path rendering mitigates path traversal exposure.

## 22. Performance Considerations
- **Virtualized Lists:** Necessary for Search Results and Symbol Lists if displaying 100+ entities.
- **Graph Rendering:** Prefer HTML/SVG over Canvas if node counts stay < 100 on screen; evaluate `react-flow-renderer` or similar lightweight libraries, falling back to Canvas for dense architectures.
- **Memoization:** Wrap complex syntax highlighting rendering in `React.memo`.

## 23. Testing Architecture
- Recommended test stack: `vitest` + `@testing-library/react` for components.
- Essential end-to-end journey relies on UI interactions corresponding to Phase 7A -> Phase 7D (import repo, search, open graph, ask).
- No frontend testing infrastructure exists today; it must be implemented (Phase 7I).

## 24. Showcase Flow (Target Simulation)
1. **Import:** Add the 'World Cup Simulation Engine'.
2. **Dashboard:** Status transitions from `pending` -> `indexed`.
3. **Search:** Search for "MatchEngine" highlighting semantic results.
4. **Symbol:** Open `MatchEngine` code chunk. 
5. **Graph:** Explore its `calls` and `overrides` edges.
6. **Chat:** Ask "How does a match progress from kickoff to final score?" -> View grounded citations dynamically mapping to lines.

## 25. Identified Contract Gaps (CRITICAL)
- **GAP 1:** No FastAPI endpoints expose the Phase 5 Retrieval pipeline (No `GET /api/v1/search`).
- **GAP 2:** No FastAPI endpoints expose the Phase 6 Context Assembly / Answering outputs (No POST `api/v1/chat`).
- **GAP 3:** No FastAPI endpoints expose internal Repository/Job orchestration indexing statuses shown in `db/models`.
- **GAP 4:** No Endpoints expose the CodeGraph querying capabilities. 
The Frontend CANNOT be built functionally until Backend wrapper endpoints are mapped in FASTAPI.

## 26. Recommended Implementation Order
Given the stark missing backend API layer, the order must be modified to build the API boundaries concurrently with their frontend counterparts:

1. **TASK-7A0:** Architecture / contract audit (**COMPLETED**)
2. **TASK-7A1 (New):** Define and implement FastAPI REST schemas and endpoints binding the Phase 2-6 internals to `api/v1/router.py`.
3. **TASK-7G:** UI Polish / Design System foundation (Establish React Shell).
4. **TASK-7A:** Repository Dashboard (Impl + UI integration).
5. **TASK-7F:** Search Experience.
6. **TASK-7C:** Symbol Explorer.
7. **TASK-7D:** Graph Visualization.
8. **TASK-7E:** Impact Analysis.
9. **TASK-7B:** Codebase Chat (Requires highest complexity of UI rendering for citations).
10. **TASK-7H:** Showcase Flow.
11. **TASK-7I:** Testing / Verification.

## 27. Explicit Non-Goals
- Do not implement custom backend ML features.
- Do not create mock backend data to pretend features work; instead, add the real endpoint wrappers.
- Do not add arbitrary bloated CSS frameworks (e.g. Tailwind) since standard DOM mapping dictates vanilla CSS in current `package.json`.
- Do not reinvent the Phase 6 query normalization logic on the frontend.
