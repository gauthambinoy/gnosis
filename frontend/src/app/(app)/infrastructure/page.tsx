"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { clsx } from "clsx";
import { api } from "@/lib/api";

/* ---------- Types ---------- */

interface HealthData {
  status?: string;
  version?: string;
  response_time_ms?: number;
  database?: { status?: string; pool_size?: number; pool_available?: number };
  cache?: { status?: string; memory_used_mb?: number };
  task_worker?: { status?: string; tasks_processed?: number };
  scheduler?: { status?: string; active_schedules?: number };
  uptime?: string;
  total_routes?: number;
}

interface SystemStatus {
  total_requests?: number;
  error_rate?: number;
  uptime?: string;
  total_routes?: number;
}

interface LLMStats {
  provider?: string;
  model?: string;
  tokens_used?: number;
  cost?: number;
  status?: string;
}

interface AWSStatus {
  s3?: { status?: string };
  sqs?: { status?: string };
  ses?: { status?: string };
  dynamodb?: { status?: string };
  [key: string]: { status?: string } | undefined;
}

type OverallStatus = "operational" | "degraded" | "outage" | "loading";

/* ---------- Helpers ---------- */

function StatusDot({ status }: { status: string | undefined }) {
  const color =
    status === "connected" || status === "healthy" || status === "running" || status === "ok" || status === "active" || status === "operational"
      ? "bg-emerald-400 shadow-emerald-400/40"
      : status === "degraded"
        ? "bg-yellow-400 shadow-yellow-400/40"
        : status === "unavailable" || status === undefined
          ? "bg-white/20"
          : "bg-red-400 shadow-red-400/40";
  return <span className={clsx("inline-block w-2.5 h-2.5 rounded-full shadow-lg shrink-0", color)} />;
}

function safeFetch<T>(path: string): Promise<T | null> {
  return api.get(path)
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null);
}

const cardVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: (i: number) => ({ opacity: 1, y: 0, transition: { delay: i * 0.07, duration: 0.4, ease: [0.4, 0, 0.2, 1] } }),
};

/* ---------- Component ---------- */

