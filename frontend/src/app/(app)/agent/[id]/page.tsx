"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Card } from "@/components/shared/Card";
import { Badge } from "@/components/shared/Badge";
import { ConsciousnessViewer } from "@/components/mindseye/ConsciousnessViewer";
import { ExecutionHistory } from "@/components/mindseye/ExecutionHistory";

const TRUST_LABELS = ["Observer", "Apprentice", "Associate", "Autonomous"];
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type TabId = "consciousness" | "history" | "memory" | "stats";

interface AgentData {
  name: string;
  description: string;
  status: string;
  avatar_emoji: string;
  trust_level: number;
  total_actions: number;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  total_corrections: number;
  accuracy: number;
  avg_latency_ms: number;
  total_tokens_used: number;
  total_cost_usd: number;
  time_saved_minutes: number;
  memory_count: number;
}

interface MemoryEntry {
  id: string;
  tier: "correction" | "episodic" | "semantic" | "procedural";
  content: string;
  importance_score: number;
  access_count: number;
  tags: string[];
  created_at: string;
}

const TIER_STYLES: Record<string, { bg: string; text: string }> = {
  correction: { bg: "bg-red-500/15", text: "text-red-400" },
  episodic: { bg: "bg-blue-500/15", text: "text-blue-400" },
  semantic: { bg: "bg-purple-500/15", text: "text-purple-400" },
  procedural: { bg: "bg-green-500/15", text: "text-green-400" },
};

// --- Tab Navigation ---

function TabBar({ active, onChange }: { active: TabId; onChange: (t: TabId) => void }) {
  const tabs: { id: TabId; label: string; icon: string }[] = [
    { id: "consciousness", label: "Mind's Eye", icon: "👁" },
    { id: "history", label: "Executions", icon: "📜" },
    { id: "memory", label: "Memory", icon: "🧠" },
    { id: "stats", label: "Stats", icon: "📊" },
  ];

  return (
    <div className="flex items-center gap-1 border-b border-gnosis-border pb-px">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`relative px-4 py-2 text-sm transition-colors ${
            active === tab.id ? "text-gnosis-primary" : "text-gnosis-muted hover:text-gnosis-text"
          }`}
        >
          <span className="mr-1.5">{tab.icon}</span>
          {tab.label}
          {active === tab.id && (
            <motion.div
              layoutId="agent-tab-indicator"
              className="absolute bottom-0 left-0 right-0 h-px bg-gnosis-primary"
            />
          )}
        </button>
      ))}
    </div>
  );
}

// --- Memory Explorer ---

