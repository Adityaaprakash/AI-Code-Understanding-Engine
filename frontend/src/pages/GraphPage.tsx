import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Network, Search, FileCode2, ChevronRight } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import { SimpleGraphCanvas } from '../components/graph/SimpleGraphCanvas';
import * as api from '../services/api';
import type { GraphTraversalResponse } from '../types';

export const GraphPage: React.FC = () => {
  const { repositoryId, symbolId } = useParams<{ repositoryId?: string; symbolId?: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<GraphTraversalResponse | null>(null);
  const [depth, setDepth] = useState<number>(1);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(symbolId || null);

  // Sync route -> local state when route changes
  useEffect(() => {
    if (symbolId) {
      setSelectedNodeId(symbolId);
    }
  }, [symbolId]);

  useEffect(() => {
    if (!repositoryId || !symbolId) {
      setData(null);
      return;
    }

    let mounted = true;
    const controller = new AbortController();

    async function fetchGraph() {
      try {
        setLoading(true);
        setError(null);
        // Using non-null assertion because we verified symbolId up top
        const resp = await api.traverseGraph(symbolId!, depth, controller.signal);
        if (mounted) {
          setData(resp);
          // If previous selection isn't in new graph, select root
          if (selectedNodeId && !resp.nodes.find(n => n.node_id === selectedNodeId)) {
            setSelectedNodeId(symbolId!);
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to fetch graph data');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    fetchGraph();

    return () => {
      mounted = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repositoryId, symbolId, depth]); // Re-run when depth changes

  const handleNodeSelect = (nodeId: string) => {
    setSelectedNodeId(nodeId);
  };

  const activeNode = selectedNodeId && data ? data.nodes.find(n => n.node_id === selectedNodeId) : null;

  if (!repositoryId || !symbolId) {
    return (
      <div className="page-content" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <EmptyState
          title="Graph Explorer"
          description="Select a symbol from the Repository or Search to start exploring its relationships."
          icon={<Network size={40} strokeWidth={1.5} />}
          action={
            <Button variant="primary" onClick={() => navigate('/search')} iconLeft={<Search size={16} />}>
              Search Symbols
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="page-content details-layout" style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 'var(--sp-4)', maxWidth: 'var(--content-max-width)', margin: '0 auto' }}>
      
      {/* Scope specific styles */}
      <style>{`
        .graph-layout {
          display: flex;
          flex-direction: column;
          flex: 1;
          gap: var(--sp-4);
          min-height: 0;
        }
        @media (min-width: 900px) {
          .graph-layout {
            flex-direction: row;
          }
        }
        .graph-main {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: var(--sp-3);
          min-width: 0;
          min-height: 400px;
        }
        .graph-sidebar {
          width: 100%;
          display: flex;
          flex-direction: column;
          gap: var(--sp-4);
          background: var(--bg-surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          padding: var(--sp-4);
          overflow-y: auto;
        }
        @media (min-width: 900px) {
          .graph-sidebar {
            width: 320px;
            flex-shrink: 0;
          }
        }
        .graph-toolbar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: var(--sp-2) var(--sp-4);
          background: var(--bg-surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
        }
        .depth-controls {
          display: flex;
          align-items: center;
          gap: var(--sp-2);
          font-size: var(--text-sm);
        }
        .depth-btn {
          padding: var(--sp-1) var(--sp-2);
          background: transparent;
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          color: var(--text-secondary);
          cursor: pointer;
          transition: all 0.2s;
        }
        .depth-btn:hover {
          border-color: var(--border-focus);
          color: var(--text-primary);
        }
        .depth-btn[data-active="true"] {
          background: var(--bg-hover);
          color: var(--accent);
          border-color: var(--accent);
          font-weight: var(--weight-medium);
        }
        .info-panel-meta {
          display: flex;
          flex-direction: column;
          gap: var(--sp-2);
          margin-top: var(--sp-2);
          margin-bottom: var(--sp-4);
        }
        .info-panel-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .info-label {
          font-size: 10px;
          text-transform: uppercase;
          color: var(--text-muted);
          font-weight: 600;
        }
        .info-value {
          font-size: var(--text-sm);
          color: var(--text-primary);
          word-break: break-all;
        }
      `}</style>
      
      {/* Toolbar */}
      <div className="graph-toolbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', fontWeight: 'var(--weight-semibold)' }}>
          <Network size={18} className="text-secondary" />
          <span>Graph Explorer</span>
        </div>

        <div className="depth-controls">
          <span className="text-muted">Traversal Depth:</span>
          {[1, 2, 3].map(d => (
            <button
              key={d}
              className="depth-btn"
              data-active={depth === d}
              onClick={() => setDepth(d)}
              disabled={loading}
              title={`Graph Depth ${d}`}
              aria-label={`Set traversal depth to ${d}`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      <div className="graph-layout">
        {/* Main Canvas Area */}
        <div className="graph-main">
          {loading ? (
             <LoadingState message="Traversing knowledge graph..." />
          ) : error ? (
             <ErrorState title="Graph API Error" message={error} action={
               <Button onClick={() => window.location.reload()}>Retry</Button>
             } />
          ) : !data || data.nodes.length === 0 ? (
             <EmptyState title="Empty Graph" description="No structural edges found from this root symbol." />
          ) : (
            <SimpleGraphCanvas 
              data={data}
              rootSymbolId={symbolId}
              selectedNodeId={selectedNodeId}
              onNodeSelect={handleNodeSelect}
            />
          )}
        </div>

        {/* Selected Node Sidebar */}
        <div className="graph-sidebar">
           {activeNode ? (
             <>
               <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', flexWrap: 'wrap' }}>
                 <FileCode2 size={20} className="text-accent" />
                 <h2 className="text-lg font-medium m-0" style={{ wordBreak: 'break-all' }}>{activeNode.name || 'Unnamed Symbol'}</h2>
               </div>
               
               <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
                 <Badge variant="default">{activeNode.kind}</Badge>
                 {activeNode.language && <Badge variant="default">{activeNode.language}</Badge>}
               </div>

               <div className="info-panel-meta">
                 <div className="info-panel-item">
                   <span className="info-label">File</span>
                   <span className="info-value font-mono">{activeNode.file_path || 'Unknown'}</span>
                 </div>
                 
                 <div className="info-panel-item">
                   <span className="info-label">Lines</span>
                   <span className="info-value">
                     {activeNode.start_line !== null && activeNode.end_line !== null 
                       ? `${activeNode.start_line} - ${activeNode.end_line}` 
                       : 'N/A'}
                   </span>
                 </div>
                 
                 <div className="info-panel-item" style={{ marginTop: 'var(--sp-2)' }}>
                   <span className="info-label">Symbol ID</span>
                   <span className="info-value text-muted text-xs font-mono">{activeNode.node_id}</span>
                 </div>
               </div>

               <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
                  <Link to={`/symbols/${repositoryId}/${activeNode.node_id}`} style={{ textDecoration: 'none' }}>
                    <Button variant="primary" style={{ width: '100%', justifyContent: 'center' }} iconRight={<ChevronRight size={16} />}>
                       Open in Symbol Explorer
                    </Button>
                  </Link>
                  {/* Option to re-root graph to this node */}
                  {activeNode.node_id !== symbolId && (
                     <Button 
                       variant="ghost" 
                       style={{ width: '100%', justifyContent: 'center' }} 
                       onClick={() => navigate(`/graph/${repositoryId}/${activeNode.node_id}`)}
                     >
                       Root Graph Here
                     </Button>
                  )}
               </div>
             </>
           ) : (
             <div style={{ padding: 'var(--sp-4)', textAlign: 'center', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)', alignItems: 'center' }}>
               <Network size={32} opacity={0.5} />
               <p>Select a node in the graph to view details.</p>
             </div>
           )}
        </div>
      </div>

    </div>
  );
};
