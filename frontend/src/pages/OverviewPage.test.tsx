import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { OverviewPage } from './OverviewPage';
import * as api from '../services/api';
import type { Repository, Job } from '../types';

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

const mockJob: Job = {
  id: 'job-1',
  repository_id: 'repo-1',
  kind: 'full_index',
  status: 'done',
  error_message: null,
  attempts: 1,
  scheduled_at: '2026-09-06T10:00:00Z',
  started_at: '2026-09-06T10:00:01Z',
  completed_at: '2026-09-06T10:00:10Z',
};

describe('OverviewPage - Repository Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithRouter = (initialRoute = '/overview/repo-1') => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/overview/:repositoryId" element={<OverviewPage />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('renders loading state initially', () => {
    // Return a never-resolving promise so we can observe the loading state
    vi.mocked(api.getRepository).mockReturnValue(new Promise(() => {}));
    vi.mocked(api.getIndexStatus).mockReturnValue(new Promise(() => {}));

    renderWithRouter();
    expect(screen.getByRole('status', { name: /Loading content/i })).toBeInTheDocument();
  });

  it('redirects to the first repository if no ID is specified in the route', async () => {
    vi.mocked(api.listRepositories).mockResolvedValue([mockRepo]);
    vi.mocked(api.getRepository).mockResolvedValue(mockRepo);
    vi.mocked(api.getIndexStatus).mockResolvedValue([mockJob]);

    renderWithRouter('/overview');
    
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('CodeLens AI');
    });
    
    expect(api.listRepositories).toHaveBeenCalled();
  });

  it('renders empty state if no repositories are connected', async () => {
    vi.mocked(api.listRepositories).mockResolvedValue([]);
    renderWithRouter('/overview');
    
    await waitFor(() => {
      expect(screen.getByText('No Repositories')).toBeInTheDocument();
    });
  });

  it('renders error state on API failure', async () => {
    vi.mocked(api.getRepository).mockRejectedValue(new Error('API failure'));
    renderWithRouter();
    
    await waitFor(() => {
      expect(screen.getByText('Error Loading Repository')).toBeInTheDocument();
    });
  });

  it('renders repository information and indexing status successfully', async () => {
    vi.mocked(api.getRepository).mockResolvedValue(mockRepo);
    vi.mocked(api.getIndexStatus).mockResolvedValue([mockJob]);
    
    renderWithRouter();

    // Verify Repository header
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('CodeLens AI');
    });
    
    expect(screen.getAllByText(/main/i).length).toBeGreaterThan(0);
    expect(screen.getByText('INDEXED')).toBeInTheDocument(); 

    // Verify metrics
    expect(screen.getByText('15,420')).toBeInTheDocument();
    
    // Showcase component instead of Quick action panels
    expect(screen.getByText('Explore CodeLens Intelligence Flow')).toBeInTheDocument();
    expect(screen.getByText('2. Universal Search')).toBeInTheDocument();
    expect(screen.getByText('5. Ask AI Chat')).toBeInTheDocument();
  });

  it('handles re-index action gracefully', async () => {
    vi.mocked(api.getRepository).mockResolvedValue(mockRepo);
    vi.mocked(api.getIndexStatus).mockResolvedValue([mockJob]);
    
    const newJob: Job = { ...mockJob, id: 'job-2', status: 'pending' };
    vi.mocked(api.indexRepository).mockResolvedValue(newJob);
    
    const user = userEvent.setup();
    renderWithRouter();

    const reindexBtn = await screen.findByRole('button', { name: /Re-index repository/i });
    await user.click(reindexBtn);
    
    expect(api.indexRepository).toHaveBeenCalledWith('repo-1');

    await waitFor(() => {
      // optimistic state updates badge wrapper to pending/indexing (INDEXING status)
      expect(screen.getByText('INDEXING')).toBeInTheDocument();
    });
  });
});