function MemoryExplorer({ agentId }: { agentId: string }) {
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState<string>("all");

  const fetchMemories = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.set("q", search);
      if (tierFilter !== "all") params.set("tier", tierFilter);
      const res = await fetch(`${API_URL}/api/v1/memory/${agentId}?${params}`);
      if (res.ok) {
        const data = await res.json();
        setMemories(Array.isArray(data) ? data : data.memories || []);
      }
    } catch {
      // API not available
    } finally {
      setLoading(false);
    }
  }, [agentId, search, tierFilter]);

  useEffect(() => {
    fetchMemories();
  }, [fetchMemories]);

  const tiers = ["all", "correction", "episodic", "semantic", "procedural"];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <input
            type="text"
            placeholder="Search memories..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-gnosis-bg border border-gnosis-border rounded-lg px-3 py-2 text-sm text-gnosis-text placeholder:text-gnosis-muted/50 focus:outline-none focus:border-gnosis-primary/40"
          />
        </div>
        <div className="flex items-center gap-1">
          {tiers.map((tier) => (
            <button
              key={tier}
              onClick={() => setTierFilter(tier)}
              className={`px-2.5 py-1 text-xs rounded-full border transition-colors capitalize ${
                tierFilter === tier
                  ? "border-gnosis-primary/40 bg-gnosis-primary/10 text-gnosis-primary"
                  : "border-gnosis-border text-gnosis-muted hover:text-gnosis-text"
              }`}
            >
              {tier}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-16 rounded-xl bg-gnosis-surface animate-pulse border border-gnosis-border" />
          ))}
        </div>
      ) : memories.length === 0 ? (
        <Card className="text-center py-8">
          <p className="text-gnosis-muted text-sm">No memories found</p>
        </Card>
      ) : (
        <div className="space-y-2">
          <AnimatePresence mode="popLayout">
            {memories.map((mem) => {
              const style = TIER_STYLES[mem.tier] || TIER_STYLES.episodic;
              return (
                <motion.div
                  key={mem.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="p-3 rounded-xl border border-gnosis-border bg-gnosis-surface"
                >
                  <div className="flex items-start gap-2">
                    <span className={`${style.bg} ${style.text} text-[10px] font-medium px-1.5 py-0.5 rounded-full flex-shrink-0 mt-0.5`}>
                      {mem.tier}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gnosis-text/90">{mem.content}</p>
                      <div className="flex items-center gap-3 mt-1.5 text-[10px] text-gnosis-muted">
                        <span>importance: {mem.importance_score.toFixed(2)}</span>
                        <span>accessed: {mem.access_count}×</span>
                        {mem.tags?.length > 0 && (
                          <span>{mem.tags.join(", ")}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

// --- Stats Panel ---

function StatsPanel({ agent }: { agent: AgentData }) {
  const stats = [
    { label: "Total Executions", value: agent.total_executions || 0, fmt: (v: number) => v.toLocaleString() },
    { label: "Successful", value: agent.successful_executions || 0, fmt: (v: number) => v.toLocaleString(), color: "text-gnosis-success" },
    { label: "Failed", value: agent.failed_executions || 0, fmt: (v: number) => v.toLocaleString(), color: "text-gnosis-error" },
    { label: "Corrections", value: agent.total_corrections || 0, fmt: (v: number) => v.toLocaleString(), color: "text-yellow-400" },
    { label: "Accuracy", value: agent.accuracy || 0, fmt: (v: number) => (v * 100).toFixed(1) + "%" },
    { label: "Avg Latency", value: agent.avg_latency_ms || 0, fmt: (v: number) => v < 1000 ? `${Math.round(v)}ms` : `${(v / 1000).toFixed(1)}s` },
    { label: "Total Tokens", value: agent.total_tokens_used || 0, fmt: (v: number) => v.toLocaleString() },
    { label: "Total Cost", value: agent.total_cost_usd || 0, fmt: (v: number) => `$${v.toFixed(4)}` },
    { label: "Time Saved", value: agent.time_saved_minutes || 0, fmt: (v: number) => `${v.toFixed(0)}m` },
    { label: "Memories", value: agent.memory_count || 0, fmt: (v: number) => v.toLocaleString() },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {stats.map((stat, i) => (
        <motion.div
          key={stat.label}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.04 }}
        >
          <Card className="text-center py-3 px-2">
            <p className={`text-lg font-bold font-mono ${(stat as { color?: string }).color || "text-gnosis-text"}`}>
              {stat.fmt(stat.value)}
            </p>
            <p className="text-[10px] text-gnosis-muted mt-1">{stat.label}</p>
          </Card>
        </motion.div>
      ))}
    </div>
  );
}

// --- Main Page ---

export default function AgentDetailPage() {
  const params = useParams();
  const agentId = params?.id as string;
  const [agent, setAgent] = useState<AgentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabId>("consciousness");
  const [executing, setExecuting] = useState(false);

  useEffect(() => {
    async function fetchAgent() {
      try {
        const res = await fetch(API_URL + "/api/v1/agents/" + agentId);
        if (res.ok) setAgent(await res.json());
      } catch {
        // API not available yet
      } finally {
        setLoading(false);
      }
    }
    if (agentId) fetchAgent();
  }, [agentId]);

  const handleExecute = async () => {
    setExecuting(true);
    try {
      await fetch(`${API_URL}/api/v1/execute/${agentId}`, { method: "POST" });
      setActiveTab("consciousness");
    } catch {
      // handle error
    } finally {
      setExecuting(false);
    }
  };

  const handleCorrect = async () => {
    const correction = prompt("Describe the correction:");
    if (!correction) return;
    try {
      await fetch(`${API_URL}/api/v1/agents/${agentId}/correct`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ correction }),
      });
    } catch {
      // handle error
    }
  };

  if (loading) {
    return <div className="h-96 rounded-2xl bg-gnosis-surface animate-pulse border border-gnosis-border" />;
  }

  if (!agent) {
    return (
      <Card className="text-center py-16">
        <p className="text-gnosis-muted">Agent not found</p>
      </Card>
    );
  }

  const trustLevel = agent.trust_level || 0;
  const totalActions = agent.total_actions || agent.total_executions || 0;
  const accuracy = agent.accuracy || 0;
  const timeSavedMinutes = agent.time_saved_minutes || 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4 mb-2">
            <span className="text-4xl">{agent.avatar_emoji || "◎"}</span>
            <div>
              <h1 className="font-display text-3xl font-bold text-gnosis-text">{agent.name}</h1>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-sm text-gnosis-primary">{TRUST_LABELS[trustLevel]}</span>
                <span className="text-gnosis-muted">·</span>
                <Badge variant={agent.status === "active" ? "success" : agent.status === "error" ? "error" : "default"}>
                  {agent.status}
                </Badge>
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleCorrect}
              className="px-4 py-2 text-sm rounded-lg border border-gnosis-border text-gnosis-muted hover:text-gnosis-text hover:border-gnosis-border/80 transition-colors"
            >
              ✏️ Correct
            </button>
            <button
              onClick={handleExecute}
              disabled={executing}
              className="px-4 py-2 text-sm rounded-lg bg-gnosis-primary text-gnosis-bg font-medium hover:bg-gnosis-primary/90 disabled:opacity-50 transition-colors"
            >
              {executing ? "Executing..." : "⚡ Execute Now"}
            </button>
          </div>
        </div>
        <p className="text-gnosis-muted mt-1">{agent.description}</p>
      </motion.div>

      {/* Metric cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Executions", value: totalActions },
          { label: "Accuracy", value: (accuracy * 100).toFixed(1) + "%" },
          { label: "Time Saved", value: timeSavedMinutes.toFixed(0) + "m" },
          { label: "Trust Level", value: "L" + trustLevel },
        ].map((m, i) => (
          <motion.div key={m.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>
            <Card className="text-center">
              <p className="text-2xl font-bold text-gnosis-text">{m.value}</p>
              <p className="text-xs text-gnosis-muted mt-1">{m.label}</p>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Tabs */}
      <TabBar active={activeTab} onChange={setActiveTab} />

      {/* Tab content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
        >
          {activeTab === "consciousness" && (
            <Card>
              <h2 className="font-semibold text-gnosis-text mb-4">Mind&apos;s Eye — Consciousness Stream</h2>
              <ConsciousnessViewer agentId={agentId} />
            </Card>
          )}

          {activeTab === "history" && <ExecutionHistory agentId={agentId} />}

          {activeTab === "memory" && <MemoryExplorer agentId={agentId} />}

          {activeTab === "stats" && <StatsPanel agent={agent} />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
