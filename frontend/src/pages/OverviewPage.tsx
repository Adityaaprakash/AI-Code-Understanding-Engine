import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Github, FolderGit2, RefreshCw, AlertCircle } from 'lucide-react';
import { Panel } from '../components/ui/Panel';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { StatusIndicator } from '../components/ui/StatusIndicator';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import * as api from '../services/api';
import type { Repository, Job } from '../types';
import { WorkflowShowcase } from '../components/ui/WorkflowShowcase';

export const OverviewPage: React.FC = () => {
  const { repositoryId } = useParams<{ repositoryId?: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [repo, setRepo] = useState<Repository | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  
  const [indexingState, setIndexingState] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');

  // Load repository based on route
  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();

    async function load() {
      try {
        setLoading(true);
        setError(null);
        
        const targetId = repositoryId;
        
        if (!targetId) {
          const repos = await api.listRepositories(controller.signal);
          if (repos.length > 0) {
            navigate(`/overview/${repos[0].id}`, { replace: true });
            return;
          } else {
            if (mounted) {
              setRepo(null);
              setLoading(false);
            }
            return;
          }
        }

        const data = await api.getRepository(targetId, controller.signal);
        if (mounted) setRepo(data);

        const statusData = await api.getIndexStatus(targetId, controller.signal);
        if (mounted) setJobs(statusData);

      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;
        if (mounted) setError(err instanceof Error ? err.message : 'Failed to load repository');
      } finally {
        if (mounted) setLoading(false);
      }
    }

    load();

    return () => {
      mounted = false;
      controller.abort();
    };
  }, [repositoryId, navigate]);

  const handleReindex = useCallback(async () => {
    if (!repo) return;
    setIndexingState('loading');
    try {
      const job = await api.indexRepository(repo.id);
      setJobs((prev) => [job, ...prev]);
      setRepo((prev) => prev ? { ...prev, status: 'indexing' } : null);
      setIndexingState('success');
    } catch {
      setIndexingState('error');
    }
  }, [repo]);

  if (loading) {
    return (
      <div className="page-content" aria-busy="true">
        <LoadingState message="Loading repository..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-content">
        <ErrorState title="Error Loading Repository" message={error} action={
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
           description="Connect a GitHub repository or local path to get started." 
           action={<Link to="/repositories"><Button variant="primary">Add Repository</Button></Link>}
        />
      </div>
    );
  }

  const isGithub = repo.source_type === 'github';
  const SourceIcon = isGithub ? Github : FolderGit2;
  const recentJob = jobs[0];

  return (
    <div className="page-content">
       <header style={{ marginBottom: 'var(--sp-6)' }} aria-label="Repository Header">
         <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)', marginBottom: 'var(--sp-2)' }}>
            <SourceIcon size={24} className="text-muted" aria-hidden="true" />
            <h1 className="text-2xl font-semibold" style={{ margin: 0 }}>{repo.name}</h1>
            <Badge variant={repo.status === 'indexed' ? 'success' : repo.status === 'error' ? 'error' : 'default'}>
              {repo.status.toUpperCase()}
            </Badge>
         </div>
         <p className="text-secondary font-mono text-sm">
           {repo.url || repo.local_path} • {repo.default_branch}
         </p>
       </header>

       <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--sp-4)', marginBottom: 'var(--sp-6)' }}>
          <Panel title="Index Status">
             <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)', height: '100%' }}>
               <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                  <StatusIndicator status={repo.status === 'indexed' ? 'online' : repo.status === 'error' ? 'offline' : 'pending'} />
                  <span className="font-medium text-md" style={{ textTransform: 'capitalize' }}>{repo.status}</span>
               </div>
               
               {recentJob && (
                 <div className="text-sm text-secondary">
                   <p>Last index attempt: {new Date(recentJob.scheduled_at).toLocaleString()}</p>
                   {recentJob.error_message && <p className="text-error" style={{ marginTop: 'var(--sp-1)' }}>{recentJob.error_message}</p>}
                 </div>
               )}

               <div style={{ marginTop: 'auto', paddingTop: 'var(--sp-2)' }}>
                 <Button 
                   variant="primary" 
                   onClick={handleReindex} 
                   loading={indexingState === 'loading' || repo.status === 'indexing' || repo.status === 'cloning'}
                   disabled={indexingState === 'loading' || repo.status === 'indexing' || repo.status === 'cloning'}
                   iconLeft={<RefreshCw size={14} />}
                   aria-label="Re-index repository"
                 >
                   Re-index Repository
                 </Button>
                 {indexingState === 'error' && (
                   <p className="text-error text-xs" style={{ marginTop: 'var(--sp-2)' }} role="alert">
                     Failed to trigger indexing.
                   </p>
                 )}
               </div>
             </div>
          </Panel>

          <Panel title="Repository Details">
            <dl style={{ display: 'grid', gridTemplateColumns: '100px 1fr', gap: 'var(--sp-2) var(--sp-4)', margin: 0 }}>
              <dt className="text-muted text-sm">Source</dt>
              <dd className="text-sm font-medium" style={{ textTransform: 'capitalize' }}>{repo.source_type}</dd>
              
              <dt className="text-muted text-sm">Branch</dt>
              <dd className="font-mono text-sm">{repo.default_branch}</dd>
              
              <dt className="text-muted text-sm">Added</dt>
              <dd className="text-sm">{new Date(repo.created_at).toLocaleDateString()}</dd>
              
              <dt className="text-muted text-sm">Updated</dt>
              <dd className="text-sm">{new Date(repo.updated_at).toLocaleDateString()}</dd>
              
              {repo.error_message && (
                <>
                  <dt className="text-muted text-sm">Error</dt>
                  <dd className="text-error text-sm" style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-1)' }}>
                     <AlertCircle size={14} aria-hidden="true" /> {repo.error_message}
                  </dd>
                </>
              )}
            </dl>
          </Panel>
          
          <Panel title="Metrics">
             {repo.total_loc !== null ? (
               <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <span className="text-muted text-sm">Total Lines of Code</span>
                  <span className="text-3xl font-semibold" style={{ marginTop: 'var(--sp-2)' }}>
                    {repo.total_loc.toLocaleString()}
                  </span>
               </div>
             ) : (
                <EmptyState title="No metrics" description="Repository must be indexed to compute metrics." />
             )}
          </Panel>
       </div>

       <WorkflowShowcase repositoryId={repo.id} />
    </div>
  );
};
