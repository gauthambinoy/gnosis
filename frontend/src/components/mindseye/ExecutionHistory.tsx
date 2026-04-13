"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card } from "@/components/shared/Card";
import { ConsciousnessViewer } from "./ConsciousnessViewer";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Types ---

type ExecutionStatus = "completed" | "failed" | "running" | "queued" | "cancelled" | "awaiting_approval";

interface CortexStep {
  phase: string;
  content: string;
  confidence: number;
  latency_ms: number;
  cost_usd: number;
  timestamp: string;
  tokens?: number;
  memories?: Array<{
    id: string;
    tier: string;
    content: string;
    relevance: number;
  }>;
}

interface Execution {
  id: string;
  trigger_type: string;
  trigger_data: Record<string, unknown>;
  status: ExecutionStatus;
  steps: CortexStep[];
  result_summary: string | null;
  error_message: string | null;
  total_latency_ms: number;
  total_tokens: number;
  total_cost_usd: number;
  reasoning_tier: string | null;
  was_corrected: string;
  created_at: string;
}

type FilterStatus = "all" | "completed" | "failed" | "running";

const STATUS_CONFIG: Record<string, { color: string; icon: string; label: string }> = {
  completed: { color: "text-gnosis-success", icon: "✓", label: "Success" },
  failed: { color: "text-gnosis-error", icon: "✗", label: "Failed" },
  running: { color: "text-gnosis-primary", icon: "◌", label: "Running" },
  queued: { color: "text-gnosis-muted", icon: "○", label: "Queued" },
  cancelled: { color: "text-gnosis-muted", icon: "⊘", label: "Cancelled" },
  awaiting_approval: { color: "text-yellow-400", icon: "⚠", label: "Awaiting" },
};

// --- Helpers ---

function buildReplayData(steps: CortexStep[]) {
  const phaseOrder = ["perceive", "memory", "context", "reason", "meta", "act"];

  const phases = steps.map((s) => ({
    phase: s.phase as "perceive" | "memory" | "context" | "reason" | "meta" | "act",
    status: "completed" as const,
    duration_ms: s.latency_ms,
    confidence: s.confidence,
    tokens: s.tokens,
  }));

  const memories = steps.flatMap(
    (s) =>
      s.memories?.map((m) => ({
        id: m.id,
        tier: m.tier as "correction" | "episodic" | "semantic" | "procedural",
        content: m.content,
        relevance: m.relevance,
      })) ?? []
  );

  const totalTokens = steps.reduce((sum, s) => sum + (s.tokens || 0), 0);
  const lastConfidence = steps.length > 0 ? steps[steps.length - 1].confidence : 0;

  const actions = steps
    .filter((s) => s.phase === "act")
    .map((s, i) => ({
      id: `replay-action-${i}`,
      action: s.content,
      status: "success" as const,
      timestamp: s.timestamp,
    }));

  // Sort phases by the canonical order
  phases.sort(
    (a, b) => phaseOrder.indexOf(a.phase) - phaseOrder.indexOf(b.phase)
  );

  return {
    phases,
    memories,
    tokens: { used: totalTokens, budget: Math.max(totalTokens, 4096) },
    confidence: lastConfidence,
    actions,
    active: false,
  };
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();

  if (diff < 60000) return "just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return d.toLocaleDateString();
}

// --- Sub-components ---

function FilterBar({
  filter,
  onChange,
  counts,
}: {
  filter: FilterStatus;
  onChange: (f: FilterStatus) => void;
  counts: Record<FilterStatus, number>;
}) {
  const filters: { key: FilterStatus; label: string }[] = [
    { key: "all", label: "All" },
    { key: "completed", label: "Success" },
    { key: "failed", label: "Failed" },
    { key: "running", label: "Running" },
  ];

  return (
    <div className="flex items-center gap-1">
      {filters.map((f) => (
        <button
          key={f.key}
          onClick={() => onChange(f.key)}
          className={`px-3 py-1 text-xs rounded-full border transition-colors ${
            filter === f.key
              ? "border-gnosis-primary/40 bg-gnosis-primary/10 text-gnosis-primary"
              : "border-gnosis-border text-gnosis-muted hover:text-gnosis-text hover:border-gnosis-border/80"
          }`}
        >
          {f.label}
          <span className="ml-1 opacity-60">{counts[f.key]}</span>
        </button>
      ))}
    </div>
  );
}

