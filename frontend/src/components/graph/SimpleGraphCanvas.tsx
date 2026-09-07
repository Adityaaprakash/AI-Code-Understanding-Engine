import React, { useState, useRef, useMemo, useCallback } from 'react';
import type { GraphTraversalResponse, SymbolItem, GraphEdge } from '../../types';

interface SimpleGraphCanvasProps {
  data: GraphTraversalResponse;
  rootSymbolId: string;
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string) => void;
}

interface Position {
  x: number;
  y: number;
}

let randSeed = 1;
function seedRandom() {
  randSeed = (randSeed * 1664525 + 1013904223) >>> 0;
  return randSeed / 4294967296;
}

function computeForceLayout(nodes: SymbolItem[], edges: GraphEdge[], rootId: string): Record<string, Position> {
  randSeed = 42; // Fixed seed for determinism
  
  const positions: Record<string, Position> = {};
  nodes.forEach(n => {
    // Initial random positions within a small box
    positions[n.node_id] = { x: seedRandom() * 400 - 200, y: seedRandom() * 400 - 200 };
  });
  if (positions[rootId]) {
    positions[rootId] = { x: 0, y: 0 };
  }

  const REPULSION = 80000;
  const ATTRACTION = 0.03;
  const DAMPING = 0.70;
  const OPTIMAL_DIST = 180;

  const velocities: Record<string, Position> = {};
  nodes.forEach(n => velocities[n.node_id] = { x: 0, y: 0 });

  for (let i = 0; i < 200; i++) {
    // Repulsion
    for (let a = 0; a < nodes.length; a++) {
      for (let b = a + 1; b < nodes.length; b++) {
        const id1 = nodes[a].node_id;
        const id2 = nodes[b].node_id;
        const dx = positions[id1].x - positions[id2].x;
        const dy = positions[id1].y - positions[id2].y;
        let dist = Math.sqrt(dx * dx + dy * dy);
        if (dist === 0) dist = 0.01;
        const force = REPULSION / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        velocities[id1].x += fx; velocities[id1].y += fy;
        velocities[id2].x -= fx; velocities[id2].y -= fy;
      }
    }

    // Attraction
    edges.forEach(e => {
      const id1 = e.source_id;
      const id2 = e.target_id;
      if (!positions[id1] || !positions[id2]) return;
      const dx = positions[id2].x - positions[id1].x;
      const dy = positions[id2].y - positions[id1].y;
      let dist = Math.sqrt(dx * dx + dy * dy);
      if (dist === 0) dist = 0.01;
      const force = (dist - OPTIMAL_DIST) * ATTRACTION;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;

      velocities[id1].x += fx; velocities[id1].y += fy;
      velocities[id2].x -= fx; velocities[id2].y -= fy;
    });

    // Update positions
    nodes.forEach(n => {
      // Fix root node loosely
      if (n.node_id === rootId) {
        velocities[n.node_id].x -= positions[n.node_id].x * 0.1;
        velocities[n.node_id].y -= positions[n.node_id].y * 0.1;
      }

      const v = velocities[n.node_id];
      v.x *= DAMPING; v.y *= DAMPING;
      
      // Safety cap velocity
      const vMag = Math.sqrt(v.x*v.x + v.y*v.y);
      if(vMag > 50) { v.x = (v.x/vMag)*50; v.y = (v.y/vMag)*50; }

      positions[n.node_id].x += v.x;
      positions[n.node_id].y += v.y;
    });
  }
  
  // Recenter exactly to bounding box center
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  nodes.forEach(n => {
    const p = positions[n.node_id];
    if (p.x < minX) minX = p.x;
    if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.y > maxY) maxY = p.y;
  });
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  nodes.forEach(n => {
    positions[n.node_id].x -= cx;
    positions[n.node_id].y -= cy;
  });

  return positions;
}

