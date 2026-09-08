import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ChatPage } from './ChatPage';
import * as api from '../services/api';
import type { QueryResponse } from '../types';

vi.mock('../services/api');

const mockQueryResponse: QueryResponse = {
  repository_id: 'test-repo',
  query: 'How does auth work?',
  normalized_query: 'how auth work',
  intent: 'Concept explanation',
  results: [
    {
      chunk_id: 'chunk-auth-123',
      file_path: 'src/auth/service.ts',
      language: 'typescript',
      score: 12.5,
      rank: 1,
      symbol_id: 'sym-auth-service',
      symbol_name: 'AuthService',
      start_line: 10,
      end_line: 50,
    }
  ],
  answer: {
    answer_text: 'The auth service uses JWT. See [CTX:chunk-auth-123] for details.\n\n```typescript\nclass AuthService {}\n```',
    intent: 'EXPLAIN',
    overall_status: 'Fully Supported',
    supported_claims: 1,
    total_claims: 1,
    generation_latency_ms: 1500,
    metadata: {}
  }
};

describe('ChatPage - Ask AI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithRouter = (initialRoute: string) => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/chat/:repositoryId" element={<ChatPage />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('renders a prompt to select a repository when accessed without repository ID', () => {
    renderWithRouter('/chat');
    expect(screen.getByText('Ask AI')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Select Repository/i })).toBeInTheDocument();
  });

  it('renders chat interface when repository ID is provided', () => {
    renderWithRouter('/chat/repo-123');
    expect(screen.getByText('repo-123')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Ask a question about this codebase/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Send message/i })).toBeDisabled();
  });

  it('rejects whitespace-only input and disables the send button', async () => {
    const user = userEvent.setup();
    renderWithRouter('/chat/repo-123');
    const input = screen.getByPlaceholderText(/Ask a question about this codebase/i);
    
    await user.type(input, '   ');
    expect(screen.getByRole('button', { name: /Send message/i })).toBeDisabled();
  });

  it('submits a valid query and renders loading state', async () => {
    const user = userEvent.setup();
    // Delay resolution to check loading state
    let resolveApi: (value: QueryResponse) => void;
    vi.mocked(api.runQuery).mockReturnValue(new Promise((resolve) => {
       resolveApi = resolve;
    }));

    renderWithRouter('/chat/repo-123');
    const input = screen.getByPlaceholderText(/Ask a question about this codebase/i);
    
    await user.type(input, 'How does auth work?');
    await user.click(screen.getByRole('button', { name: /Send message/i }));

    expect(screen.getByText('How does auth work?')).toBeInTheDocument();
    expect(screen.getByText('Analyzing the codebase...')).toBeInTheDocument();
    
    expect(api.runQuery).toHaveBeenCalledWith({
      query: 'How does auth work?',
      repository_id: 'repo-123',
      top_k: 10,
      generate_answer: true
    });
    
    // Resolve manually to cleanup
    resolveApi!(mockQueryResponse);
  });

  it('renders grounded answer safely with citations and markdown', async () => {
    const user = userEvent.setup();
    vi.mocked(api.runQuery).mockResolvedValue(mockQueryResponse);

    renderWithRouter('/chat/test-repo');
    const input = screen.getByPlaceholderText(/Ask a question about this codebase/i);
    
    await user.type(input, 'How does auth work?{enter}');

    // Wait for the AI message
    await waitFor(() => {
      // "The auth service uses JWT. See " is rendered normally
      expect(screen.getByText(/The auth service uses JWT/)).toBeInTheDocument();
    });

    // Code block rendered properly
    expect(screen.getByText('typescript')).toBeInTheDocument();
    expect(screen.getByText('class AuthService {}')).toBeInTheDocument();

    // Verify citation rendering and linking
    const citationBadge = screen.getByText('[1]');
    expect(citationBadge).toBeInTheDocument();
    expect(citationBadge.closest('a')).toHaveAttribute('href', '/symbols/test-repo/sym-auth-service');

    // Source summary section renders
    expect(screen.getByText('src/auth/service.ts')).toBeInTheDocument();
    expect(screen.getByText('10-50')).toBeInTheDocument();
    
    // Status badges
    expect(screen.getByText('Fully Supported')).toBeInTheDocument();
    expect(screen.getByText('1 / 1 Claims Grounded')).toBeInTheDocument();
  });

  it('renders an ErrorMessage on API failure locally without breaking whole app', async () => {
    const user = userEvent.setup();
    vi.mocked(api.runQuery).mockRejectedValue(new Error('LLM Provider Timed Out'));

    renderWithRouter('/chat/test-repo');
    const input = screen.getByPlaceholderText(/Ask a question about this codebase/i);
    
    await user.type(input, 'What connects to SQL?{enter}');

    await waitFor(() => {
      expect(screen.getByText(/Error communicating with backend: LLM Provider Timed Out/i)).toBeInTheDocument();
    });
  });

  it('pre-populates message text when a symbol_id is provided from Symbol Explorer', () => {
    renderWithRouter('/chat/test-repo?symbol_id=node-payment-service');
    expect(screen.getByText('Explain how the symbol node-payment-service works.')).toBeInTheDocument();
    // Expect send button to be instantly enabled
    expect(screen.getByRole('button', { name: /Send message/i })).not.toBeDisabled();
  });
});
