import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Target, Network, MessageSquare, ChevronLeft, ChevronDown, ChevronRight, AlertCircle, FileCode2 } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import * as api from '../services/api';
import type { ImpactAnalysisResponse, ImpactNode, ImpactPath, SymbolItem } from '../types';

export const ImpactPage: React.FC = () => {
  const { repositoryId, symbolId } = useParams<{ repositoryId?: string; symbolId?: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rootSymbol, setRootSymbol] = useState<SymbolItem | null>(null);
  const [impactData, setImpactData] = useState<ImpactAnalysisResponse | null>(null);

  useEffect(() => {
    if (!repositoryId || !symbolId) {
      setImpactData(null);
      setRootSymbol(null);
      return;
    }

    let mounted = true;
    const controller = new AbortController();

    async function loadImpact() {
      try {
        setLoading(true);
        setError(null);
        const [graphRes, impRes] = await Promise.all([
          api.traverseGraph(symbolId!, 0, controller.signal).catch(() => null),
          api.analyzeImpact(symbolId!, 3, controller.signal)
        ]);
        if (mounted) {
          if (graphRes && graphRes.nodes.length > 0) {
            setRootSymbol(graphRes.nodes.find(n => n.node_id === symbolId) || null);
          }
          setImpactData(impRes);
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load impact analysis');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadImpact();

    return () => {
      mounted = false;
      controller.abort();
    };
  }, [repositoryId, symbolId]);

  const { direct, transitive, maxDepth, nodeNameMap } = useMemo(() => {
    if (!impactData) return { direct: [], transitive: [], maxDepth: 0, nodeNameMap: new Map<string, string>() };
    const directNodes: ImpactNode[] = [];
    const transitiveNodes: ImpactNode[] = [];
    let max = 0;

    const nameMap = new Map<string, string>();
    if (rootSymbol) nameMap.set(rootSymbol.node_id, rootSymbol.name || 'Unnamed');

    for (const node of impactData.impacted_nodes) {
      nameMap.set(node.node_id, node.name || 'Unnamed');

      const depth = Math.round(1 / node.impact_score);
      if (depth > max) max = depth;

      if (depth === 1) {
        directNodes.push(node);
      } else {
        transitiveNodes.push(node);
      }
    }

    return { direct: directNodes, transitive: transitiveNodes, maxDepth: max, nodeNameMap: nameMap };
  }, [impactData, rootSymbol]);

  if (!repositoryId || !symbolId) {
    return (
      <div className="page-content">
        <EmptyState
          title="No Symbol Selected"
          description="Navigate to a symbol to analyze its graph-derived impact radius."
          icon={<Target size={32} strokeWidth={1.5} />}
          action={<Button variant="primary" onClick={() => navigate('/search')}>Go to Search</Button>}
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page-content" aria-busy="true">
        <LoadingState message="Analyzing impact radius..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-content">
        <ErrorState title="Analysis Error" message={error} action={
          <Button onClick={() => window.location.reload()}>Retry</Button>
        } />
      </div>
    );
  }

  if (!impactData) return null;

  return (
    <div className="page-content details-layout" style={{ maxWidth: 'var(--content-max-width)', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 'var(--sp-6)' }}>
      <style>{`
        .impact-hero {
          display: flex;
          flex-direction: column;
          gap: var(--sp-2);
          padding-bottom: var(--sp-4);
          border-bottom: 1px solid var(--border);
        }
        .impact-title-row {
          display: flex;
          align-items: center;
          gap: var(--sp-3);
          flex-wrap: wrap;
        }
        .impact-meta-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: var(--sp-4);
          background-color: var(--bg-surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          padding: var(--sp-4);
        }
        .meta-item {
          display: flex;
          flex-direction: column;
          gap: var(--sp-1);
        }
        .meta-label {
          font-size: var(--text-xs);
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          font-weight: var(--weight-semibold);
        }
        .meta-value {
          font-size: var(--text-sm);
          font-family: var(--font-mono);
          color: var(--text-primary);
        }
        .actions-panel {
          display: flex;
          flex-wrap: wrap;
          gap: var(--sp-3);
          padding-top: var(--sp-4);
          border-top: 1px solid var(--border);
        }
        .impact-section {
          display: flex;
          flex-direction: column;
          gap: var(--sp-4);
        }
        .impact-section h2 {
          font-size: var(--text-base);
          font-weight: var(--weight-semibold);
          color: var(--text-primary);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          border-bottom: 1px solid var(--border);
          padding-bottom: var(--sp-2);
          margin: 0;
        }
        .impact-list {
          display: flex;
          flex-direction: column;
          gap: var(--sp-3);
        }
        .impact-card {
          background-color: var(--bg-surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          padding: var(--sp-4);
          display: flex;
          flex-direction: column;
          gap: var(--sp-3);
        }
        .impact-card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: var(--sp-4);
        }
        .impact-card-title {
          font-family: var(--font-mono);
          font-size: var(--text-sm);
          font-weight: var(--weight-semibold);
          color: var(--accent);
          text-decoration: none;
        }
        .impact-card-title:hover {
          text-decoration: underline;
        }
        .impact-card-meta {
          font-size: var(--text-xs);
          color: var(--text-secondary);
        }
        .path-expand-btn {
          cursor: pointer;
          user-select: none;
          display: inline-flex;
          align-items: center;
          gap: var(--sp-1);
          font-size: var(--text-xs);
          color: var(--text-muted);
          background: none;
          border: none;
          padding: 0;
          font-family: inherit;
        }
        .path-expand-btn:hover {
          color: var(--text-primary);
        }
        .path-view {
          margin-top: var(--sp-3);
          padding: var(--sp-3);
          background-color: var(--bg-body);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          font-family: var(--font-mono);
          font-size: var(--text-xs);
          display: flex;
          flex-direction: column;
          gap: var(--sp-2);
        }
        .path-step-rel {
          display: flex;
          align-items: center;
          color: var(--text-muted);
          margin-left: var(--sp-3);
        }
        .path-node {
          display: flex;
          align-items: center;
          gap: var(--sp-2);
          color: var(--text-primary);
          font-weight: var(--weight-medium);
        }
      `}</style>

      <div style={{ marginBottom: '-var(--sp-2)' }}>
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)} iconLeft={<ChevronLeft size={16} />}>
          Back to Symbol
        </Button>
      </div>

      <header className="impact-hero">
        <div className="impact-title-row">
          <Target size={24} className="text-secondary" />
          <h1 className="text-2xl font-semibold m-0">Impact Analysis</h1>
        </div>

        {rootSymbol ? (
           <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)', marginTop: 'var(--sp-2)' }}>
             <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)', flexWrap: 'wrap' }}>
               <span className="text-base font-mono">{rootSymbol.name}</span>
               <Badge variant="default" className="text-xs uppercase tracking-wider">{rootSymbol.kind}</Badge>
               {rootSymbol.language && <Badge variant="default" className="text-xs">{rootSymbol.language}</Badge>}
             </div>
             <div className="text-xs text-secondary font-mono">{rootSymbol.file_path || 'Unknown location'}</div>
           </div>
        ) : (
           <div className="mt-4 text-sm font-mono text-secondary">{symbolId}</div>
        )}
      </header>

      <section>
        <div className="impact-meta-grid">
          <div className="meta-item">
            <span className="meta-label">Total Impacted</span>
            <span className="meta-value">{impactData.impacted_nodes.length} dependents</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Direct Impact</span>
            <span className="meta-value">{direct.length} symbols</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Transitive Impact</span>
            <span className="meta-value">{transitive.length} symbols</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Maximum Depth</span>
            <span className="meta-value">{maxDepth} {maxDepth === 1 ? 'hop' : 'hops'}</span>
          </div>
        </div>
      </section>

      <section className="actions-panel">
        <Link to={`/symbols/${repositoryId}/${symbolId}`} style={{ textDecoration: 'none' }}>
           <Button iconLeft={<FileCode2 size={16} />}>View Symbol</Button>
        </Link>
        <Link to={`/graph/${repositoryId}/${symbolId}`} style={{ textDecoration: 'none' }}>
           <Button iconLeft={<Network size={16} />}>Open in Graph</Button>
        </Link>
        <Link to={`/chat/${repositoryId}?symbol_id=${symbolId}`} style={{ textDecoration: 'none' }}>
           <Button iconLeft={<MessageSquare size={16} />}>Ask AI</Button>
        </Link>
      </section>

      {impactData.impacted_nodes.length === 0 ? (
        <EmptyState
          title="No Dependent Symbols Found"
          description="This symbol has no graph-derived dependents within the analyzed impact scope."
          icon={<AlertCircle size={32} className="text-secondary" />}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-8)' }}>
          {direct.length > 0 && (
            <ImpactGroup
               title="Direct Impact"
               nodes={direct}
               paths={impactData.paths || []}
               nodeNameMap={nodeNameMap}
               repositoryId={repositoryId}
             />
           )}
           {transitive.length > 0 && (
            <ImpactGroup
               title="Transitive Impact"
               nodes={transitive}
               paths={impactData.paths || []}
               nodeNameMap={nodeNameMap}
               repositoryId={repositoryId}
             />
           )}
        </div>
      )}
    </div>
  );
};

