"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card } from "@/components/shared/Card";
import { Button } from "@/components/shared/Button";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Memory {
  id: string;
  content: string;
  tier: string;
  relevance_score?: number;
  access_count?: number;
  strength?: number;
  created_at?: string;
  last_accessed?: string;
  metadata?: Record<string, unknown>;
}

interface MemoryStats {
  total: number;
  by_tier: Record<string, number>;
}

const TIERS = [
  { key: "all", label: "All", color: "text-gnosis-text", bg: "bg-gnosis-border" },
  { key: "correction", label: "Correction", color: "text-red-400", bg: "bg-red-500/10" },
  { key: "episodic", label: "Episodic", color: "text-blue-400", bg: "bg-blue-500/10" },
  { key: "semantic", label: "Semantic", color: "text-purple-400", bg: "bg-purple-500/10" },
  { key: "procedural", label: "Procedural", color: "text-green-400", bg: "bg-green-500/10" },
];

function tierColor(tier: string): { text: string; bg: string; border: string } {
  switch (tier) {
    case "correction":
      return { text: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/30" };
    case "episodic":
      return { text: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/30" };
    case "semantic":
      return { text: "text-purple-400", bg: "bg-purple-500/10", border: "border-purple-500/30" };
    case "procedural":
      return { text: "text-green-400", bg: "bg-green-500/10", border: "border-green-500/30" };
    default:
      return { text: "text-gnosis-muted", bg: "bg-gnosis-border", border: "border-gnosis-border" };
  }
}

function formatTimestamp(ts?: string): string {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

interface MemoryExplorerProps {
  agentId: string;
}

export default function MemoryExplorer({ agentId }: MemoryExplorerProps) {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [stats, setStats] = useState<MemoryStats>({ total: 0, by_tier: {} });
  const [loading, setLoading] = useState(true);
  const [activeTier, setActiveTier] = useState("all");
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<Memory[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [showStore, setShowStore] = useState(false);
  const [newContent, setNewContent] = useState("");
  const [newTier, setNewTier] = useState("semantic");
  const [storing, setStoring] = useState(false);

  const fetchMemories = useCallback(async () => {
    setLoading(true);
    try {
      const tierParam = activeTier !== "all" ? `?tier=${activeTier}` : "";
      const res = await fetch(`${API_URL}/api/v1/memory/${agentId}${tierParam}`);
      if (res.ok) {
        const data = await res.json();
        setMemories(data.memories || []);
        if (data.stats) setStats(data.stats);
      }
    } catch {
      // API not available
    } finally {
      setLoading(false);
    }
  }, [agentId, activeTier]);

  useEffect(() => {
    fetchMemories();
  }, [fetchMemories]);

  async function handleSearch() {
    if (!search.trim()) {
      setSearchResults(null);
      return;
    }
    setSearching(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/memory/${agentId}/search?query=${encodeURIComponent(search)}`
      );
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.results || []);
      }
    } catch {
      // handle silently
    } finally {
      setSearching(false);
    }
  }

  async function handleStore() {
    if (!newContent.trim()) return;
    setStoring(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/memory/${agentId}/store`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tier: newTier, content: newContent, metadata: {} }),
      });
      if (res.ok) {
        setNewContent("");
        setShowStore(false);
        fetchMemories();
      }
    } catch {
      // handle silently
    } finally {
      setStoring(false);
    }
  }

  const displayMemories = searchResults ?? memories;

  return (
    <div className="space-y-6">
      {/* Stats Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="rounded-xl border border-gnosis-border bg-gnosis-surface p-3 text-center">
          <p className="text-2xl font-bold text-gnosis-text">{stats.total || 0}</p>
          <p className="text-xs text-gnosis-muted">Total</p>
        </div>
        {TIERS.filter((t) => t.key !== "all").map((t) => {
          const c = tierColor(t.key);
          return (
            <div key={t.key} className={`rounded-xl border ${c.border} ${c.bg} p-3 text-center`}>
              <p className={`text-2xl font-bold ${c.text}`}>
                {stats.by_tier?.[t.key] || 0}
              </p>
              <p className="text-xs text-gnosis-muted">{t.label}</p>
            </div>
          );
        })}
      </div>

      {/* Search & Actions */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gnosis-muted">⌕</span>
          <input
            type="text"
            placeholder="Search memories..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              if (!e.target.value.trim()) setSearchResults(null);
            }}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="w-full rounded-xl border border-gnosis-border bg-gnosis-surface pl-11 pr-4 py-2.5 text-sm text-gnosis-text placeholder:text-gnosis-muted focus:outline-none focus:border-gnosis-primary/50 transition-colors"
          />
        </div>
        <Button variant="secondary" size="sm" onClick={handleSearch} disabled={searching}>
          {searching ? "..." : "Search"}
        </Button>
        <Button variant="primary" size="sm" onClick={() => setShowStore(!showStore)}>
          + Store Memory
        </Button>
      </div>

      {/* Store Memory Form */}
      <AnimatePresence>
        {showStore && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            <Card className="space-y-3">
              <h3 className="text-sm font-semibold text-gnosis-text">Store New Memory</h3>
              <textarea
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                placeholder="Enter knowledge to store..."
                rows={3}
                className="w-full rounded-lg border border-gnosis-border bg-gnosis-bg px-3 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted focus:outline-none focus:border-gnosis-primary/50 resize-none"
              />
              <div className="flex items-center gap-3">
                <select
                  value={newTier}
                  onChange={(e) => setNewTier(e.target.value)}
                  className="rounded-lg border border-gnosis-border bg-gnosis-bg px-3 py-1.5 text-sm text-gnosis-text focus:outline-none focus:border-gnosis-primary/50"
                >
                  <option value="semantic">Semantic</option>
                  <option value="episodic">Episodic</option>
                  <option value="procedural">Procedural</option>
                  <option value="correction">Correction</option>
                </select>
                <Button variant="primary" size="sm" onClick={handleStore} disabled={storing || !newContent.trim()}>
                  {storing ? "Storing..." : "Store"}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setShowStore(false)}>
                  Cancel
                </Button>
              </div>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Tier Tabs */}
      <div className="flex gap-2 flex-wrap">
        {TIERS.map((t) => {
          const c = tierColor(t.key);
          return (
            <button
              key={t.key}
              onClick={() => {
                setActiveTier(t.key);
                setSearchResults(null);
                setSearch("");
              }}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 border ${
                activeTier === t.key
                  ? `${c.bg} ${c.text} ${c.border}`
                  : "border-gnosis-border text-gnosis-muted hover:text-gnosis-text"
              }`}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Memories List */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 rounded-2xl bg-gnosis-surface animate-pulse border border-gnosis-border" />
          ))}
        </div>
      ) : displayMemories.length === 0 ? (
        <div className="text-center py-12 text-gnosis-muted">
          <p className="text-3xl mb-2">🧠</p>
          <p>{searchResults !== null ? "No memories match your search." : "No memories stored yet."}</p>
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-3"
        >
          {displayMemories.map((mem, i) => {
            const c = tierColor(mem.tier);
            const relevance = mem.relevance_score ?? 0;
            const strength = mem.strength ?? 0;
            return (
              <motion.div
                key={mem.id || i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
              >
                <Card className={`border-l-2 ${c.border}`}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gnosis-text leading-relaxed line-clamp-3">
                        {mem.content}
                      </p>
                      <div className="flex items-center gap-3 mt-3 flex-wrap">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${c.bg} ${c.text}`}>
                          {mem.tier}
                        </span>
                        {mem.access_count !== undefined && (
                          <span className="text-xs text-gnosis-muted">
                            {mem.access_count} accesses
                          </span>
                        )}
                        <span className="text-xs text-gnosis-muted">
                          Created {formatTimestamp(mem.created_at)}
                        </span>
                        {mem.last_accessed && (
                          <span className="text-xs text-gnosis-muted">
                            Last accessed {formatTimestamp(mem.last_accessed)}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Score Bars */}
                    <div className="shrink-0 w-24 space-y-2">
                      <div>
                        <div className="flex justify-between text-[10px] text-gnosis-muted mb-0.5">
                          <span>Relevance</span>
                          <span>{(relevance * 100).toFixed(0)}%</span>
                        </div>
                        <div className="h-1 rounded-full bg-gnosis-border overflow-hidden">
                          <div
                            className="h-full rounded-full bg-gnosis-primary"
                            style={{ width: `${relevance * 100}%` }}
                          />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-[10px] text-gnosis-muted mb-0.5">
                          <span>Strength</span>
                          <span>{(strength * 100).toFixed(0)}%</span>
                        </div>
                        <div className="h-1 rounded-full bg-gnosis-border overflow-hidden">
                          <div
                            className={`h-full rounded-full ${c.text.replace("text-", "bg-")}`}
                            style={{ width: `${strength * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>
              </motion.div>
            );
          })}
        </motion.div>
      )}
    </div>
  );
}