export default function InfrastructurePage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [llm, setLLM] = useState<LLMStats | null>(null);
  const [aws, setAWS] = useState<AWSStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [testingLLM, setTestingLLM] = useState(false);
  const [llmTestResult, setLLMTestResult] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    const [h, s, l, a] = await Promise.all([
      safeFetch<HealthData>("/health"),
      safeFetch<SystemStatus>("/system/status"),
      safeFetch<LLMStats>("/llm/stats"),
      safeFetch<AWSStatus>("/aws/status"),
    ]);
    setHealth(h);
    setSystem(s);
    setLLM(l);
    setAWS(a);
    setLastChecked(new Date());
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  /* Derive overall status */
  const overall: OverallStatus = loading
    ? "loading"
    : !health
      ? "outage"
      : health.status === "healthy" || health.status === "ok"
        ? "operational"
        : "degraded";

  const overallLabel: Record<OverallStatus, string> = {
    operational: "All Systems Operational",
    degraded: "Degraded Performance",
    outage: "Major Outage",
    loading: "Checking…",
  };

  const overallColor: Record<OverallStatus, string> = {
    operational: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    degraded: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    outage: "bg-red-500/10 text-red-400 border-red-500/20",
    loading: "bg-white/5 text-gnosis-muted border-white/10",
  };

  async function testLLM() {
    setTestingLLM(true);
    setLLMTestResult(null);
    try {
      const res = await api.post("/llm/test");
      if (res.ok) {
        const data = await res.json();
        setLLMTestResult(data.message || "Connection successful ✓");
      } else {
        setLLMTestResult("Test failed — check API keys");
      }
    } catch {
      setLLMTestResult("Connection error");
    } finally {
      setTestingLLM(false);
    }
  }

  /* ---- Service card data ---- */
  const services = [
    {
      title: "API Server",
      icon: "⚡",
      status: health?.status === "healthy" || health?.status === "ok" ? "operational" : health ? "degraded" : undefined,
      rows: [
        { label: "Status", value: health?.status ?? "Unavailable" },
        { label: "Response Time", value: health?.response_time_ms != null ? `${health.response_time_ms}ms` : "—" },
        { label: "Version", value: health?.version ?? "—" },
      ],
    },
    {
      title: "Database (PostgreSQL)",
      icon: "🗄️",
      status: health?.database?.status ?? undefined,
      rows: [
        { label: "Connection", value: health?.database?.status ?? "Unavailable" },
        { label: "Pool Size", value: health?.database?.pool_size?.toString() ?? "—" },
        { label: "Available", value: health?.database?.pool_available?.toString() ?? "—" },
      ],
    },
    {
      title: "Cache (Redis)",
      icon: "🔴",
      status: health?.cache?.status ?? undefined,
      rows: [
        { label: "Connection", value: health?.cache?.status ?? "Unavailable" },
        { label: "Memory Used", value: health?.cache?.memory_used_mb != null ? `${health.cache.memory_used_mb} MB` : "—" },
      ],
    },
    {
      title: "LLM Gateway",
      icon: "🤖",
      status: llm?.status ?? (llm ? "connected" : undefined),
      rows: [
        { label: "Provider", value: llm?.provider ?? "Unavailable" },
        { label: "Model", value: llm?.model ?? "—" },
        { label: "Tokens Used", value: llm?.tokens_used?.toLocaleString() ?? "—" },
        { label: "Cost", value: llm?.cost != null ? `$${llm.cost.toFixed(4)}` : "—" },
      ],
    },
    {
      title: "AWS Services",
      icon: "☁️",
      status: aws
        ? Object.values(aws).every((v) => v && typeof v === "object" && (v.status === "ok" || v.status === "connected" || v.status === "operational"))
          ? "operational"
          : "degraded"
        : undefined,
      rows: ["s3", "sqs", "ses", "dynamodb"].map((svc) => ({
        label: svc.toUpperCase(),
        value: aws?.[svc]?.status ?? "Unavailable",
      })),
    },
    {
      title: "Task Worker",
      icon: "⚙️",
      status: health?.task_worker?.status ?? undefined,
      rows: [
        { label: "Status", value: health?.task_worker?.status ?? "Unavailable" },
        { label: "Tasks Processed", value: health?.task_worker?.tasks_processed?.toLocaleString() ?? "—" },
      ],
    },
    {
      title: "Scheduler",
      icon: "🕐",
      status: health?.scheduler?.status ?? undefined,
      rows: [
        { label: "Status", value: health?.scheduler?.status ?? "Unavailable" },
        { label: "Active Schedules", value: health?.scheduler?.active_schedules?.toString() ?? "—" },
      ],
    },
  ];

  /* ---- Metrics ---- */
  const metrics = [
    { label: "Total API Routes", value: health?.total_routes ?? system?.total_routes ?? "—" },
    { label: "Uptime", value: health?.uptime ?? system?.uptime ?? "—" },
    { label: "Total Requests", value: system?.total_requests?.toLocaleString() ?? "—" },
    { label: "Error Rate", value: system?.error_rate != null ? `${(system.error_rate * 100).toFixed(2)}%` : "—" },
  ];

  /* ---- Loading state ---- */
  if (loading && !health) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-gnosis-muted">Checking infrastructure…</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-bold text-gnosis-text">
            🏗️ Infrastructure Status
          </h1>
          <p className="text-gnosis-muted mt-1">
            Real-time health monitoring for all Gnosis services
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <span className={clsx("inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border", overallColor[overall])}>
            <span className={clsx(
              "w-2 h-2 rounded-full",
              overall === "operational" ? "bg-emerald-400" : overall === "degraded" ? "bg-yellow-400" : overall === "outage" ? "bg-red-400" : "bg-white/30",
            )} />
            {overallLabel[overall]}
          </span>
          {lastChecked && (
            <span className="text-xs text-gnosis-muted">
              Last checked: {lastChecked.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* Service Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {services.map((svc, i) => (
          <motion.div
            key={svc.title}
            custom={i}
            variants={cardVariants}
            initial="hidden"
            animate="visible"
            className="p-5 rounded-2xl border border-gnosis-border bg-gnosis-surface hover:border-gnosis-primary/20 transition-colors"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="text-lg">{svc.icon}</span>
                <h3 className="text-sm font-semibold text-gnosis-text">{svc.title}</h3>
              </div>
              <StatusDot status={svc.status} />
            </div>
            <div className="space-y-2">
              {svc.rows.map((row) => (
                <div key={row.label} className="flex justify-between text-xs">
                  <span className="text-gnosis-muted">{row.label}</span>
                  <span className="text-gnosis-text font-medium">{row.value}</span>
                </div>
              ))}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Metrics Section */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <h2 className="text-lg font-semibold text-gnosis-text mb-4">System Metrics</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {metrics.map((m, i) => (
            <motion.div
              key={m.label}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.6 + i * 0.05 }}
              className="p-4 rounded-2xl border border-gnosis-border bg-gnosis-surface text-center"
            >
              <p className="text-xs text-gnosis-muted mb-1">{m.label}</p>
              <p className="text-xl font-display font-bold text-gnosis-primary">{m.value}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7 }}
        className="p-6 rounded-2xl border border-gnosis-border bg-gnosis-surface"
      >
        <h2 className="text-lg font-semibold text-gnosis-text mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-3 items-center">
          <button
            onClick={fetchAll}
            disabled={loading}
            className="px-4 py-2 rounded-xl text-sm font-medium bg-gnosis-primary text-black hover:brightness-110 transition-all disabled:opacity-50"
          >
            {loading ? "Refreshing…" : "↻ Refresh All"}
          </button>
          <button
            onClick={testLLM}
            disabled={testingLLM}
            className="px-4 py-2 rounded-xl text-sm font-medium border border-gnosis-primary/40 text-gnosis-primary hover:bg-gnosis-primary/10 transition-all disabled:opacity-50"
          >
            {testingLLM ? "Testing…" : "🤖 Test LLM Connection"}
          </button>
          {llmTestResult && (
            <span className={clsx(
              "text-xs px-3 py-1.5 rounded-full",
              llmTestResult.includes("✓") || llmTestResult.includes("successful")
                ? "bg-emerald-500/10 text-emerald-400"
                : "bg-red-500/10 text-red-400",
            )}>
              {llmTestResult}
            </span>
          )}
        </div>
      </motion.div>
    </div>
  );
}