export const SimpleGraphCanvas: React.FC<SimpleGraphCanvasProps> = ({ data, rootSymbolId, selectedNodeId, onNodeSelect }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Compute positions deterministically
  const layout = useMemo(() => {
    return computeForceLayout(data.nodes, data.edges, rootSymbolId);
  }, [data, rootSymbolId]);

  // Pan / Zoom state
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 0.8 });
  const [isDragging, setIsDragging] = useState(false);
  const lastMouse = useRef({ x: 0, y: 0 });

  const handleWheel = (e: React.WheelEvent) => {
    if (!containerRef.current) return;
    
    // Determine focal point
    const rect = containerRef.current.getBoundingClientRect();
    const cursorX = e.clientX - rect.left;
    const cursorY = e.clientY - rect.top;

    // Zoom delta
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    let newK = transform.k * zoomFactor;
    newK = Math.min(Math.max(0.1, newK), 4);

    // Adjust x/y to zoom around cursor
    const newX = cursorX - (cursorX - transform.x) * (newK / transform.k);
    const newY = cursorY - (cursorY - transform.y) * (newK / transform.k);

    setTransform({ x: newX, y: newY, k: newK });
  };

  const handlePointerDown = (e: React.PointerEvent) => {
    if (e.target instanceof Element && e.target.closest('.node')) return; // let node click win
    setIsDragging(true);
    lastMouse.current = { x: e.clientX, y: e.clientY };
    e.currentTarget.setPointerCapture?.(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging) return;
    const dx = e.clientX - lastMouse.current.x;
    const dy = e.clientY - lastMouse.current.y;
    setTransform(prev => ({ ...prev, x: prev.x + dx, y: prev.y + dy }));
    lastMouse.current = { x: e.clientX, y: e.clientY };
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    setIsDragging(false);
    e.currentTarget.releasePointerCapture?.(e.pointerId);
  };

  const fitView = useCallback(() => {
    if (!containerRef.current) return;
    const w = containerRef.current.clientWidth;
    const h = containerRef.current.clientHeight;
    
    // Bounds of nodes
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    Object.values(layout).forEach(p => {
      if (p.x < minX) minX = p.x;
      if (p.x > maxX) maxX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.y > maxY) maxY = p.y;
    });

    const pad = 100;
    const graphW = (maxX - minX) || 1;
    const graphH = (maxY - minY) || 1;
    
    const scaleX = (w - pad * 2) / graphW;
    const scaleY = (h - pad * 2) / graphH;
    const scale = Math.min(Math.max(Math.min(scaleX, scaleY), 0.2), 1.5);
    
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    
    setTransform({
      x: w / 2 - cx * scale,
      y: h / 2 - cy * scale,
      k: scale
    });
  }, [layout]);

  // Initial fit
  React.useEffect(() => {
    fitView();
  }, [fitView]);

  return (
    <div 
      className="graph-canvas"
      ref={containerRef}
      onWheel={handleWheel}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      {/* Controls overlay */}
      <div className="graph-controls">
        <button onClick={fitView} title="Fit to View" aria-label="Fit Graph to View" className="graph-control-btn">
          Fit
        </button>
      </div>

      <svg width="100%" height="100%" className="graph-svg">
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--color-edge)" />
          </marker>
          <marker id="arrow-selected" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent)" />
          </marker>
        </defs>

        <g transform={`translate(${transform.x}, ${transform.y}) scale(${transform.k})`}>
          {/* Edges */}
          {data.edges.map((e, idx) => {
            const p1 = layout[e.source_id];
            const p2 = layout[e.target_id];
            if (!p1 || !p2) return null;

            const isRelated = selectedNodeId === e.source_id || selectedNodeId === e.target_id;
            const strokeColor = isRelated ? 'var(--accent)' : 'var(--color-edge)';
            const markerId = isRelated ? 'url(#arrow-selected)' : 'url(#arrow)';
            const strokeWidth = isRelated ? 2 : 1.5;

            // Simple label placement at midpoint
            const mx = (p1.x + p2.x) / 2;
            const my = (p1.y + p2.y) / 2;

            return (
              <g key={`${e.source_id}-${e.target_id}-${idx}`}>
                <line 
                  x1={p1.x} y1={p1.y} 
                  x2={p2.x} y2={p2.y} 
                  stroke={strokeColor} 
                  strokeWidth={strokeWidth} 
                  markerEnd={markerId}
                />
                <text x={mx} y={my} dy={-5} textAnchor="middle" className="edge-label" fill={strokeColor}>
                  {e.kind}
                </text>
              </g>
            );
          })}

          {/* Nodes */}
          {data.nodes.map(n => {
            const p = layout[n.node_id];
            if (!p) return null;

            const isSelected = selectedNodeId === n.node_id;
            const isRoot = n.node_id === rootSymbolId;
            
            let fillClass = 'node-bg';
            if (isSelected) fillClass = 'node-bg-selected';
            else if (isRoot) fillClass = 'node-bg-root';

            return (
              <g 
                key={n.node_id} 
                transform={`translate(${p.x}, ${p.y})`} 
                className={`node ${isSelected ? 'selected' : ''}`}
                onClick={() => onNodeSelect(n.node_id)}
                style={{ cursor: 'pointer' }}
                aria-label={`Node ${n.name}`}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if(e.key === 'Enter' || e.key === ' ') onNodeSelect(n.node_id); }}
              >
                <circle r={22} className={fillClass} />
                <text dy="-28" textAnchor="middle" className={`node-label ${isSelected ? 'strong' : ''}`}>{n.name || 'Unnamed'}</text>
                {n.kind && (
                  <text dy="32" textAnchor="middle" className="node-kind">{n.kind}</text>
                )}
                <text dy="5" textAnchor="middle" className="node-icon">{_getIconForKind(n.kind)}</text>
              </g>
            );
          })}
        </g>
      </svg>
      {/* Scope CSS */}
      <style>{`
        .graph-canvas {
          position: relative;
          width: 100%;
          height: 100%;
          overflow: hidden;
          background-color: var(--bg-surface);
          border-radius: var(--radius-md);
          border: 1px solid var(--border);
          user-select: none;
        }
        .graph-controls {
          position: absolute;
          top: var(--sp-4);
          right: var(--sp-4);
          z-index: 10;
        }
        .graph-control-btn {
          background-color: var(--bg-overlay);
          border: 1px solid var(--border);
          color: var(--text-primary);
          padding: var(--sp-1) var(--sp-3);
          border-radius: var(--radius-full);
          font-size: var(--text-sm);
          cursor: pointer;
          transition: background-color var(--transition-fast);
        }
        .graph-control-btn:hover {
          background-color: var(--bg-hover);
        }
        .graph-svg {
          display: block;
        }
        .node-bg {
          fill: var(--bg-overlay);
          stroke: var(--border-focus);
          stroke-width: 2px;
          transition: fill 0.2s;
        }
        .node-bg-root {
          fill: var(--bg-overlay);
          stroke: var(--success);
          stroke-width: 3px;
        }
        .node-bg-selected {
          fill: var(--accent);
          stroke: var(--accent);
          stroke-width: 2px;
        }
        .node:hover .node-bg, .node:hover .node-bg-root {
          fill: var(--bg-hover);
        }
        .node-label {
          fill: var(--text-primary);
          font-size: 13px;
          font-weight: var(--weight-medium);
          pointer-events: none;
          text-shadow: 0 1px 3px var(--bg-canvas);
        }
        .node-label.strong {
          fill: var(--accent);
          font-weight: var(--weight-bold);
        }
        .node-kind {
          fill: var(--text-secondary);
          font-size: 10px;
          text-transform: uppercase;
          pointer-events: none;
        }
        .node-icon {
          font-family: monospace;
          font-size: 16px;
          fill: var(--text-secondary);
          pointer-events: none;
        }
        .selected .node-icon {
          fill: var(--bg-surface);
        }
        .edge-label {
          font-size: 10px;
          font-weight: 600;
          pointer-events: none;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        :root {
          --color-edge: rgba(100, 100, 100, 0.4);
        }
        @media (prefers-color-scheme: dark) {
          :root {
            --color-edge: rgba(150, 150, 150, 0.3);
          }
        }
      `}</style>
    </div>
  );
}

function _getIconForKind(kind: string): string {
  switch(kind.toUpperCase()) {
    case 'CLASS': return 'C';
    case 'INTERFACE': return 'I';
    case 'FUNCTION': case 'METHOD': return 'ƒ';
    case 'VARIABLE': return 'v';
    case 'MODULE': return '{}';
    default: return '·';
  }
}
