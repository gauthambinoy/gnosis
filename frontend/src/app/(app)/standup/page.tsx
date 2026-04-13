"use client";

import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Card } from "@/components/shared/Card";
import { Badge } from "@/components/shared/Badge";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface StandupAgent {
  id: string;
  name: string;
  emoji: string;
  summary: string;
  executions: number;
  successes: number;
  failures: number;
  cost_usd: number;
}

interface NotableEvent {
  message: string;
  severity: "info" | "warning" | "error" | "success";
  timestamp: string;
  agent_name?: string;
}

interface StandupData {
  date: string;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  total_cost_usd: number;
  time_saved_minutes: number;
  top_agent: string | null;
  agents: StandupAgent[];
  notable_events: NotableEvent[];
}

function AnimatedCounter({ value, duration = 1200 }: { value: number; duration?: number }) {
  const [display, setDisplay] = useState(0);
  const ref = useRef<number | null>(null);

  useEffect(() => {
    const start = performance.now();
    const from = 0;
    function tick(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(from + (value - from) * eased));
      if (progress < 1) {
        ref.current = requestAnimationFrame(tick);
      }
    }
    ref.current = requestAnimationFrame(tick);
    return () => {
      if (ref.current) cancelAnimationFrame(ref.current);
    };
  }, [value, duration]);

  return <>{display}</>;
}

const SEVERITY_CONFIG: Record<string, { variant: "success" | "warning" | "error" | "default"; icon: string }> = {
  info: { variant: "default", icon: "ℹ️" },
  warning: { variant: "warning", icon: "⚠️" },
  error: { variant: "error", icon: "🔴" },
  success: { variant: "success", icon: "✅" },
};

export default function StandupPage() {
  const [standup, setStandup] = useState<StandupData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStandup() {
      try {
        const res = await fetch(`${API_URL}/api/v1/standup/daily`);
        if (res.ok) {
          setStandup(await res.json());
        }
      } catch {
        // API not available yet
      } finally {
        setLoading(false);
      }
    }
    fetchStandup();
  }, []);

  const totalExec = standup?.total_executions ?? 0;
  const successes = standup?.successful_executions ?? 0;
  const failures = standup?.failed_executions ?? 0;
  const successRate = totalExec > 0 ? ((successes / totalExec) * 100) : 0;
  const topAgent = standup?.top_agent ?? "—";
  const cost = standup?.total_cost_usd ?? 0;
  const timeSaved = standup?.time_saved_minutes ?? 0;
  const agents = standup?.agents ?? [];
  const events = standup?.notable_events ?? [];

  const statCards = [
    { label: "Executions (24h)", value: totalExec, suffix: "" },
    { label: "Success Rate", value: Math.round(successRate), suffix: "%" },
    { label: "Failures", value: failures, suffix: "" },
    { label: "Time Saved", value: Math.round(timeSaved), suffix: "m" },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-gnosis-text">◈ Morning Standup</h1>
        <p className="text-gnosis-muted mt-1">
          Daily briefing from your agent network —{" "}
          {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 rounded-2xl bg-gnosis-surface animate-pulse border border-gnosis-border" />
          ))}
        </div>
      ) : (
        <>
          {/* Stats Grid */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid grid-cols-2 lg:grid-cols-4 gap-4"
          >
            {statCards.map((s, i) => (
              <motion.div
                key={s.label}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }}
              >
                <Card className="text-center">
                  <p className="text-3xl font-bold text-gnosis-primary">
                    <AnimatedCounter value={s.value} />
                    {s.suffix}
                  </p>
                  <p className="text-xs text-gnosis-muted mt-1">{s.label}</p>
                </Card>
              </motion.div>
            ))}
          </motion.div>

          {/* Summary Row */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            <Card>
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-xs text-gnosis-muted">Top Agent</p>
                  <p className="font-semibold text-gnosis-text">{topAgent}</p>
                </div>
                <div>
                  <p className="text-xs text-gnosis-muted">Total Cost</p>
                  <p className="font-semibold text-gnosis-gold">${cost.toFixed(4)}</p>
                </div>
                <div>
                  <p className="text-xs text-gnosis-muted">Success / Fail</p>
                  <p className="font-semibold">
                    <span className="text-gnosis-success">{successes}</span>
                    {" / "}
                    <span className="text-gnosis-error">{failures}</span>
                  </p>
                </div>
              </div>
            </Card>
          </motion.div>

          {/* Notable Events */}
          {events.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <h2 className="text-lg font-semibold text-gnosis-text mb-3">Notable Events</h2>
              <div className="space-y-2">
                {events.map((evt, i) => {
                  const config = SEVERITY_CONFIG[evt.severity] || SEVERITY_CONFIG.info;
                  return (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.45 + i * 0.05 }}
                    >
                      <Card className="flex items-center gap-3 !py-3">
                        <span>{config.icon}</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gnosis-text">{evt.message}</p>
                          <p className="text-xs text-gnosis-muted">
                            {evt.agent_name && `${evt.agent_name} · `}
                            {new Date(evt.timestamp).toLocaleTimeString()}
                          </p>
                        </div>
                        <Badge variant={config.variant}>{evt.severity}</Badge>
                      </Card>
                    </motion.div>
                  );
                })}
              </div>
            </motion.div>
          )}

          {/* Per-Agent Breakdown */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <h2 className="text-lg font-semibold text-gnosis-text mb-3">Agent Breakdown</h2>
            {agents.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {agents.map((agent, i) => {
                  const agentRate = agent.executions > 0 ? (agent.successes / agent.executions) * 100 : 0;
                  return (
                    <motion.div
                      key={agent.id || i}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.55 + i * 0.06 }}
                    >
                      <Card glow>
                        <div className="flex items-start gap-3">
                          <span className="text-2xl">{agent.emoji || "◎"}</span>
                          <div className="flex-1 min-w-0">
                            <h3 className="font-semibold text-gnosis-text">{agent.name}</h3>
                            <p className="text-sm text-gnosis-muted mt-1 line-clamp-2">{agent.summary}</p>
                            <div className="flex items-center gap-4 mt-3 text-xs text-gnosis-muted">
                              <span>{agent.executions} runs</span>
                              <span className="text-gnosis-success">{agent.successes} ✓</span>
                              {agent.failures > 0 && (
                                <span className="text-gnosis-error">{agent.failures} ✗</span>
                              )}
                              <span className="text-gnosis-gold">${agent.cost_usd.toFixed(4)}</span>
                            </div>
                            {/* Success bar */}
                            <div className="mt-2 h-1 rounded-full bg-gnosis-border overflow-hidden">
                              <div
                                className="h-full rounded-full bg-gnosis-success"
                                style={{ width: `${agentRate}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      </Card>
                    </motion.div>
                  );
                })}
              </div>
            ) : (
              <Card>
                <p className="text-gnosis-muted text-center py-8">
                  No agent activity yet. Create your first agent to see daily standups.
                </p>
              </Card>
            )}
          </motion.div>
        </>
      )}
    </div>
  );
}
