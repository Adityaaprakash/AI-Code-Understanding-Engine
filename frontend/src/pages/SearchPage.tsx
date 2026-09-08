import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import { Search, Loader2, FileCode2, FileText, Network, MessageSquare } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import * as api from '../services/api';
import type { Repository, QueryResponse } from '../types';

export const SearchPage: React.FC = () => {
  const { repositoryId } = useParams<{ repositoryId?: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryParam = searchParams.get('q') || '';

  const [loadingRepo, setLoadingRepo] = useState(true);
  const [repoError, setRepoError] = useState<string | null>(null);
  const [repo, setRepo] = useState<Repository | null>(null);

  const [inputValue, setInputValue] = useState(queryParam);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [queryResponse, setQueryResponse] = useState<QueryResponse | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();

    async function initRepo() {
      try {
        setLoadingRepo(true);
        setRepoError(null);

        const targetId = repositoryId;
        if (!targetId) {
          const repos = await api.listRepositories(controller.signal);
          if (repos.length > 0) {
            navigate(`/search/${repos[0].id}`, { replace: true });
            return;
          } else {
            if (mounted) {
              setRepo(null);
              setLoadingRepo(false);
            }
            return;
          }
        }

        const data = await api.getRepository(targetId, controller.signal);
        if (mounted) {
          setRepo(data);
          setLoadingRepo(false);
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;
        if (mounted) {
          setRepoError(err instanceof Error ? err.message : 'Failed to load repository');
          setLoadingRepo(false);
        }
      }
    }

    initRepo();
    return () => {
      mounted = false;
      controller.abort();
    };
  }, [repositoryId, navigate]);

  useEffect(() => {
    if (!repositoryId || !queryParam) {
      setQueryResponse(null);
      return;
    }

    let mounted = true;
    const controller = new AbortController();

    async function executeSearch() {
      try {
        setIsSearching(true);
        setSearchError(null);
        const resp = await api.runQuery(
          {
            query: queryParam,
            repository_id: repositoryId!,
            top_k: 20,
            generate_answer: false,
          },
          controller.signal
        );
        if (mounted) {
          setQueryResponse(resp);
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;
        if (mounted) {
          setSearchError(err instanceof Error ? err.message : 'Search failed');
        }
      } finally {
        if (mounted) {
          setIsSearching(false);
        }
      }
    }

    executeSearch();

    return () => {
      mounted = false;
      controller.abort();
    };
  }, [repositoryId, queryParam]);

  useEffect(() => {
    setInputValue(queryParam);
  }, [queryParam]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = inputValue.trim();
    if (trimmed) {
      setSearchParams({ q: trimmed });
    } else {
      setSearchParams({});
    }
  };

  const handleClear = () => {
    setInputValue('');
    setSearchParams({});
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  if (loadingRepo) {
    return (
      <div className="page-content" aria-busy="true">
        <LoadingState message="Loading context..." />
      </div>
    );
  }

  if (repoError) {
    return (
      <div className="page-content">
        <ErrorState title="Error" message={repoError} action={
         <Button onClick={() => window.location.reload()}>Retry</Button>
        } />
      </div>
    );
  }

  if (!repo) {
    return (
      <div className="page-content">
        <EmptyState 
           title="No Repositories" 
           description="Please connect a repository before searching." 
           action={<Link to="/repositories"><Button variant="primary">Add Repository</Button></Link>}
        />
      </div>
    );
  }

  return (
    <div className="page-content details-layout" style={{ maxWidth: 'var(--content-max-width)', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 'var(--sp-6)' }}>
      {/* Shared CSS styling for the search input inline to maintain component modularity */}
      <style>{`
        .search-hero {
          display: flex;
          flex-direction: column;
          gap: var(--sp-4);
        }
        .search-form {
          position: relative;
          display: flex;
          align-items: center;
        }
        .search-input-large {
          width: 100%;
          padding: var(--sp-3) var(--sp-10) var(--sp-3) calc(var(--sp-4) + 24px);
          font-size: var(--text-lg);
          font-family: var(--font-sans);
          color: var(--text-primary);
          background-color: var(--bg-surface);
          border: 1px solid var(--border-strong);
          border-radius: var(--radius-lg);
          transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
        }
        .search-input-large:focus {
          outline: none;
          border-color: var(--border-focus);
          box-shadow: var(--focus-ring);
        }
        .search-input-icon {
          position: absolute;
          left: var(--sp-4);
          color: var(--text-muted);
          pointer-events: none;
        }
        .search-clear-btn {
          position: absolute;
          right: var(--sp-2);
          background: transparent;
          border: none;
          color: var(--text-muted);
          padding: var(--sp-1) var(--sp-2);
          cursor: pointer;
          font-size: var(--text-sm);
          font-weight: var(--weight-medium);
          border-radius: var(--radius-md);
        }
        .search-clear-btn:hover {
          color: var(--text-primary);
          background: var(--bg-hover);
        }
        .search-result-item {
          display: flex;
          flex-direction: column;
          gap: var(--sp-2);
          padding: var(--sp-4);
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          background-color: var(--bg-surface);
        }
        .search-result-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: var(--sp-4);
        }
        .search-result-title {
          font-size: var(--text-md);
          font-weight: var(--weight-semibold);
          color: var(--accent);
          display: flex;
          align-items: center;
          gap: var(--sp-2);
          text-decoration: none;
        }
        .search-result-title:hover {
          text-decoration: underline;
        }
        .search-result-meta {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: var(--sp-3);
          font-family: var(--font-mono);
          font-size: var(--text-xs);
          color: var(--text-secondary);
        }
        .search-result-content {
          font-family: var(--font-mono);
          font-size: var(--text-sm);
          background-color: var(--bg-elevated);
          padding: var(--sp-3);
          border-radius: var(--radius-sm);
          overflow-x: auto;
          color: var(--text-primary);
          border-left: 2px solid var(--border-strong);
        }
      `}</style>

      <header className="search-hero">
        <div>
          <h1 className="text-2xl font-semibold m-0" style={{ marginBottom: 'var(--sp-1)' }}>Search</h1>
          <p className="text-secondary text-sm m-0">Searching within <span className="font-medium text-primary">{repo.name}</span></p>
        </div>
        
        <form onSubmit={handleSubmit} className="search-form" role="search">
          <Search className="search-input-icon" size={20} aria-hidden="true" />
          <input
            ref={inputRef}
            type="search"
            className="search-input-large"
            placeholder="Search classes, functions, or natural language concepts..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isSearching}
            aria-label="Search query"
          />
          {inputValue && (
            <button type="button" className="search-clear-btn" onClick={handleClear} aria-label="Clear search">
              ESC
            </button>
          )}
        </form>
      </header>

      {isSearching && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 'var(--sp-10)' }} aria-busy="true">
          <Loader2 className="loading-spinner text-muted" size={32} />
          <p className="text-muted text-sm" style={{ marginTop: 'var(--sp-4)' }}>Retrieving code structure and context...</p>
        </div>
      )}

      {!isSearching && searchError && (
        <ErrorState title="Search Failed" message={searchError} />
      )}

      {!isSearching && !searchError && !queryResponse && !queryParam && (
        <EmptyState 
           title="What can you search for?" 
           description="Enter concepts like 'authentication flow', symbol names like 'UserService', or file paths to explore the codebase."
           icon={<Search size={32} strokeWidth={1.5} />}
        />
      )}

      {!isSearching && !searchError && queryResponse && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 className="text-base font-medium m-0">Results for "{queryResponse.query}"</h2>
            <div className="text-xs text-muted font-mono" style={{ display: 'flex', gap: 'var(--sp-3)' }}>
              <span>Intent: {queryResponse.intent}</span>
            </div>
          </div>

          {queryResponse.results.length === 0 ? (
            <EmptyState title="No results found" description="Try a different query or a broader concept." />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
              {queryResponse.results.map((item, index) => (
                <div key={item.chunk_id || index} className="search-result-item">
                  <div className="search-result-header">
                    {item.symbol_id ? (
                      <Link to={`/symbols/${queryResponse.repository_id}/${item.symbol_id}`} className="search-result-title">
                        <FileCode2 size={16} />
                        {item.symbol_name || (item.file_path.split('/').pop() || item.file_path)}
                      </Link>
                    ) : (
                      <div className="search-result-title" style={{ cursor: 'default', textDecoration: 'none' }}>
                        <FileCode2 size={16} />
                        {item.symbol_name || (item.file_path.split('/').pop() || item.file_path)}
                      </div>
                    )}
                    <Badge variant={item.score > 0.8 ? 'success' : 'default'}>
                      Rank #{item.rank}
                    </Badge>
                  </div>
                  
                  <div className="search-result-meta">
                    <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-1)' }}>
                      <FileText size={12} /> {item.file_path}
                    </span>
                    {item.start_line && item.end_line && (
                      <span>Lines {item.start_line}-{item.end_line}</span>
                    )}
                    {item.language && <span>{item.language}</span>}
                    <span>Score: {item.score.toFixed(3)}</span>
                  </div>

                  {item.content && (
                    <pre className="search-result-content">
                      <code>{item.content}</code>
                    </pre>
                  )}
                  
                  <div style={{ display: 'flex', gap: 'var(--sp-2)', marginTop: 'var(--sp-2)' }}>
                     {item.symbol_name && (
                       <Link to={`/graph/${queryResponse.repository_id}/${item.symbol_id}`} style={{ textDecoration: 'none' }}>
                         <Button size="sm" variant="ghost" iconLeft={<Network size={14} />}>Explore Graph</Button>
                       </Link>
                     )}
                     <Link to={`/chat/${queryResponse.repository_id}?symbol_id=${item.symbol_id || ''}`} style={{ textDecoration: 'none' }}>
                       <Button size="sm" variant="ghost" iconLeft={<MessageSquare size={14} />}>Ask AI</Button>
                     </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
