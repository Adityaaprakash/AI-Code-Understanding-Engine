import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { SymbolsPage } from './SymbolsPage';
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

describe('SymbolsPage - Symbol Explorer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithRouter = (initialRoute: string) => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/symbols" element={<SymbolsPage />} />
          <Route path="/symbols/:repositoryId/:symbolId" element={<SymbolsPage />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('renders an empty state if no symbol is selected', () => {
    renderWithRouter('/symbols');
    expect(screen.getByText('No Symbol Selected')).toBeInTheDocument();
  });

  it('renders a loading state while fetching symbol data', () => {
    vi.mocked(api.traverseGraph).mockReturnValue(new Promise(() => {})); // Never resolves
    renderWithRouter('/symbols/repo-1/node-auth-service');
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders an error state if the API fails', async () => {
    vi.mocked(api.traverseGraph).mockRejectedValue(new Error('Network disconnected'));
    renderWithRouter('/symbols/repo-1/node-auth-service');

    await waitFor(() => {
      expect(screen.getByText('Error resolving symbol')).toBeInTheDocument();
      expect(screen.getByText('Network disconnected')).toBeInTheDocument();
    });
  });

  it('renders symbol metadata and root node gracefully', async () => {
    vi.mocked(api.traverseGraph).mockResolvedValue(mockGraphResponse);
    renderWithRouter('/symbols/repo-1/node-auth-service');

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('AuthService');
    });

    // Check metadata
    expect(screen.getByText(/src\/auth\/service\.ts/i)).toBeInTheDocument();
    expect(screen.getByText(/10 - 50/i)).toBeInTheDocument();
  });

  it('renders relationships accurately', async () => {
    vi.mocked(api.traverseGraph).mockResolvedValue(mockGraphResponse);
    renderWithRouter('/symbols/repo-1/node-auth-service');

    await waitFor(() => {
      // The relationship group "Calls" should be present
      expect(screen.getByText(/Calls/i, { selector: 'h3' })).toBeInTheDocument();
    });

    // Verify related node rendering
    expect(screen.getByText('UserRepository')).toBeInTheDocument();
    expect(screen.getByText('src/db/repo.ts')).toBeInTheDocument();
  });

  it('renders a not found state if symbol doesn\'t exist in graph results', async () => {
    vi.mocked(api.traverseGraph).mockResolvedValue({
      source_node_id: 'unknown-id',
      depth: 1,
      nodes: [], // missed node
      edges: []
    });
    renderWithRouter('/symbols/repo-1/unknown-id');

    await waitFor(() => {
      expect(screen.getByText('Symbol Not Found')).toBeInTheDocument();
      expect(screen.getByText(/Could not locate symbol ID: unknown-id/i)).toBeInTheDocument();
    });
  });

});
