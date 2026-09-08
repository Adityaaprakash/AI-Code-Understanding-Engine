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

export interface ImpactPathStep {
  source_id: string;
  target_id: string;
  kind: string;
  edge_id?: string | null;
}

export interface ImpactPath {
  target_id: string;
  depth: number;
  node_ids: string[];
  steps: ImpactPathStep[];
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
  paths: ImpactPath[];
}

// ---------------------------------------------------------------------------
// Query / Chat
// ---------------------------------------------------------------------------

export interface QueryRequest {
  query: string;
  repository_id: string;
  top_k?: number;
  generate_answer?: boolean;
}

export interface GroundedAnswerResponse {
  answer_text: string;
  intent: string;
  overall_status: string;
  supported_claims: number;
  total_claims: number;
  generation_latency_ms: number;
  metadata: Record<string, unknown>;
}

export interface SearchResultItem {
  chunk_id: string;
  file_path: string;
  language: string;
  score: number;
  rank: number;
  symbol_name?: string | null;
  symbol_id?: string | null;
  start_line?: number | null;
  end_line?: number | null;
  content?: string | null;
}

export interface QueryResponse {
  repository_id: string;
  query: string;
  normalized_query: string;
  intent: string;
  results: SearchResultItem[];
  answer?: GroundedAnswerResponse | null;
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
