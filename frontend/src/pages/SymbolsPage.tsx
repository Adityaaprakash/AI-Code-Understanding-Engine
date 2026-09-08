import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { FileCode2, Network, MessageSquare, Target, ChevronLeft, ArrowRight, ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import * as api from '../services/api';
import type { GraphTraversalResponse, GraphEdge } from '../types';

interface GroupedRelationships {
  label: string;
  edges: GraphEdge[];
  isOutgoing: boolean;
}

export const SymbolsPage: React.FC = () => {
  const { repositoryId, symbolId } = useParams<{ repositoryId?: string; symbolId?: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<GraphTraversalResponse | null>(null);

  useEffect(() => {
    if (!repositoryId || !symbolId) {
      setData(null);
      return;
    }

    let mounted = true;
    const controller = new AbortController();

    async function fetchSymbolDetails() {
      try {
        setLoading(true);
        setError(null);
        // Traverse to depth 1 to get exact symbol details + immediate neighbors
        const resp = await api.traverseGraph(symbolId!, 1, controller.signal);
        if (mounted) {
          setData(resp);
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load symbol details');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    fetchSymbolDetails();

    return () => {
      mounted = false;
      controller.abort();
    };
  }, [repositoryId, symbolId]);

  if (!repositoryId || !symbolId) {
    return (
      <div className="page-content">
        <EmptyState
          title="No Symbol Selected"
          description="Navigate to a symbol from the search results to inspect its metadata and relationships."
          icon={<FileCode2 size={32} strokeWidth={1.5} />}
          action={<Button variant="primary" onClick={() => navigate('/search')}>Go to Search</Button>}
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="page-content" aria-busy="true">
        <LoadingState message="Resolving symbol relationships..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-content">
        <ErrorState title="Error resolving symbol" message={error} action={
         <Button onClick={() => window.location.reload()}>Retry</Button>
        } />
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const rootSymbol = data.nodes.find(n => n.node_id === symbolId);
  if (!rootSymbol) {
    return (
      <div className="page-content">
        <EmptyState
          title="Symbol Not Found"
          description={`Could not locate symbol ID: ${symbolId} in the semantic graph.`}
          action={<Button onClick={() => navigate(-1)} iconLeft={<ChevronLeft size={16} />}>Go Back</Button>}
        />
      </div>
    );
  }

  // Process relationships
  const outgoing = data.edges.filter(e => e.source_id === symbolId);
  const incoming = data.edges.filter(e => e.target_id === symbolId);

  // Helper mapping
  const groupRules: { kind: string; outLabel: string; inLabel: string }[] = [
    { kind: 'CALLS', outLabel: 'Calls', inLabel: 'Called By' },
    { kind: 'IMPORTS', outLabel: 'Imports', inLabel: 'Imported By' },
    { kind: 'EXTENDS', outLabel: 'Extends', inLabel: 'Extended By' },
    { kind: 'IMPLEMENTS', outLabel: 'Implements', inLabel: 'Implemented By' },
    { kind: 'REFERENCES', outLabel: 'References', inLabel: 'Referenced By' },
    { kind: 'DEPENDS_ON', outLabel: 'Depends On', inLabel: 'Dependents' }
  ];

  const grouped: GroupedRelationships[] = [];
  
  groupRules.forEach(rule => {
    const outEdges = outgoing.filter(e => e.kind === rule.kind);
    if (outEdges.length > 0) grouped.push({ label: rule.outLabel, edges: outEdges, isOutgoing: true });

    const inEdges = incoming.filter(e => e.kind === rule.kind);
    if (inEdges.length > 0) grouped.push({ label: rule.inLabel, edges: inEdges, isOutgoing: false });
  });

  // Catch-all for unknown kinds
  const knownKinds = new Set(groupRules.map(r => r.kind));
  const unknownOut = outgoing.filter(e => !knownKinds.has(e.kind));
  if (unknownOut.length > 0) {
    // group by their dynamic kind
    const byKind = new Map<string, GraphEdge[]>();
    unknownOut.forEach(e => {
       const ls = byKind.get(e.kind) || [];
       ls.push(e);
       byKind.set(e.kind, ls);
    });
    byKind.forEach((edges, kind) => grouped.push({ label: `${kind} (Out)`, edges, isOutgoing: true }));
  }

  const unknownIn = incoming.filter(e => !knownKinds.has(e.kind));
  if (unknownIn.length > 0) {
    const byKind = new Map<string, GraphEdge[]>();
    unknownIn.forEach(e => {
       const ls = byKind.get(e.kind) || [];
       ls.push(e);
       byKind.set(e.kind, ls);
    });
    byKind.forEach((edges, kind) => grouped.push({ label: `${kind} (In)`, edges, isOutgoing: false }));
  }

  const getNode = (id: string) => data.nodes.find(n => n.node_id === id);

  return (
    <div className="page-content details-layout" style={{ maxWidth: 'var(--content-max-width)', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 'var(--sp-6)' }}>
      {/* CSS encapsulation */}
      <style>{`
        .symbol-hero {
          display: flex;
          flex-direction: column;
          gap: var(--sp-2);
          padding-bottom: var(--sp-4);
          border-bottom: 1px solid var(--border);
        }
        .symbol-title-row {
          display: flex;
          align-items: center;
          gap: var(--sp-3);
          flex-wrap: wrap;
        }
        .symbol-type-badge {
          text-transform: uppercase;
        }
        .symbol-meta-grid {
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
          word-break: break-all;
        }
        .rel-group {
          margin-bottom: var(--sp-6);
        }
        .rel-group h3 {
          font-size: var(--text-md);
          font-weight: var(--weight-medium);
          margin-top: 0;
          margin-bottom: var(--sp-3);
          display: flex;
          align-items: center;
          gap: var(--sp-2);
          color: var(--text-primary);
        }
        .rel-list {
          display: flex;
          flex-direction: column;
          gap: var(--sp-2);
        }
        .rel-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: var(--sp-3);
          background-color: var(--bg-surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          transition: border-color var(--transition-fast), background-color var(--transition-fast);
          text-decoration: none;
          color: inherit;
        }
        .rel-item:hover {
          border-color: var(--border-focus);
          background-color: var(--bg-hover);
        }
        .rel-symbol-name {
          font-family: var(--font-mono);
          font-size: var(--text-sm);
          font-weight: var(--weight-medium);
          color: var(--accent);
        }
        .rel-symbol-file {
          font-size: var(--text-xs);
          color: var(--text-secondary);
        }
        .actions-panel {
          display: flex;
          flex-wrap: wrap;
          gap: var(--sp-3);
          padding-top: var(--sp-4);
          border-top: 1px solid var(--border);
        }
      `}</style>
      
      <div style={{ marginBottom: '-var(--sp-2)' }}>
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)} iconLeft={<ChevronLeft size={16} />}>
          Back
        </Button>
      </div>

      <header className="symbol-hero">
        <div className="symbol-title-row">
          <FileCode2 size={24} className="text-secondary" />
          <h1 className="text-2xl font-semibold m-0">{rootSymbol.name || 'Unnamed Symbol'}</h1>
          <Badge variant="default" className="symbol-type-badge">{rootSymbol.kind}</Badge>
          {rootSymbol.language && <Badge variant="default">{rootSymbol.language}</Badge>}
        </div>
        <p className="text-sm text-secondary font-mono m-0" style={{ marginTop: 'var(--sp-2)' }}>
          {rootSymbol.qualified_name && rootSymbol.qualified_name !== rootSymbol.name 
            ? rootSymbol.qualified_name 
            : rootSymbol.file_path || 'No Path'}
        </p>
      </header>

      <section>
        <h2 className="text-base font-semibold mb-3 mt-0">Metadata</h2>
        <div className="symbol-meta-grid">
          <div className="meta-item">
            <span className="meta-label">File</span>
            <span className="meta-value">{rootSymbol.file_path || 'Unknown'}</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Lines</span>
            <span className="meta-value">
              {rootSymbol.start_line !== null && rootSymbol.end_line !== null 
                ? `${rootSymbol.start_line} - ${rootSymbol.end_line}` 
                : 'N/A'}
            </span>
          </div>
          <div className="meta-item">
            <span className="meta-label">UUID</span>
            <span className="meta-value text-xs text-muted">{rootSymbol.node_id}</span>
          </div>
        </div>
      </section>

      <section className="actions-panel">
        <Link to={`/graph`} style={{ textDecoration: 'none' }}>
           <Button iconLeft={<Network size={16} />}>View in Graph</Button>
        </Link>
        <Link to={`/impact/${repositoryId}/${symbolId}`} style={{ textDecoration: 'none' }}>
           <Button iconLeft={<Target size={16} />}>Analyze Impact</Button>
        </Link>
        <Link to={`/chat`} style={{ textDecoration: 'none' }}>
           <Button iconLeft={<MessageSquare size={16} />}>Ask AI</Button>
        </Link>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-4 mt-0">Relationships</h2>
        
        {grouped.length === 0 ? (
          <EmptyState 
            title="No Relationships" 
            description="This symbol is isolated or lacks resolvable edges within the knowledge graph." 
          />
        ) : (
          grouped.map((group) => (
            <div key={group.label} className="rel-group">
              <h3>
                {group.label} <Badge variant="default" className="text-xs">{group.edges.length}</Badge>
              </h3>
              <div className="rel-list">
                {group.edges.map(edge => {
                  const targetId = group.isOutgoing ? edge.target_id : edge.source_id;
                  const node = getNode(targetId);
                  
                  if (!node) return null;

                  return (
                    <Link 
                      key={edge.source_id + edge.target_id + edge.kind} 
                      to={`/symbols/${repositoryId}/${node.node_id}`} 
                      className="rel-item"
                    >
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-1)' }}>
                        <span className="rel-symbol-name">
                          {group.isOutgoing && <ArrowRight size={12} style={{ marginRight: '4px', verticalAlign: 'middle', color: 'var(--text-muted)' }} />}
                          {!group.isOutgoing && <ArrowLeft size={12} style={{ marginRight: '4px', verticalAlign: 'middle', color: 'var(--text-muted)' }} />}
                          {node.name || 'Unnamed'}
                        </span>
                        <span className="rel-symbol-file">{node.file_path || 'Unknown origin'}</span>
                      </div>
                      <Badge variant="default" className="text-xs">{node.kind}</Badge>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </section>
    </div>
  );
};
