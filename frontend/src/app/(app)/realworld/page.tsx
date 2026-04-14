"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface Source {
  name: string;
  description: string;
  refresh_rate: number;
  params: string[];
  has_free_api: boolean;
}

interface Trigger {
  id: string;
  source: string;
  params: Record<string, string>;
  field_path: string;
  condition: string;
  threshold: string | number;
  action_description: string;
  active: boolean;
  last_value: unknown;
  last_checked: string;
  last_fired: string;
}

interface HistoryEvent {
  id: string;
  trigger_id: string;
  source: string;
  field_path: string;
  condition: string;
  value: unknown;
  threshold: unknown;
  fired_at: string;
}

interface RWStats {
  sources_available: number;
  triggers_total: number;
  triggers_active: number;
  events_fired: number;
  cache_entries: number;
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const CONDITIONS = [">", "<", ">=", "<=", "==", "!=", "contains", "changes"];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function RealWorldPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [stats, setStats] = useState<RWStats | null>(null);
  const [liveData, setLiveData] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"live" | "triggers" | "history" | "stats">("live");

  // Trigger builder state
  const [newSource, setNewSource] = useState("");
  const [newParams, setNewParams] = useState("");
  const [newField, setNewField] = useState("");
  const [newCondition, setNewCondition] = useState(">");
  const [newThreshold, setNewThreshold] = useState("");
  const [newAction, setNewAction] = useState("");

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [srcRes, trigRes, histRes, statRes] = await Promise.all([
        fetch(`${API}/api/v1/realworld/sources`),
        fetch(`${API}/api/v1/realworld/triggers?user_id=default`),
        fetch(`${API}/api/v1/realworld/history?limit=50`),
        fetch(`${API}/api/v1/realworld/stats`),
      ]);
      setSources((await srcRes.json()).sources || []);
      setTriggers((await trigRes.json()).triggers || []);
      setHistory((await histRes.json()).history || []);
      setStats(await statRes.json());
    } catch {
      // API may be unavailable
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchLive = useCallback(async () => {
    const liveSources = ["weather", "crypto", "time", "exchange_rates"];
    const defaults: Record<string, string> = {
      weather: "city=London",
      crypto: "coins=bitcoin,ethereum",
      time: "zone=America/New_York",
      exchange_rates: "currency=USD",
    };
    const results: Record<string, unknown> = {};
    await Promise.all(
      liveSources.map(async (s) => {
        try {
          const res = await fetch(`${API}/api/v1/realworld/fetch/${s}?params=${defaults[s] || ""}`);
          results[s] = await res.json();
        } catch {
          results[s] = { error: "unavailable" };
        }
      })
    );
    setLiveData(results);
  }, []);

  useEffect(() => {
    fetchAll();
    fetchLive();
    intervalRef.current = setInterval(fetchLive, 30000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchAll, fetchLive]);

  const handleCreateTrigger = async () => {
    const params: Record<string, string> = {};
    if (newParams) {
      newParams.split(",").forEach((pair) => {
        const [k, v] = pair.split("=").map((s) => s.trim());
        if (k && v) params[k] = v;
      });
    }
    try {
      await fetch(`${API}/api/v1/realworld/triggers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "default",
          source: newSource,
          params,
          field_path: newField,
          condition: newCondition,
          threshold: newThreshold,
          action_description: newAction,
        }),
      });
      setNewSource("");
      setNewParams("");
      setNewField("");
      setNewCondition(">");
      setNewThreshold("");
      setNewAction("");
      fetchAll();
    } catch { /* ignore */ }
  };

  const handleDeleteTrigger = async (id: string) => {
    try {
      await fetch(`${API}/api/v1/realworld/triggers/${id}`, { method: "DELETE" });
      setTriggers((prev) => prev.filter((t) => t.id !== id));
    } catch { /* ignore */ }
  };

  const handleCheckNow = async () => {
    try {
      await fetch(`${API}/api/v1/realworld/triggers/check`, { method: "POST" });
      fetchAll();
    } catch { /* ignore */ }
  };

  const sourceIcon = (name: string) => {
    const icons: Record<string, string> = { weather: "🌤️", news: "📰", crypto: "₿", stocks: "📈", time: "🕐", ip_info: "🌐", exchange_rates: "💱", random_data: "🎲" };
    return icons[name] || "📡";
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <h1 className="text-3xl font-bold text-gnosis-text flex items-center gap-3">
          <span className="text-4xl">🌍</span> Real World
        </h1>
        <p className="text-gnosis-muted mt-2">Agents that react to the physical world</p>
      </motion.div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gnosis-border pb-2">
        {(["live", "triggers", "history", "stats"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-colors ${
              tab === t ? "bg-gnosis-primary/10 text-gnosis-primary border-b-2 border-gnosis-primary" : "text-gnosis-muted hover:text-gnosis-text"
            }`}
          >
            {t === "live" && "📡 Live Data"}
            {t === "triggers" && "⚡ Triggers"}
            {t === "history" && "📜 History"}
            {t === "stats" && "📈 Stats"}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-center py-20">
            <div className="text-4xl mb-4 animate-pulse">🌍</div>
            <p className="text-gnosis-muted">Connecting to the real world...</p>
          </motion.div>
        ) : (
          <>
            {/* Live Data Tab */}
            {tab === "live" && (
              <motion.div key="live" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} className="space-y-6">
                {/* Source grid */}
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  {sources.map((src, i) => (
                    <motion.div
                      key={src.name}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="rounded-xl border border-gnosis-border bg-gnosis-surface p-4"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xl">{sourceIcon(src.name)}</span>
                        <h3 className="font-semibold text-gnosis-text text-sm capitalize">{src.name}</h3>
                        {src.has_free_api && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-green-500/20 text-green-400 font-medium">FREE</span>}
                      </div>
                      <p className="text-xs text-gnosis-muted mb-2">{src.description}</p>
                      <div className="text-[10px] text-gnosis-muted/60">
                        Refresh: {src.refresh_rate > 0 ? `${src.refresh_rate}s` : "on demand"}
                        {src.params.length > 0 && ` · Params: ${src.params.join(", ")}`}
                      </div>
                    </motion.div>
                  ))}
                </div>

                {/* Live widgets */}
                <h2 className="text-lg font-semibold text-gnosis-text">Live Data Feeds</h2>
                <div className="grid gap-4 md:grid-cols-2">
                  {Object.entries(liveData).map(([source, data], i) => (
                    <motion.div
                      key={source}
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.08 }}
                      className="rounded-xl border border-gnosis-border bg-gnosis-surface p-5"
                    >
                      <div className="flex items-center gap-2 mb-3">
                        <span className="text-xl">{sourceIcon(source)}</span>
                        <h3 className="font-semibold text-gnosis-text capitalize">{source.replace("_", " ")}</h3>
                        <span className="ml-auto text-[9px] px-2 py-0.5 rounded-full bg-green-500/20 text-green-400 animate-pulse">● LIVE</span>
                      </div>
                      <pre className="text-xs text-gnosis-muted bg-black/20 rounded-lg p-3 overflow-auto max-h-40 font-mono">
                        {JSON.stringify(data, null, 2).slice(0, 500)}
                      </pre>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Triggers Tab */}
            {tab === "triggers" && (
              <motion.div key="triggers" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} className="space-y-6">
                {/* Trigger builder */}
                <div className="rounded-xl border border-gnosis-border bg-gnosis-surface p-6 space-y-4">
                  <h2 className="text-lg font-semibold text-gnosis-text">⚡ Create Trigger</h2>
                  <div className="grid gap-3 md:grid-cols-3">
                    <div>
                      <label className="text-xs text-gnosis-muted block mb-1">Source</label>
                      <select value={newSource} onChange={(e) => setNewSource(e.target.value)} className="w-full rounded-lg bg-black/20 border border-gnosis-border px-3 py-2 text-sm text-gnosis-text">
                        <option value="">Select source...</option>
                        {sources.map((s) => (
                          <option key={s.name} value={s.name}>{sourceIcon(s.name)} {s.name}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-gnosis-muted block mb-1">Params (key=val,...)</label>
                      <input value={newParams} onChange={(e) => setNewParams(e.target.value)} placeholder="city=London" className="w-full rounded-lg bg-black/20 border border-gnosis-border px-3 py-2 text-sm text-gnosis-text" />
                    </div>
                    <div>
                      <label className="text-xs text-gnosis-muted block mb-1">Field Path</label>
                      <input value={newField} onChange={(e) => setNewField(e.target.value)} placeholder="data.bitcoin.usd" className="w-full rounded-lg bg-black/20 border border-gnosis-border px-3 py-2 text-sm text-gnosis-text" />
                    </div>
                    <div>
                      <label className="text-xs text-gnosis-muted block mb-1">Condition</label>
                      <select value={newCondition} onChange={(e) => setNewCondition(e.target.value)} className="w-full rounded-lg bg-black/20 border border-gnosis-border px-3 py-2 text-sm text-gnosis-text">
                        {CONDITIONS.map((c) => <option key={c} value={c}>{c}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-gnosis-muted block mb-1">Threshold</label>
                      <input value={newThreshold} onChange={(e) => setNewThreshold(e.target.value)} placeholder="100000" className="w-full rounded-lg bg-black/20 border border-gnosis-border px-3 py-2 text-sm text-gnosis-text" />
                    </div>
                    <div>
                      <label className="text-xs text-gnosis-muted block mb-1">Action</label>
                      <input value={newAction} onChange={(e) => setNewAction(e.target.value)} placeholder="Send alert" className="w-full rounded-lg bg-black/20 border border-gnosis-border px-3 py-2 text-sm text-gnosis-text" />
                    </div>
                  </div>
                  <button onClick={handleCreateTrigger} disabled={!newSource || !newField} className="px-5 py-2 rounded-lg bg-gnosis-primary text-white text-sm font-medium hover:bg-gnosis-primary/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
                    Create Trigger
                  </button>
                </div>

                {/* Active triggers */}
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-gnosis-text">Active Triggers</h2>
                  <button onClick={handleCheckNow} className="px-3 py-1.5 rounded-lg bg-gnosis-primary/20 text-gnosis-primary text-xs font-medium hover:bg-gnosis-primary/30 transition-colors">
                    ⚡ Check Now
                  </button>
                </div>
                {triggers.length === 0 ? (
                  <div className="text-center py-12 text-gnosis-muted">
                    <div className="text-4xl mb-3">⚡</div>
                    <p>No triggers configured</p>
                    <p className="text-sm mt-1">Create one above to get started</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {triggers.map((t, i) => (
                      <motion.div
                        key={t.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className="rounded-xl border border-gnosis-border bg-gnosis-surface p-4 flex items-center gap-4"
                      >
                        <span className="text-xl">{sourceIcon(t.source)}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-gnosis-text font-medium">
                            {t.source} · <span className="font-mono text-gnosis-primary">{t.field_path}</span>{" "}
                            <span className="text-gnosis-muted">{t.condition}</span>{" "}
                            <span className="text-yellow-400">{String(t.threshold)}</span>
                          </div>
                          <div className="text-xs text-gnosis-muted mt-0.5">
                            {t.action_description || "No action set"}
                            {t.last_value !== null && <> · Last: <span className="text-gnosis-text">{String(t.last_value)}</span></>}
                          </div>
                        </div>
                        <span className={`text-[9px] px-2 py-0.5 rounded-full ${t.active ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
                          {t.active ? "ACTIVE" : "PAUSED"}
                        </span>
                        <button onClick={() => handleDeleteTrigger(t.id)} className="text-gnosis-muted hover:text-red-400 transition-colors text-sm">✕</button>
                      </motion.div>
                    ))}
                  </div>
                )}
              </motion.div>
            )}

            {/* History Tab */}
            {tab === "history" && (
              <motion.div key="history" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} className="space-y-3">
                {history.length === 0 ? (
                  <div className="text-center py-16 text-gnosis-muted">
                    <div className="text-4xl mb-3">📜</div>
                    <p>No events yet</p>
                    <p className="text-sm mt-1">Events appear here when triggers fire</p>
                  </div>
                ) : (
                  history.map((ev, i) => (
                    <motion.div
                      key={ev.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03 }}
                      className="rounded-xl border border-gnosis-border bg-gnosis-surface p-4 flex items-center gap-4"
                    >
                      <span className="text-xl">{sourceIcon(ev.source)}</span>
                      <div className="flex-1">
                        <div className="text-sm text-gnosis-text">
                          <span className="font-mono text-gnosis-primary">{ev.field_path}</span>{" "}
                          <span className="text-gnosis-muted">{ev.condition}</span>{" "}
                          <span className="text-yellow-400">{String(ev.threshold)}</span>{" "}
                          → <span className="text-green-400">{String(ev.value)}</span>
                        </div>
                        <div className="text-[10px] text-gnosis-muted/60 mt-0.5">{ev.fired_at}</div>
                      </div>
                    </motion.div>
                  ))
                )}
              </motion.div>
            )}

            {/* Stats Tab */}
            {tab === "stats" && (
              <motion.div key="stats" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
                {stats &&
                  [
                    { label: "Sources", value: stats.sources_available, icon: "📡" },
                    { label: "Total Triggers", value: stats.triggers_total, icon: "⚡" },
                    { label: "Active Triggers", value: stats.triggers_active, icon: "✅" },
                    { label: "Events Fired", value: stats.events_fired, icon: "🔥" },
                    { label: "Cache Entries", value: stats.cache_entries, icon: "💾" },
                  ].map((s, i) => (
                    <motion.div
                      key={s.label}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.06 }}
                      className="rounded-xl border border-gnosis-border bg-gnosis-surface p-5 text-center"
                    >
                      <div className="text-2xl mb-2">{s.icon}</div>
                      <div className="text-2xl font-bold text-gnosis-text">{s.value}</div>
                      <div className="text-xs text-gnosis-muted mt-1">{s.label}</div>
                    </motion.div>
                  ))}
              </motion.div>
            )}
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
