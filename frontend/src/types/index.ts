/**
 * Domain models — aligned with backend Pydantic/SQLAlchemy contracts.
 * Do not invent fields. These map 1:1 to the 7A1 API response schemas.
 */

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
}

// ---------------------------------------------------------------------------
// Repository
// ---------------------------------------------------------------------------

export type RepositoryStatus =
  | 'pending'
  | 'cloning'
  | 'indexing'
  | 'indexed'
  | 'error'
  | 'stale';

export type RepositorySourceType = 'github' | 'local';

export interface Repository {
  id: string;
  name: string;
  source_type: RepositorySourceType;
  url: string | null;
  local_path: string | null;
  default_branch: string;
  status: RepositoryStatus;
  error_message: string | null;
  total_loc: number | null;
  created_at: string;
  updated_at: string;
}

export interface RepositoryCreate {
  name: string;
  source_type: RepositorySourceType;
  url?: string;
  local_path?: string;
  default_branch?: string;
}

// ---------------------------------------------------------------------------
// Job
// ---------------------------------------------------------------------------

export type JobKind = 'full_index' | 'incremental_index';
export type JobStatus = 'pending' | 'running' | 'done' | 'failed';

export interface Job {
  id: string;
  repository_id: string;
  kind: JobKind;
  status: JobStatus;
  error_message: string | null;
  attempts: number;
  scheduled_at: string;
  started_at: string | null;
  completed_at: string | null;
}

// ---------------------------------------------------------------------------
// Symbol / Graph
// ---------------------------------------------------------------------------

export interface SymbolItem {
  node_id: string;
  name: string;
  qualified_name: string;
  kind: string;
  file_path: string | null;
  start_line: number | null;
  end_line: number | null;
  language: string | null;
}

export interface SymbolSearchResponse {
  repository_id: string;
  query: string;
  results: SymbolItem[];
}

export interface GraphEdge {
  source_id: string;
  target_id: string;
  kind: string;
}

export interface GraphTraversalResponse {
  source_node_id: string;
  depth: number;
  nodes: SymbolItem[];
  edges: GraphEdge[];
}

export interface ImpactNode extends SymbolItem {
  impact_score: number;
  categories: string[];
}

export interface ImpactAnalysisResponse {
  source_node_id: string;
  depth: number;
  impacted_nodes: ImpactNode[];
  total_impact_score: number;
}

// ---------------------------------------------------------------------------
// Query / Chat
// ---------------------------------------------------------------------------

export interface QueryRequest {
  query: string;
  repository_id: string;
}

export interface QueryResponse {
  answer: string;
  sources: SourceReference[];
  query_intent: string;
  model: string;
  latency_ms: number;
}

export interface SourceReference {
  chunk_id: string;
  file_path: string;
  start_line: number;
  end_line: number;
  language: string;
  relevance_score: number;
}

// ---------------------------------------------------------------------------
// Async state
// ---------------------------------------------------------------------------

export type AsyncStatus = 'idle' | 'loading' | 'success' | 'error';

export interface AsyncState<T> {
  status: AsyncStatus;
  data: T | null;
  error: string | null;
}

export function idle<T>(): AsyncState<T> {
  return { status: 'idle', data: null, error: null };
}

export function loading<T>(): AsyncState<T> {
  return { status: 'loading', data: null, error: null };
}

export function success<T>(data: T): AsyncState<T> {
  return { status: 'success', data, error: null };
}

export function failure<T>(error: string): AsyncState<T> {
  return { status: 'error', data: null, error };
}