function ExecutionRow({
  execution,
  isExpanded,
  onToggle,
}: {
  execution: Execution;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const cfg = STATUS_CONFIG[execution.status] || STATUS_CONFIG.queued;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
    >
      {/* Row header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-3 rounded-xl border border-gnosis-border bg-gnosis-surface hover:border-gnosis-border/80 transition-colors text-left"
      >
        <span className={`text-sm ${cfg.color}`}>{cfg.icon}</span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gnosis-text font-medium truncate">
              {execution.trigger_type}
            </span>
            {execution.reasoning_tier && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-gnosis-primary/10 text-gnosis-primary font-mono">
                {execution.reasoning_tier}
              </span>
            )}
            {execution.was_corrected === "true" && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400">
                corrected
              </span>
            )}
          </div>
          <p className="text-xs text-gnosis-muted truncate mt-0.5">
            {execution.result_summary || execution.error_message || "No summary"}
          </p>
        </div>

        <div className="flex items-center gap-4 flex-shrink-0 text-xs text-gnosis-muted">
          <span>{formatDuration(execution.total_latency_ms)}</span>
          <span>{execution.total_tokens.toLocaleString()} tok</span>
          <span>${execution.total_cost_usd.toFixed(4)}</span>
          <span>{formatTimestamp(execution.created_at)}</span>
          <motion.span
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            className="text-gnosis-muted"
          >
            ▾
          </motion.span>
        </div>
      </button>

      {/* Expanded: Mind's Eye replay */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="mt-2 p-4 rounded-xl bg-gnosis-bg border border-gnosis-border">
              <h4 className="text-xs text-gnosis-muted uppercase tracking-wider mb-3">
                Mind&apos;s Eye Replay
              </h4>
              <ConsciousnessViewer
                agentId={execution.id}
                replayData={buildReplayData(execution.steps || [])}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// --- Main Component ---

interface ExecutionHistoryProps {
  agentId: string;
}

export function ExecutionHistory({ agentId }: ExecutionHistoryProps) {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterStatus>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchExecutions = useCallback(async () => {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/agents/${agentId}/executions`
      );
      if (res.ok) {
        const data = await res.json();
        setExecutions(Array.isArray(data) ? data : data.executions || []);
      }
    } catch {
      // API not available
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    fetchExecutions();
  }, [fetchExecutions]);

  const filtered =
    filter === "all"
      ? executions
      : executions.filter((e) => {
          if (filter === "completed") return e.status === "completed";
          if (filter === "failed") return e.status === "failed" || e.status === "cancelled";
          if (filter === "running") return e.status === "running" || e.status === "queued";
          return true;
        });

  const counts: Record<FilterStatus, number> = {
    all: executions.length,
    completed: executions.filter((e) => e.status === "completed").length,
    failed: executions.filter((e) => e.status === "failed" || e.status === "cancelled").length,
    running: executions.filter((e) => e.status === "running" || e.status === "queued").length,
  };

  if (loading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-16 rounded-xl bg-gnosis-surface animate-pulse border border-gnosis-border"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gnosis-text">
          Execution History
        </h3>
        <FilterBar filter={filter} onChange={setFilter} counts={counts} />
      </div>

      {filtered.length === 0 ? (
        <Card className="text-center py-8">
          <p className="text-gnosis-muted text-sm">
            {executions.length === 0
              ? "No executions yet"
              : "No executions match this filter"}
          </p>
        </Card>
      ) : (
        <div className="space-y-2">
          <AnimatePresence mode="popLayout">
            {filtered.map((exec) => (
              <ExecutionRow
                key={exec.id}
                execution={exec}
                isExpanded={expandedId === exec.id}
                onToggle={() =>
                  setExpandedId((prev) => (prev === exec.id ? null : exec.id))
                }
              />
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
