import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ImpactPage } from './ImpactPage';
import * as api from '../services/api';
import type { GraphTraversalResponse, ImpactAnalysisResponse } from '../types';

vi.mock('../services/api');

const mockGraphResponse: GraphTraversalResponse = {
  source_node_id: 'node-auth',
  depth: 0,
  nodes: [
    {
      node_id: 'node-auth',
      name: 'AuthService',
      qualified_name: 'src.auth.AuthService',
      kind: 'CLASS',
      file_path: 'src/auth/service.ts',
      start_line: 10,
      end_line: 50,
      language: 'typescript'
    }
  ],
  edges: []
};

const mockImpactResponse: ImpactAnalysisResponse = {
  source_node_id: 'node-auth',
  depth: 3,
  impacted_nodes: [
    {
      node_id: 'node-login',
      name: 'LoginController',
      qualified_name: 'src.auth.LoginController',
      kind: 'CLASS',
      file_path: 'src/auth/login.ts',
      start_line: 5,
      end_line: 25,
      language: 'typescript',
      impact_score: 1.0, // depth 1
      categories: ['USES', 'CALLS']
    },
    {
      node_id: 'node-router',
      name: 'AppRouter',
      qualified_name: 'src.router.AppRouter',
      kind: 'CLASS',
      file_path: 'src/router.ts',
      start_line: 10,
      end_line: 45,
      language: 'typescript',
      impact_score: 0.5, // depth 2
      categories: ['CALLS']
    }
  ],
  total_impact_score: 2,
  paths: [
    {
      target_id: 'node-login',
      depth: 1,
      node_ids: ['node-auth', 'node-login'],
      steps: [
        { source_id: 'node-login', target_id: 'node-auth', kind: 'USES' }
      ]
    },
    {
      target_id: 'node-router',
      depth: 2,
      node_ids: ['node-auth', 'node-login', 'node-router'],
      steps: [
        { source_id: 'node-login', target_id: 'node-auth', kind: 'USES' },
        { source_id: 'node-router', target_id: 'node-login', kind: 'CALLS' }
      ]
    }
  ]
};

describe('ImpactPage - Impact Analysis Engine', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithRouter = (initialRoute: string) => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/impact" element={<ImpactPage />} />
          <Route path="/impact/:repositoryId/:symbolId" element={<ImpactPage />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('renders an empty state if no symbol is selected', () => {
    renderWithRouter('/impact');
    expect(screen.getByText('No Symbol Selected')).toBeInTheDocument();
  });

  it('renders a loading state while fetching impact data', () => {
    vi.mocked(api.analyzeImpact).mockReturnValue(new Promise(() => {})); // Never resolves
    vi.mocked(api.traverseGraph).mockReturnValue(new Promise(() => {}));
    renderWithRouter('/impact/repo-1/node-auth');
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders an error state if the API fails', async () => {
    vi.mocked(api.analyzeImpact).mockRejectedValue(new Error('Network disconnected'));
    vi.mocked(api.traverseGraph).mockRejectedValue(new Error('Network disconnected'));
    renderWithRouter('/impact/repo-1/node-auth');

    await waitFor(() => {
      expect(screen.getByText('Analysis Error')).toBeInTheDocument();
      expect(screen.getByText('Network disconnected')).toBeInTheDocument();
    });
  });

  it('renders symbol metadata correctly without fabricating', async () => {
    vi.mocked(api.analyzeImpact).mockResolvedValue(mockImpactResponse);
    vi.mocked(api.traverseGraph).mockResolvedValue(mockGraphResponse);
    renderWithRouter('/impact/repo-1/node-auth');

    await waitFor(() => {
      // Top level node
      expect(screen.getByText('AuthService')).toBeInTheDocument();
      // Transitive meta item
      expect(screen.getAllByText('Transitive Impact').length).toBeGreaterThan(0);
    });
  });

  it('distinguishes direct and transitive impact accurately', async () => {
    vi.mocked(api.analyzeImpact).mockResolvedValue(mockImpactResponse);
    vi.mocked(api.traverseGraph).mockResolvedValue(mockGraphResponse);
    renderWithRouter('/impact/repo-1/node-auth');

    await waitFor(() => {
      expect(screen.getAllByText('Direct Impact').length).toBeGreaterThan(0);
      expect(screen.getByText('LoginController')).toBeInTheDocument();
    });

    expect(screen.getByText('AppRouter')).toBeInTheDocument();
    
    // Depth labels
    expect(screen.getByText('Depth 1')).toBeInTheDocument();
    expect(screen.getByText('Depth 2')).toBeInTheDocument();
    
    // Check edge kinds from categories
    expect(screen.getByText('USES')).toBeInTheDocument();
  });

  it('expands and renders impact path evidence correctly', async () => {
    vi.mocked(api.analyzeImpact).mockResolvedValue(mockImpactResponse);
    vi.mocked(api.traverseGraph).mockResolvedValue(mockGraphResponse);
    renderWithRouter('/impact/repo-1/node-auth');

    await waitFor(() => {
      expect(screen.getByText('LoginController')).toBeInTheDocument();
    });

    // LoginController is first card, AppRouter is second. Both have "Why is this impacted?".
    const expandButtons = screen.getAllByRole('button', { name: /Why is this impacted\?/i });
    expect(expandButtons.length).toBe(2);

    // Expand AppRouter path (transitive)
    fireEvent.click(expandButtons[1]);

    // Graph UI inference mapping uses names mapped in the UI map, so it should resolve names properly
    await waitFor(() => {
      // Verify node names in the path trace
      const traces = screen.getAllByText('↓ USES');
      expect(traces.length).toBeGreaterThan(0);
    });
  });

  it('renders empty impact state when zero impact is found', async () => {
    vi.mocked(api.analyzeImpact).mockResolvedValue({
      source_node_id: 'node-auth',
      depth: 3,
      impacted_nodes: [],
      total_impact_score: 0,
      paths: []
    });
    vi.mocked(api.traverseGraph).mockResolvedValue(mockGraphResponse);
    
    renderWithRouter('/impact/repo-1/node-auth');

    await waitFor(() => {
      expect(screen.getByText('No Dependent Symbols Found')).toBeInTheDocument();
    });
  });
});
