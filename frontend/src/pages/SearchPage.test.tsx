import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { SearchPage } from './SearchPage';
import * as api from '../services/api';
import type { Repository, QueryResponse } from '../types';

vi.mock('../services/api');

const mockRepo: Repository = {
  id: 'repo-1',
  name: 'CodeLens AI',
  source_type: 'github',
  url: 'https://github.com/Adityaaprakash/AI-Code-Understanding-Engine.git',
  local_path: null,
  default_branch: 'main',
  status: 'indexed',
  error_message: null,
  total_loc: 15420,
  created_at: '2026-08-01T10:00:00Z',
  updated_at: '2026-09-06T10:00:00Z',
};

const mockQueryResponse: QueryResponse = {
  repository_id: 'repo-1',
  query: 'auth flow',
  normalized_query: 'auth flow',
  intent: 'CODE_SEARCH',
  results: [
    {
      chunk_id: 'chunk-1',
      file_path: 'backend/auth.py',
      language: 'python',
      score: 0.95,
      rank: 1,
      symbol_name: 'AuthService',
      start_line: 10,
      end_line: 30,
      content: 'class AuthService:\n    def login(self):\n        pass',
    },
    {
      chunk_id: 'chunk-2',
      file_path: 'backend/middleware.py',
      language: 'python',
      score: 0.75,
      rank: 2,
      symbol_name: null,
      start_line: 5,
      end_line: 15,
      content: 'def require_auth():\n    pass',
    }
  ],
  answer: null
};

describe('SearchPage - Full Search Experience', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithRouter = (initialRoute = '/search/repo-1') => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/search" element={<SearchPage />} />
          <Route path="/search/:repositoryId" element={<SearchPage />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('renders a loading state while fetching repository context', () => {
    vi.mocked(api.getRepository).mockReturnValue(new Promise(() => {}));
    renderWithRouter();
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('redirects to the first repo if repositoryId is missing', async () => {
    vi.mocked(api.listRepositories).mockResolvedValue([mockRepo]);
    vi.mocked(api.getRepository).mockResolvedValue(mockRepo);

    renderWithRouter('/search');
    
    await waitFor(() => {
      // The hero subtitle has the repository name
      expect(screen.getByText('CodeLens AI')).toBeInTheDocument();
    });
    
    expect(api.listRepositories).toHaveBeenCalled();
  });

  it('renders search input and empty state initially when there is no query', async () => {
    vi.mocked(api.getRepository).mockResolvedValue(mockRepo);
    renderWithRouter('/search/repo-1');

    await waitFor(() => {
      expect(screen.getByRole('searchbox', { name: /search query/i })).toBeInTheDocument();
    });

    // Check empty state
    expect(screen.getByText('What can you search for?')).toBeInTheDocument();
  });

  it('executes a search when a query is provided via URL parameter', async () => {
    vi.mocked(api.getRepository).mockResolvedValue(mockRepo);
    vi.mocked(api.runQuery).mockResolvedValue(mockQueryResponse);

    renderWithRouter('/search/repo-1?q=auth+flow');

    await waitFor(() => {
      expect(api.runQuery).toHaveBeenCalledWith(
        { query: 'auth flow', repository_id: 'repo-1', top_k: 20, generate_answer: false },
        expect.any(AbortSignal)
      );
    });

    // Verify results rendered
    expect(screen.getByText('Results for "auth flow"')).toBeInTheDocument();
    expect(screen.getByText('AuthService')).toBeInTheDocument();
    expect(screen.getByText('backend/auth.py')).toBeInTheDocument();
    expect(screen.getByText('backend/middleware.py')).toBeInTheDocument();
  });

  it('executes search upon typing and submitting the form', async () => {
    vi.mocked(api.getRepository).mockResolvedValue(mockRepo);
    // initial mount no query
    renderWithRouter('/search/repo-1');
    
    await waitFor(() => {
      expect(screen.getByRole('searchbox', { name: /search query/i })).toBeInTheDocument();
    });

    // setup search mock
    vi.mocked(api.runQuery).mockResolvedValue(mockQueryResponse);
    const user = userEvent.setup();
    const input = screen.getByRole('searchbox', { name: /search query/i });
    
    await user.type(input, 'auth flow{enter}');

    await waitFor(() => {
      expect(api.runQuery).toHaveBeenCalledWith(
        { query: 'auth flow', repository_id: 'repo-1', top_k: 20, generate_answer: false },
        expect.any(AbortSignal)
      );
    });

    expect(screen.getByText('backend/auth.py')).toBeInTheDocument();
  });

  it('handles empty results appropriately', async () => {
    vi.mocked(api.getRepository).mockResolvedValue(mockRepo);
    vi.mocked(api.runQuery).mockResolvedValue({ ...mockQueryResponse, results: [] });

    renderWithRouter('/search/repo-1?q=notfound');

    await waitFor(() => {
      expect(screen.getByText('No results found')).toBeInTheDocument();
    });
  });

  it('handles errors from the API endpoint', async () => {
    vi.mocked(api.getRepository).mockResolvedValue(mockRepo);
    vi.mocked(api.runQuery).mockRejectedValue(new Error('Backend timeout'));

    renderWithRouter('/search/repo-1?q=fail');

    await waitFor(() => {
      expect(screen.getByText('Search Failed')).toBeInTheDocument();
      expect(screen.getByText('Backend timeout')).toBeInTheDocument();
    });
  });
});
