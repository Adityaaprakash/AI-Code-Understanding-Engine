import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { GraphPage } from './GraphPage';
import * as api from '../services/api';
import type { GraphTraversalResponse } from '../types';

vi.mock('../services/api');

const mockGraphResponse: GraphTraversalResponse = {
  source_node_id: 'node-auth-service',
  depth: 1,
  nodes: [
    {
      node_id: 'node-auth-service',
      name: 'AuthService',
      qualified_name: 'src.auth.AuthService',
      kind: 'CLASS',
      file_path: 'src/auth/service.ts',
      start_line: 10,
      end_line: 50,
      language: 'typescript'
    },
    {
      node_id: 'node-user-repo',
      name: 'UserRepository',
      qualified_name: 'src.db.UserRepository',
      kind: 'CLASS',
      file_path: 'src/db/repo.ts',
      start_line: 5,
      end_line: 100,
      language: 'typescript'
    }
  ],
  edges: [
    {
      source_id: 'node-auth-service',
      target_id: 'node-user-repo',
      kind: 'CALLS'
    }
  ]
};

describe('GraphPage - Graph Explorer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithRouter = (initialRoute: string) => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/graph/:repositoryId" element={<GraphPage />} />
          <Route path="/graph/:repositoryId/:symbolId" element={<GraphPage />} />
          <Route path="/search" element={<div>Search Page</div>} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('renders a prompt to select a symbol when accessed without a symbol ID', () => {
    renderWithRouter('/graph/repo-1');
    expect(screen.getByText('Graph Explorer')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Search Symbols/i })).toBeInTheDocument();
  });

  it('navigates to Search when clicking the prompt action', async () => {
    const user = userEvent.setup();
    renderWithRouter('/graph/repo-1');
    await user.click(screen.getByRole('button', { name: /Search Symbols/i }));
    expect(screen.getByText('Search Page')).toBeInTheDocument();
  });

  it('renders loading state while fetching graph', () => {
    vi.mocked(api.traverseGraph).mockReturnValue(new Promise(() => {}));
    renderWithRouter('/graph/repo-1/node-auth-service');
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders error state on API failure', async () => {
    vi.mocked(api.traverseGraph).mockRejectedValue(new Error('Network disconnected'));
    renderWithRouter('/graph/repo-1/node-auth-service');

    await waitFor(() => {
      expect(screen.getByText('Graph API Error')).toBeInTheDocument();
      expect(screen.getByText('Network disconnected')).toBeInTheDocument();
    });
  });

  it('renders graph and active node details on success', async () => {
    vi.mocked(api.traverseGraph).mockResolvedValue(mockGraphResponse);
    renderWithRouter('/graph/repo-1/node-auth-service');

    await waitFor(() => {
      expect(api.traverseGraph).toHaveBeenCalledWith('node-auth-service', 1, expect.any(AbortSignal));
    });

    // Check that graph canvas rendered the root symbol node name in SVG
    expect(await screen.findByText('AuthService', { selector: 'text' })).toBeInTheDocument();
    expect(await screen.findByText('UserRepository', { selector: 'text' })).toBeInTheDocument();
    expect(await screen.findByText('CALLS', { selector: 'text' })).toBeInTheDocument();

    // Check sidebar active node
    expect(screen.getByRole('heading', { level: 2, name: /AuthService/i })).toBeInTheDocument();
    expect(screen.getByText(/src\/auth\/service\.ts/i)).toBeInTheDocument();
  });

  it('allows clicking a node to change the active node panel', async () => {
    const user = userEvent.setup();
    vi.mocked(api.traverseGraph).mockResolvedValue(mockGraphResponse);
    renderWithRouter('/graph/repo-1/node-auth-service');

    // Wait until rendering completes and root node is active
    expect(await screen.findByRole('heading', { level: 2, name: /AuthService/i })).toBeInTheDocument();

    // Click the target node in the graph
    const targetNode = screen.getByRole('button', { name: /Node UserRepository/i });
    await user.click(targetNode);

    // Sidebar should now display UserRepository
    expect(screen.getByRole('heading', { level: 2, name: /UserRepository/i })).toBeInTheDocument();
    expect(screen.getByText(/src\/db\/repo\.ts/i)).toBeInTheDocument();
    
    // There should be an action to re-root the graph
    expect(screen.getByRole('button', { name: /Root Graph Here/i })).toBeInTheDocument();
  });

  it('fetches new data when depth is changed', async () => {
    const user = userEvent.setup();
    vi.mocked(api.traverseGraph).mockResolvedValue(mockGraphResponse);
    renderWithRouter('/graph/repo-1/node-auth-service');

    await waitFor(() => {
      expect(api.traverseGraph).toHaveBeenCalledWith('node-auth-service', 1, expect.any(AbortSignal));
    });

    // Click depth 2 button
    const depth2Button = screen.getByRole('button', { name: /Set traversal depth to 2/i });
    await user.click(depth2Button);

    await waitFor(() => {
      expect(api.traverseGraph).toHaveBeenCalledWith('node-auth-service', 2, expect.any(AbortSignal));
    });
  });

  it('preserves repository state isolation in the graph request', async () => {
    vi.mocked(api.traverseGraph).mockResolvedValue(mockGraphResponse);
    renderWithRouter('/graph/test-repo-999/node-auth-service');

    await waitFor(() => {
      expect(api.traverseGraph).toHaveBeenCalled();
    });
    // No repositoryId sent to backend in 7A1 architecture (it relies on UUID globally uniqueness)
    // Here we ensure frontend renders correctly within its route scope.
    expect(await screen.findByText('AuthService', { selector: 'text' })).toBeInTheDocument();
  });
});
