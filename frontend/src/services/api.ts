/**
 * API client — strongly typed, fetch-based.
 * Maps to the 7A1 backend REST contracts exactly.
 * No invented endpoints; no fabricated response shapes.
 */

import type {
  GraphTraversalResponse,
  HealthResponse,
  ImpactAnalysisResponse,
  QueryRequest,
  QueryResponse,
  Repository,
  RepositoryCreate,
  SymbolSearchResponse,
} from '../types';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  'http://localhost:8000';

// ---------------------------------------------------------------------------
// Core helpers
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

interface ErrorBody {
  detail?: string;
  error_code?: string;
  message?: string;
}

async function request<T>(
  path: string,
  init?: RequestInit,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    signal,
    ...init,
  });

  if (!response.ok) {
    let code = 'API_ERROR';
    let message = `Request failed: ${response.status}`;
    try {
      const body = (await response.json()) as ErrorBody;
      code = body.error_code ?? code;
      message = body.detail ?? body.message ?? message;
    } catch {
      // non-JSON error body
    }
    throw new ApiError(response.status, code, message);
  }

  // 204 No Content
  if (response.status === 204) return undefined as T;

  return response.json() as Promise<T>;
}

function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>(path, { method: 'GET' }, signal);
}

function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body) }, signal);
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return get<HealthResponse>('/health', signal);
}

// ---------------------------------------------------------------------------
// Repositories
// ---------------------------------------------------------------------------

export function listRepositories(signal?: AbortSignal): Promise<Repository[]> {
  return get<Repository[]>('/api/v1/repositories', signal);
}

export function getRepository(id: string, signal?: AbortSignal): Promise<Repository> {
  return get<Repository>(`/api/v1/repositories/${id}`, signal);
}

export function createRepository(
  payload: RepositoryCreate,
  signal?: AbortSignal,
): Promise<Repository> {
  return post<Repository>('/api/v1/repositories', payload, signal);
}

// ---------------------------------------------------------------------------
// Symbols
// ---------------------------------------------------------------------------

export function searchSymbols(
  repositoryId: string,
  query: string,
  signal?: AbortSignal,
): Promise<SymbolSearchResponse> {
  const params = new URLSearchParams({ repository_id: repositoryId, query });
  return get<SymbolSearchResponse>(`/api/v1/symbols?${params}`, signal);
}

// ---------------------------------------------------------------------------
// Graph
// ---------------------------------------------------------------------------

export function traverseGraph(
  sourceNodeId: string,
  depth = 2,
  signal?: AbortSignal,
): Promise<GraphTraversalResponse> {
  const params = new URLSearchParams({
    source_node_id: sourceNodeId,
    depth: String(depth),
  });
  return get<GraphTraversalResponse>(`/api/v1/graph?${params}`, signal);
}

// ---------------------------------------------------------------------------
// Impact analysis
// ---------------------------------------------------------------------------

export function analyzeImpact(
  sourceNodeId: string,
  depth = 3,
  signal?: AbortSignal,
): Promise<ImpactAnalysisResponse> {
  const params = new URLSearchParams({
    source_node_id: sourceNodeId,
    depth: String(depth),
  });
  return get<ImpactAnalysisResponse>(`/api/v1/impact?${params}`, signal);
}

// ---------------------------------------------------------------------------
// Query / Chat
// ---------------------------------------------------------------------------

export function runQuery(
  payload: QueryRequest,
  signal?: AbortSignal,
): Promise<QueryResponse> {
  return post<QueryResponse>('/api/v1/query', payload, signal);
}
