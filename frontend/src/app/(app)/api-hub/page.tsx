"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CatalogAPI {
  key: string;
  name: string;
  description: string;
  category: string;
  endpoints: number;
  docs_url: string;
}

interface APIDetail {
  name: string;
  description: string;
  base_url: string;
  auth_type: string;
  docs_url: string;
  key_env_var: string;
  endpoints: { method: string; path: string; description: string }[];
  category: string;
}

interface Connection {
  id: string;
  api_name: string;
  api_key: string;
  base_url: string;
  auth_type: string;
  status: string;
  total_calls: number;
  errors: number;
}

interface Stats {
  catalog_size: number;
  active_connections: number;
  connected: number;
  total_api_calls: number;
  total_errors: number;
}

type Tab = "catalog" | "connections" | "explorer";

const CATEGORY_ICONS: Record<string, string> = {
  payments: "💳", developer: "🐙", communication: "💬", productivity: "📝",
  ai: "🤖", ecommerce: "🛒", email: "📧", data: "📊", crm: "👥",
};

export default function APIHubPage() {
  const [tab, setTab] = useState<Tab>("catalog");
  const [catalog, setCatalog] = useState<CatalogAPI[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<CatalogAPI[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [loading, setLoading] = useState(false);

  // Connect modal
  const [connectModal, setConnectModal] = useState<string | null>(null);
  const [connectKey, setConnectKey] = useState("");
  const [connectResult, setConnectResult] = useState<string | null>(null);

  // API detail
  const [selectedAPI, setSelectedAPI] = useState<APIDetail | null>(null);

  // Explorer
  const [explorerConn, setExplorerConn] = useState("");
  const [explorerEndpoint, setExplorerEndpoint] = useState("");
  const [explorerMethod, setExplorerMethod] = useState("GET");
  const [explorerBody, setExplorerBody] = useState("");
  const [explorerResult, setExplorerResult] = useState<string | null>(null);

  // Code gen
  const [generatedCode, setGeneratedCode] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [catRes, connRes, catsRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/apis/catalog`),
        fetch(`${API_BASE}/api/v1/apis/connections`),
        fetch(`${API_BASE}/api/v1/apis/categories`),
        fetch(`${API_BASE}/api/v1/apis/stats`),
      ]);
      if (catRes.ok) { const d = await catRes.json(); setCatalog(d.apis || []); }
      if (connRes.ok) { const d = await connRes.json(); setConnections(d.connections || []); }
      if (catsRes.ok) { const d = await catsRes.json(); setCategories(d.categories || []); }
      if (statsRes.ok) { const d = await statsRes.json(); setStats(d); }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSearch = async () => {
    if (!search.trim()) { setSearchResults([]); return; }
    try {
      const res = await fetch(`${API_BASE}/api/v1/apis/search?q=${encodeURIComponent(search)}`);
      if (res.ok) { const d = await res.json(); setSearchResults(d.results || []); }
    } catch { /* ignore */ }
  };

  useEffect(() => {
    const timer = setTimeout(handleSearch, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const loadAPIDetail = async (name: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/apis/catalog/${name}`);
      if (res.ok) { const d = await res.json(); setSelectedAPI(d); }
    } catch { /* ignore */ }
  };

  const connectToAPI = async () => {
    if (!connectModal || !connectKey.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/apis/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_name: connectModal, api_key: connectKey }),
      });
      const d = await res.json();
      if (res.ok) {
        setConnectResult(d.message || "Connected!");
        setTimeout(() => { setConnectModal(null); setConnectKey(""); setConnectResult(null); fetchData(); }, 1500);
      } else {
        setConnectResult(d.detail || "Connection failed");
      }
    } finally { setLoading(false); }
  };

  const deleteConnection = async (id: string) => {
    await fetch(`${API_BASE}/api/v1/apis/connections/${id}`, { method: "DELETE" });
    fetchData();
  };

  const testConnection = async (id: string) => {
    const res = await fetch(`${API_BASE}/api/v1/apis/connections/${id}/test`, { method: "POST" });
    if (res.ok) fetchData();
  };

  const callAPI = async () => {
    if (!explorerConn || !explorerEndpoint) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/apis/connections/${explorerConn}/call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          endpoint_path: explorerEndpoint,
          method: explorerMethod,
          body: explorerBody ? JSON.parse(explorerBody) : null,
        }),
      });
      const d = await res.json();
      setExplorerResult(JSON.stringify(d, null, 2));
    } catch (e) {
      setExplorerResult(String(e));
    } finally { setLoading(false); }
  };

  const generateCode = async (name: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/apis/generate/${name}`);
      if (res.ok) { const d = await res.json(); setGeneratedCode(d.code); }
    } catch { /* ignore */ }
  };

  const filteredCatalog = selectedCategory
    ? catalog.filter(a => a.category === selectedCategory)
    : catalog;

  const displayList = search.trim() && searchResults.length > 0 ? searchResults : filteredCatalog;

  const statusDot = (s: string) => {
    switch (s) {
      case "connected": return "bg-emerald-400";
      case "configured": return "bg-amber-400";
      case "failed": return "bg-red-400";
      default: return "bg-gray-400";
    }
  };

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: "catalog", label: "API Catalog", icon: "📚" },
    { id: "connections", label: `Connections (${connections.length})`, icon: "🔌" },
    { id: "explorer", label: "API Explorer", icon: "🔬" },
  ];

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-gnosis-text">🔗 API Hub</h1>
        <p className="text-gnosis-muted mt-1">Auto-discover and connect to any API — say the name, we wire it up</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { label: "Catalog APIs", value: stats.catalog_size, icon: "📚" },
            { label: "Connections", value: stats.active_connections, icon: "🔌" },
            { label: "Connected", value: stats.connected, icon: "✅" },
            { label: "API Calls", value: stats.total_api_calls, icon: "📡" },
            { label: "Errors", value: stats.total_errors, icon: "⚠️" },
          ].map((s) => (
            <div key={s.label} className="bg-gnosis-surface border border-gnosis-border rounded-xl p-3 text-center">
              <p className="text-lg">{s.icon}</p>
              <p className="text-xl font-bold text-gnosis-text">{s.value}</p>
              <p className="text-xs text-gnosis-muted">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <input
          type="text" value={search} onChange={e => setSearch(e.target.value)}
          placeholder='Search for an API... (e.g. "stripe", "payments", "email")'
          className="w-full bg-gnosis-surface border border-gnosis-border rounded-xl px-5 py-3 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50"
        />
        {search && (
          <button onClick={() => setSearch("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gnosis-muted hover:text-gnosis-text text-sm">✕</button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-xl bg-gnosis-bg border border-gnosis-border w-fit">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`relative px-4 py-1.5 text-sm font-medium rounded-lg transition-colors ${
              tab === t.id ? "text-gnosis-primary" : "text-gnosis-muted hover:text-gnosis-text"
            }`}>
            {tab === t.id && (
              <motion.div layoutId="api-tab" className="absolute inset-0 bg-gnosis-primary/10 rounded-lg" transition={{ duration: 0.2 }} />
            )}
            <span className="relative z-10">{t.icon} {t.label}</span>
          </button>
        ))}
      </div>

      {/* Category filter (catalog tab) */}
      {tab === "catalog" && (
        <div className="flex flex-wrap gap-2">
          <button onClick={() => setSelectedCategory("")}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
              !selectedCategory ? "bg-gnosis-primary/10 text-gnosis-primary" : "text-gnosis-muted hover:text-gnosis-text"
            }`}>All</button>
          {categories.map(cat => (
            <button key={cat} onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                selectedCategory === cat ? "bg-gnosis-primary/10 text-gnosis-primary" : "text-gnosis-muted hover:text-gnosis-text"
              }`}>{CATEGORY_ICONS[cat] || "📦"} {cat}</button>
          ))}
        </div>
      )}

      {/* Content */}
      <AnimatePresence mode="wait">
        {tab === "catalog" && (
          <motion.div key="catalog" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {displayList.map((api) => (
              <div key={api.key} className="bg-gnosis-surface border border-gnosis-border rounded-xl p-4 space-y-3 hover:border-gnosis-primary/30 transition-colors">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-gnosis-text text-sm flex items-center gap-2">
                      {CATEGORY_ICONS[api.category] || "📦"} {api.name}
                    </h3>
                    <p className="text-xs text-gnosis-muted mt-1">{api.description}</p>
                  </div>
                  <span className="px-2 py-0.5 bg-gnosis-bg text-gnosis-muted rounded text-xs shrink-0">{api.category}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gnosis-muted">{api.endpoints} endpoints</span>
                  {api.docs_url && (
                    <a href={api.docs_url} target="_blank" rel="noopener noreferrer"
                      className="text-gnosis-primary hover:underline">Docs ↗</a>
                  )}
                </div>
                <div className="flex gap-2">
                  <button onClick={() => { setConnectModal(api.key); setConnectKey(""); setConnectResult(null); }}
                    className="flex-1 px-3 py-1.5 bg-gnosis-primary/10 text-gnosis-primary rounded-lg text-xs font-medium hover:bg-gnosis-primary/20 transition-colors">
                    ⚡ Connect
                  </button>
                  <button onClick={() => loadAPIDetail(api.key)}
                    className="px-3 py-1.5 text-gnosis-muted hover:text-gnosis-text text-xs transition-colors">
                    Details
                  </button>
                  <button onClick={() => generateCode(api.key)}
                    className="px-3 py-1.5 text-gnosis-muted hover:text-gnosis-text text-xs transition-colors">
                    &lt;/&gt;
                  </button>
                </div>
              </div>
            ))}
          </motion.div>
        )}

        {tab === "connections" && (
          <motion.div key="connections" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="space-y-3">
            {connections.length === 0 && (
              <div className="text-center py-16">
                <p className="text-4xl mb-3">🔌</p>
                <p className="text-gnosis-muted text-sm">No API connections yet. Browse the catalog and connect!</p>
              </div>
            )}
            {connections.map((conn) => (
              <div key={conn.id} className="bg-gnosis-surface border border-gnosis-border rounded-xl p-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-2.5 h-2.5 rounded-full ${statusDot(conn.status)}`} />
                  <div>
                    <h3 className="font-semibold text-gnosis-text text-sm">{conn.api_name}</h3>
                    <p className="text-xs text-gnosis-muted">{conn.base_url}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-xs text-right">
                    <p className="text-gnosis-text">{conn.total_calls} calls</p>
                    <p className="text-gnosis-muted">{conn.status}</p>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => testConnection(conn.id)}
                      className="px-3 py-1 bg-gnosis-bg border border-gnosis-border rounded-lg text-xs text-gnosis-text hover:border-gnosis-primary/50 transition-colors">
                      Test
                    </button>
                    <button onClick={() => { setTab("explorer"); setExplorerConn(conn.id); }}
                      className="px-3 py-1 bg-gnosis-primary/10 text-gnosis-primary rounded-lg text-xs hover:bg-gnosis-primary/20 transition-colors">
                      Explore
                    </button>
                    <button onClick={() => deleteConnection(conn.id)}
                      className="px-3 py-1 text-red-400 hover:bg-red-400/10 rounded-lg text-xs transition-colors">
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </motion.div>
        )}

        {tab === "explorer" && (
          <motion.div key="explorer" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="space-y-4 max-w-3xl">
            <div className="bg-gnosis-surface border border-gnosis-border rounded-xl p-5 space-y-4">
              <h3 className="font-semibold text-gnosis-text text-sm">🔬 API Explorer</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <select value={explorerConn} onChange={e => setExplorerConn(e.target.value)}
                  className="bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text focus:outline-none focus:border-gnosis-primary/50">
                  <option value="">Select connection...</option>
                  {connections.map(c => <option key={c.id} value={c.id}>{c.api_name} ({c.id})</option>)}
                </select>
                <select value={explorerMethod} onChange={e => setExplorerMethod(e.target.value)}
                  className="bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text focus:outline-none focus:border-gnosis-primary/50">
                  {["GET", "POST", "PUT", "PATCH", "DELETE"].map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <input value={explorerEndpoint} onChange={e => setExplorerEndpoint(e.target.value)}
                placeholder="/endpoint/path"
                className="w-full bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text font-mono placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50" />
              {["POST", "PUT", "PATCH"].includes(explorerMethod) && (
                <textarea value={explorerBody} onChange={e => setExplorerBody(e.target.value)} rows={4}
                  placeholder='{"key": "value"}'
                  className="w-full bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text font-mono placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50 resize-none" />
              )}
              <button onClick={callAPI} disabled={loading || !explorerConn || !explorerEndpoint}
                className="px-6 py-2 bg-gnosis-primary text-white rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-gnosis-primary/90 transition-colors">
                📡 Send Request
              </button>
              {explorerResult && (
                <pre className="bg-gnosis-bg border border-gnosis-border rounded-lg p-4 text-xs text-gnosis-text overflow-auto max-h-80 font-mono">
                  {explorerResult}
                </pre>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Connect Modal */}
      <AnimatePresence>
        {connectModal && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setConnectModal(null)}>
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
              onClick={e => e.stopPropagation()}
              className="bg-gnosis-surface border border-gnosis-border rounded-xl p-6 space-y-4 w-full max-w-md">
              <h3 className="font-semibold text-gnosis-text">⚡ Connect to {connectModal}</h3>
              <p className="text-xs text-gnosis-muted">Enter your API key to establish a connection.</p>
              <input value={connectKey} onChange={e => setConnectKey(e.target.value)} type="password"
                placeholder="API Key / Token"
                className="w-full bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/50" />
              {connectResult && (
                <p className={`text-xs ${connectResult.includes("!") ? "text-emerald-400" : "text-red-400"}`}>{connectResult}</p>
              )}
              <div className="flex gap-2">
                <button onClick={connectToAPI} disabled={loading || !connectKey.trim()}
                  className="px-4 py-2 bg-gnosis-primary text-white rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-gnosis-primary/90 transition-colors">
                  Connect
                </button>
                <button onClick={() => setConnectModal(null)}
                  className="px-4 py-2 text-gnosis-muted text-sm hover:text-gnosis-text transition-colors">
                  Cancel
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* API Detail Modal */}
      <AnimatePresence>
        {selectedAPI && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setSelectedAPI(null)}>
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
              onClick={e => e.stopPropagation()}
              className="bg-gnosis-surface border border-gnosis-border rounded-xl p-6 space-y-4 w-full max-w-lg max-h-[80vh] overflow-y-auto">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gnosis-text text-lg">{selectedAPI.name}</h3>
                <button onClick={() => setSelectedAPI(null)} className="text-gnosis-muted hover:text-gnosis-text">✕</button>
              </div>
              <p className="text-sm text-gnosis-muted">{selectedAPI.description}</p>
              <div className="text-xs space-y-1">
                <p><span className="text-gnosis-muted">Base URL:</span> <span className="text-gnosis-text font-mono">{selectedAPI.base_url}</span></p>
                <p><span className="text-gnosis-muted">Auth:</span> <span className="text-gnosis-text">{selectedAPI.auth_type}</span></p>
                <p><span className="text-gnosis-muted">Env var:</span> <span className="text-gnosis-text font-mono">{selectedAPI.key_env_var}</span></p>
              </div>
              <div>
                <p className="text-xs font-semibold text-gnosis-text mb-2">Endpoints:</p>
                <div className="space-y-1.5">
                  {selectedAPI.endpoints.map((ep, i) => (
                    <div key={i} className="flex items-center gap-2 bg-gnosis-bg rounded-lg px-3 py-1.5 text-xs">
                      <span className={`font-mono font-bold ${
                        ep.method === "GET" ? "text-emerald-400" : ep.method === "POST" ? "text-blue-400" :
                        ep.method === "PUT" ? "text-amber-400" : ep.method === "DELETE" ? "text-red-400" : "text-gnosis-muted"
                      }`}>{ep.method}</span>
                      <span className="text-gnosis-text font-mono">{ep.path}</span>
                      <span className="text-gnosis-muted ml-auto">{ep.description}</span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Generated Code Modal */}
      <AnimatePresence>
        {generatedCode && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setGeneratedCode(null)}>
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
              onClick={e => e.stopPropagation()}
              className="bg-gnosis-surface border border-gnosis-border rounded-xl p-6 space-y-4 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gnosis-text">&lt;/&gt; Generated Connector</h3>
                <button onClick={() => setGeneratedCode(null)} className="text-gnosis-muted hover:text-gnosis-text">✕</button>
              </div>
              <pre className="bg-gnosis-bg border border-gnosis-border rounded-lg p-4 text-xs text-gnosis-text overflow-auto font-mono">
                {generatedCode}
              </pre>
              <button onClick={() => { navigator.clipboard.writeText(generatedCode); }}
                className="px-4 py-2 bg-gnosis-primary/10 text-gnosis-primary rounded-lg text-xs font-medium hover:bg-gnosis-primary/20 transition-colors">
                📋 Copy to Clipboard
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