function ImpactGroup({ title, nodes, paths, nodeNameMap, repositoryId }: { title: string, nodes: ImpactNode[], paths: ImpactPath[], nodeNameMap: Map<string, string>, repositoryId: string }) {
  return (
    <section className="impact-section">
       <h2>{title}</h2>
       <div className="impact-list">
         {nodes.map(node => (
           <ImpactCard key={node.node_id} node={node} paths={paths} nodeNameMap={nodeNameMap} repositoryId={repositoryId} />
         ))}
       </div>
    </section>
  );
}

function ImpactCard({ node, paths, nodeNameMap, repositoryId }: { node: ImpactNode, paths: ImpactPath[], nodeNameMap: Map<string, string>, repositoryId: string }) {
  const [expanded, setExpanded] = useState(false);
  const depth = Math.round(1 / node.impact_score);

  // Find a path ending at this node
  const nodePaths = paths?.filter(p => p.target_id === node.node_id) || [];
  const primaryPath = nodePaths.length > 0 ? nodePaths[0] : null;

  return (
    <div className="impact-card">
      <div className="impact-card-header">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-1)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
            <Link to={`/symbols/${repositoryId}/${node.node_id}`} className="impact-card-title">
              {node.name || 'Unnamed'}
            </Link>
            <Badge variant="default" className="text-xs uppercase tracking-wider">{node.kind}</Badge>
          </div>
          <div className="impact-card-meta">
            {node.file_path || 'Unknown location'}
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 'var(--sp-1)' }}>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Depth {depth}</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-1)', marginTop: 'var(--sp-1)', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            {node.categories.map(c => (
              <span key={c} style={{ padding: '0 4px', backgroundColor: 'var(--bg-body)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
                 {c}
              </span>
            ))}
          </div>
        </div>
      </div>

      {primaryPath && primaryPath.steps.length > 0 && (
         <div style={{ marginTop: 'var(--sp-2)', fontSize: 'var(--text-xs)' }}>
           <button className="path-expand-btn" onClick={() => setExpanded(!expanded)}>
             {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
             Why is this impacted?
           </button>
           {expanded && (
             <div className="path-view">
               <div className="path-node">
                 <FileCode2 size={12} className="text-muted" />
                 {nodeNameMap.get(primaryPath.steps[0].target_id) || primaryPath.steps[0].target_id}
               </div>
               {primaryPath.steps.map((step, idx) => (
                 <React.Fragment key={idx}>
                   <div className="path-step-rel">
                     ↓ {step.kind}
                   </div>
                   <div className="path-node">
                     <FileCode2 size={12} className="text-secondary" />
                     {nodeNameMap.get(step.source_id) || step.source_id}
                   </div>
                 </React.Fragment>
               ))}
             </div>
           )}
         </div>
      )}
    </div>
  );
}
