"use client";

import { useState, useEffect, useRef, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface GraphNode {
  id: string;
  name: string;
  type: string;
  mentions: number;
  properties: Record<string, unknown>;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  weight: number;
}

interface GraphStats {
  total_entities: number;
  total_relationships: number;
  entity_types: Record<string, number>;
}

const TYPE_COLORS: Record<string, string> = {
  person: "#6366f1",
  organization: "#f59e0b",
  concept: "#10b981",
  tool: "#3b82f6",
  action: "#ef4444",
  location: "#8b5cf6",
};

const TYPE_LABELS: Record<string, string> = {
  person: "Person",
  organization: "Organization",
  concept: "Concept",
  tool: "Tool",
  action: "Action",
  location: "Location",
};

export default function KnowledgePage() {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<GraphNode[]>([]);
  const [extractText, setExtractText] = useState("");
  const [extracting, setExtracting] = useState(false);
  const svgRef = useRef<SVGSVGElement>(null);
  const animFrameRef = useRef<number>(0);
  const draggingRef = useRef<string | null>(null);
  const mouseRef = useRef({ x: 0, y: 0 });

  const fetchGraph = useCallback(async () => {
    try {
      const [graphRes, statsRes] = await Promise.all([
        fetch(`${API}/api/v1/knowledge-graph/graph`),
        fetch(`${API}/api/v1/knowledge-graph/stats`),
      ]);
      const graphData = await graphRes.json();
      const statsData = await statsRes.json();

      const width = 800;
      const height = 600;
      const initialized: GraphNode[] = graphData.nodes.map(
        (n: Omit<GraphNode, "x" | "y" | "vx" | "vy">, i: number) => ({
          ...n,
          x: width / 2 + (Math.cos((i * 2 * Math.PI) / graphData.nodes.length) * width) / 3,
          y: height / 2 + (Math.sin((i * 2 * Math.PI) / graphData.nodes.length) * height) / 3,
          vx: 0,
          vy: 0,
        })
      );

      setNodes(initialized);
      setEdges(graphData.edges);
      setStats(statsData);
    } catch {
      /* API unavailable */
    }
  }, []);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  // Force-directed simulation
  useEffect(() => {
    if (nodes.length === 0) return;

    const width = 800;
    const height = 600;
    let localNodes = nodes.map((n) => ({ ...n }));

    const tick = () => {
      const k = 0.01; // repulsion damping
      const springLen = 120;
      const springK = 0.005;
      const damping = 0.9;
      const centerForce = 0.001;

      // Repulsion between all node pairs
      for (let i = 0; i < localNodes.length; i++) {
        for (let j = i + 1; j < localNodes.length; j++) {
          const dx = localNodes[j].x - localNodes[i].x;
          const dy = localNodes[j].y - localNodes[i].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = (500 / (dist * dist)) * k;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          localNodes[i].vx -= fx;
          localNodes[i].vy -= fy;
          localNodes[j].vx += fx;
          localNodes[j].vy += fy;
        }
      }

      // Spring forces along edges
      const nodeMap = new Map(localNodes.map((n) => [n.id, n]));
      for (const edge of edges) {
        const s = nodeMap.get(edge.source);
        const t = nodeMap.get(edge.target);
        if (!s || !t) continue;
        const dx = t.x - s.x;
        const dy = t.y - s.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - springLen) * springK;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        s.vx += fx;
        s.vy += fy;
        t.vx -= fx;
        t.vy -= fy;
      }

      // Center gravity + update positions
      for (const n of localNodes) {
        if (draggingRef.current === n.id) {
          n.x = mouseRef.current.x;
          n.y = mouseRef.current.y;
          n.vx = 0;
          n.vy = 0;
          continue;
        }
        n.vx += (width / 2 - n.x) * centerForce;
        n.vy += (height / 2 - n.y) * centerForce;
        n.vx *= damping;
        n.vy *= damping;
        n.x += n.vx;
        n.y += n.vy;
        n.x = Math.max(20, Math.min(width - 20, n.x));
        n.y = Math.max(20, Math.min(height - 20, n.y));
      }

      setNodes([...localNodes]);
      animFrameRef.current = requestAnimationFrame(tick);
    };

    animFrameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [nodes.length, edges]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    try {
      const res = await fetch(
        `${API}/api/v1/knowledge-graph/entities/search?query=${encodeURIComponent(searchQuery)}`
      );
      const data = await res.json();
      setSearchResults(data.entities || []);
    } catch {
      /* ignore */
    }
  };

  const handleExtract = async () => {
    if (!extractText.trim()) return;
    setExtracting(true);
    try {
      await fetch(`${API}/api/v1/knowledge-graph/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: extractText }),
      });
      setExtractText("");
      await fetchGraph();
    } catch {
      /* ignore */
    }
    setExtracting(false);
  };

  const handleMouseDown = (nodeId: string) => {
    draggingRef.current = nodeId;
  };

  const handleMouseUp = () => {
    draggingRef.current = null;
  };

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    mouseRef.current = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  };

  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-gnosis-text flex items-center gap-3">
            <span className="text-4xl">🧠</span>
            Knowledge Graph
          </h1>
          <p className="text-gnosis-muted mt-1">
            Entity-relationship graph from agent memory and interactions
          </p>
        </div>
      </div>

      {/* Stats Card */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gnosis-surface border border-gnosis-border rounded-xl p-4">
            <p className="text-xs text-gnosis-muted uppercase tracking-wider">Entities</p>
            <p className="text-2xl font-bold text-gnosis-text mt-1">{stats.total_entities}</p>
          </div>
          <div className="bg-gnosis-surface border border-gnosis-border rounded-xl p-4">
            <p className="text-xs text-gnosis-muted uppercase tracking-wider">Relationships</p>
            <p className="text-2xl font-bold text-gnosis-text mt-1">{stats.total_relationships}</p>
          </div>
          {Object.entries(stats.entity_types).map(([type, count]) => (
            <div
              key={type}
              className="bg-gnosis-surface border border-gnosis-border rounded-xl p-4"
            >
              <p className="text-xs text-gnosis-muted uppercase tracking-wider">
                {TYPE_LABELS[type] || type}
              </p>
              <p className="text-2xl font-bold" style={{ color: TYPE_COLORS[type] || "#888" }}>
                {count}
              </p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Graph Visualization */}
        <div className="lg:col-span-2 bg-gnosis-surface border border-gnosis-border rounded-xl p-4">
          <h2 className="text-lg font-semibold text-gnosis-text mb-3">Graph Visualization</h2>

          {/* Legend */}
          <div className="flex flex-wrap gap-3 mb-3">
            {Object.entries(TYPE_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-1.5 text-xs text-gnosis-muted">
                <span
                  className="w-3 h-3 rounded-full inline-block"
                  style={{ backgroundColor: color }}
                />
                {TYPE_LABELS[type] || type}
              </div>
            ))}
          </div>

          <svg
            ref={svgRef}
            viewBox="0 0 800 600"
            className="w-full h-auto bg-gnosis-bg rounded-lg border border-gnosis-border"
            style={{ minHeight: 400 }}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            {/* Edges */}
            {edges.map((edge) => {
              const s = nodeMap.get(edge.source);
              const t = nodeMap.get(edge.target);
              if (!s || !t) return null;
              const midX = (s.x + t.x) / 2;
              const midY = (s.y + t.y) / 2;
              return (
                <g key={edge.id}>
                  <line
                    x1={s.x}
                    y1={s.y}
                    x2={t.x}
                    y2={t.y}
                    stroke="#4b5563"
                    strokeWidth={Math.min(edge.weight * 1.5, 5)}
                    strokeOpacity={0.5}
                  />
                  <text
                    x={midX}
                    y={midY - 4}
                    textAnchor="middle"
                    fill="#6b7280"
                    fontSize={9}
                  >
                    {edge.type}
                  </text>
                </g>
              );
            })}

            {/* Nodes */}
            {nodes.map((node) => {
              const r = Math.max(8, Math.min(20, 6 + node.mentions * 3));
              const color = TYPE_COLORS[node.type] || "#6b7280";
              const isSelected = selectedNode?.id === node.id;
              return (
                <g
                  key={node.id}
                  onMouseDown={() => handleMouseDown(node.id)}
                  onClick={() => setSelectedNode(node)}
                  style={{ cursor: "pointer" }}
                >
                  {isSelected && (
                    <circle cx={node.x} cy={node.y} r={r + 4} fill="none" stroke={color} strokeWidth={2} strokeOpacity={0.5} />
                  )}
                  <circle cx={node.x} cy={node.y} r={r} fill={color} fillOpacity={0.8} stroke={color} strokeWidth={1.5} />
                  <text
                    x={node.x}
                    y={node.y + r + 12}
                    textAnchor="middle"
                    fill="#d1d5db"
                    fontSize={10}
                    fontWeight={isSelected ? 700 : 400}
                  >
                    {node.name}
                  </text>
                </g>
              );
            })}

            {nodes.length === 0 && (
              <text x={400} y={300} textAnchor="middle" fill="#6b7280" fontSize={14}>
                No entities yet. Extract text or add entities to build the graph.
              </text>
            )}
          </svg>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Search */}
          <div className="bg-gnosis-surface border border-gnosis-border rounded-xl p-4">
            <h3 className="text-sm font-semibold text-gnosis-text mb-2">Search Entities</h3>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="flex-1 bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted focus:outline-none focus:border-gnosis-primary"
              />
              <button
                onClick={handleSearch}
                className="px-3 py-2 bg-gnosis-primary/20 text-gnosis-primary rounded-lg text-sm hover:bg-gnosis-primary/30 transition-colors"
              >
                🔍
              </button>
            </div>
            {searchResults.length > 0 && (
              <ul className="mt-2 space-y-1 max-h-40 overflow-y-auto">
                {searchResults.map((r: GraphNode) => (
                  <li
                    key={r.id}
                    className="text-xs text-gnosis-muted px-2 py-1 hover:bg-white/5 rounded cursor-pointer"
                    onClick={() => {
                      const found = nodes.find((n) => n.id === r.id);
                      if (found) setSelectedNode(found);
                    }}
                  >
                    <span
                      className="inline-block w-2 h-2 rounded-full mr-1.5"
                      style={{ backgroundColor: TYPE_COLORS[r.type] || "#888" }}
                    />
                    {r.name}{" "}
                    <span className="text-gnosis-muted/60">({r.mentions} mentions)</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Selected node details */}
          {selectedNode && (
            <div className="bg-gnosis-surface border border-gnosis-border rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gnosis-text mb-2">Node Details</h3>
              <div className="space-y-1 text-xs text-gnosis-muted">
                <p>
                  <span className="text-gnosis-text font-medium">Name:</span> {selectedNode.name}
                </p>
                <p>
                  <span className="text-gnosis-text font-medium">Type:</span>{" "}
                  <span
                    className="inline-block px-1.5 py-0.5 rounded text-white text-[10px]"
                    style={{ backgroundColor: TYPE_COLORS[selectedNode.type] || "#888" }}
                  >
                    {selectedNode.type}
                  </span>
                </p>
                <p>
                  <span className="text-gnosis-text font-medium">Mentions:</span>{" "}
                  {selectedNode.mentions}
                </p>
                {Object.keys(selectedNode.properties).length > 0 && (
                  <div>
                    <span className="text-gnosis-text font-medium">Properties:</span>
                    <pre className="mt-1 bg-gnosis-bg p-2 rounded text-[10px] overflow-x-auto">
                      {JSON.stringify(selectedNode.properties, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="mt-2 text-xs text-gnosis-muted hover:text-gnosis-text"
              >
                ✕ Close
              </button>
            </div>
          )}

          {/* Extract text */}
          <div className="bg-gnosis-surface border border-gnosis-border rounded-xl p-4">
            <h3 className="text-sm font-semibold text-gnosis-text mb-2">Extract from Text</h3>
            <textarea
              value={extractText}
              onChange={(e) => setExtractText(e.target.value)}
              placeholder="Paste text to extract entities and relationships..."
              rows={4}
              className="w-full bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted focus:outline-none focus:border-gnosis-primary resize-none"
            />
            <button
              onClick={handleExtract}
              disabled={extracting || !extractText.trim()}
              className="mt-2 w-full px-3 py-2 bg-gnosis-primary/20 text-gnosis-primary rounded-lg text-sm hover:bg-gnosis-primary/30 transition-colors disabled:opacity-50"
            >
              {extracting ? "Extracting..." : "Extract Entities"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
