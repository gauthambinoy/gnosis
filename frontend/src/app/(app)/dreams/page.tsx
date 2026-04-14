"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

// ─── Types ───
interface DreamScenario {
  id: string;
  agent_id: string;
  scenario_type: string;
  description: string;
  input_prompt: string;
  simulated_response: string;
  original_response: string;
  improvement_score: number;
  insights: string[];
  dreamed_at: number;
  duration_ms: number;
}

interface DreamSession {
  id: string;
  agent_id: string;
  started_at: number;
  ended_at: number;
  status: string;
  scenarios_played: number;
  insights_discovered: number;
  prompt_improvements: Record<string, unknown>[];
  memory_consolidations: number;
  dreams: DreamScenario[];
  summary: string;
}

interface EvolutionRecord {
  id: string;
  agent_id: string;
  timestamp: number;
  original_prompt: string;
  evolved_prompt: string;
  reason: string;
  performance_before: number;
  performance_after: number;
  generation: number;
  accepted: boolean;
}

interface DreamStats {
  total_dream_sessions: number;
  agents_dreaming_now: number;
  total_evolutions: number;
  accepted_evolutions: number;
  agents_with_dreams: number;
  total_performance_records: number;
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const DREAM_PHASES = [
  { key: "replay", label: "Memory Replay", icon: "🔄", color: "text-blue-400" },
  { key: "variation", label: "Variations", icon: "🔀", color: "text-yellow-400" },
  { key: "novel", label: "Novel Scenarios", icon: "💡", color: "text-emerald-400" },
  { key: "adversarial", label: "Adversarial", icon: "⚔️", color: "text-red-400" },
  { key: "consolidation", label: "Consolidation", icon: "🧠", color: "text-purple-400" },
  { key: "evolution", label: "Evolution", icon: "🧬", color: "text-cyan-400" },
];

const TYPE_ICONS: Record<string, string> = {
  replay: "🔄",
  variation: "🔀",
  novel: "💡",
  adversarial: "⚔️",
  consolidation: "🧠",
};

// ─── Particle Background ───
function ParticleField() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {/* Stars */}
      {Array.from({ length: 60 }).map((_, i) => (
        <div
          key={i}
          className="absolute rounded-full bg-white/20"
          style={{
            width: `${Math.random() * 2 + 1}px`,
            height: `${Math.random() * 2 + 1}px`,
            top: `${Math.random() * 100}%`,
            left: `${Math.random() * 100}%`,
            animation: `twinkle ${3 + Math.random() * 4}s ease-in-out infinite`,
            animationDelay: `${Math.random() * 5}s`,
          }}
        />
      ))}
      {/* Nebula glows */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-purple-600/5 blur-3xl animate-pulse" style={{ animationDuration: "8s" }} />
      <div className="absolute bottom-1/3 right-1/4 w-80 h-80 rounded-full bg-blue-600/5 blur-3xl animate-pulse" style={{ animationDuration: "12s" }} />
      <div className="absolute top-2/3 left-1/2 w-64 h-64 rounded-full bg-emerald-600/5 blur-3xl animate-pulse" style={{ animationDuration: "10s" }} />
      <style jsx>{`
        @keyframes twinkle {
          0%, 100% { opacity: 0.2; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}

// ─── Improvement Score Bar ───
function ScoreBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, (score + 1) * 50));
  const color = score > 0.5 ? "bg-emerald-500" : score > 0.2 ? "bg-yellow-500" : "bg-blue-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className={`h-full rounded-full ${color}`}
        />
      </div>
      <span className="text-xs text-gnosis-muted font-mono w-10 text-right">{(score * 100).toFixed(0)}%</span>
    </div>
  );
}

// ─── Dream Card ───
function DreamCard({ dream, index }: { dream: DreamScenario; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className="relative p-4 rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm hover:border-purple-500/30 transition-all group"
    >
      <div className="flex items-start gap-3">
        <span className="text-xl mt-0.5">{TYPE_ICONS[dream.scenario_type] || "🌀"}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 font-mono">
              {dream.scenario_type}
            </span>
            <span className="text-xs text-gnosis-muted font-mono">{dream.duration_ms.toFixed(0)}ms</span>
          </div>
          <p className="text-sm text-gnosis-text/90 leading-relaxed">{dream.description}</p>
          {dream.insights && dream.insights.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {dream.insights.map((insight, i) => (
                <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  💡 {insight}
                </span>
              ))}
            </div>
          )}
          <div className="mt-2">
            <ScoreBar score={dream.improvement_score} />
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ─── Evolution Card ───
function EvolutionCard({
  evolution,
  onAccept,
  onReject,
}: {
  evolution: EvolutionRecord;
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
}) {
  const [showDiff, setShowDiff] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="relative pl-8 pb-8 border-l-2 border-purple-500/30 last:pb-0"
    >
      {/* Timeline dot */}
      <div className="absolute left-0 top-0 -translate-x-[9px] w-4 h-4 rounded-full bg-gnosis-bg border-2 border-purple-500 flex items-center justify-center">
        <div className={`w-2 h-2 rounded-full ${evolution.accepted ? "bg-emerald-400" : "bg-purple-400"}`} />
      </div>

      <div className="p-4 rounded-xl border border-white/[0.06] bg-white/[0.02]">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 font-mono font-bold">
            Gen {evolution.generation}
          </span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400">
            🧬 {evolution.reason.split("—")[0]?.trim()}
          </span>
          {evolution.accepted && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400">
              ✅ Accepted
            </span>
          )}
        </div>
        <p className="text-sm text-gnosis-muted mb-3">{evolution.reason}</p>

        <button
          onClick={() => setShowDiff(!showDiff)}
          className="text-xs text-purple-400 hover:text-purple-300 underline underline-offset-2 mb-2"
        >
          {showDiff ? "Hide" : "Show"} prompt diff
        </button>

        <AnimatePresence>
          {showDiff && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="grid grid-cols-2 gap-2 mt-2">
                <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/10">
                  <p className="text-xs text-red-400 font-mono mb-1">Original</p>
                  <p className="text-xs text-gnosis-muted font-mono whitespace-pre-wrap break-all leading-relaxed">
                    {evolution.original_prompt.slice(0, 300)}{evolution.original_prompt.length > 300 ? "…" : ""}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                  <p className="text-xs text-emerald-400 font-mono mb-1">Evolved</p>
                  <p className="text-xs text-gnosis-muted font-mono whitespace-pre-wrap break-all leading-relaxed">
                    {evolution.evolved_prompt.slice(0, 300)}{evolution.evolved_prompt.length > 300 ? "…" : ""}
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {!evolution.accepted && (
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => onAccept(evolution.id)}
              className="px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 text-xs font-medium hover:bg-emerald-500/20 transition-colors border border-emerald-500/20"
            >
              ✅ Accept Evolution
            </button>
            <button
              onClick={() => onReject(evolution.id)}
              className="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 text-xs font-medium hover:bg-red-500/20 transition-colors border border-red-500/20"
            >
              ✗ Reject
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ─── Phase Indicator ───
function PhaseIndicator({ dreams }: { dreams: DreamScenario[] }) {
  const completedTypes = new Set(dreams.map((d) => d.scenario_type));

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {DREAM_PHASES.map((phase, i) => {
        const done = completedTypes.has(phase.key);
        return (
          <div key={phase.key} className="flex items-center gap-1">
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                done
                  ? "bg-purple-500/15 text-purple-300 border border-purple-500/30"
                  : "bg-white/[0.03] text-gnosis-muted border border-white/[0.05]"
              }`}
            >
              <span>{phase.icon}</span>
              <span className="hidden sm:inline">{phase.label}</span>
            </div>
            {i < DREAM_PHASES.length - 1 && (
              <span className="text-white/10 text-xs">→</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Main Page ───
export default function DreamsPage() {
  const [agentId, setAgentId] = useState("agent-1");
  const [customAgent, setCustomAgent] = useState("");
  const [isDreaming, setIsDreaming] = useState(false);
  const [currentSession, setCurrentSession] = useState<DreamSession | null>(null);
  const [sessions, setSessions] = useState<DreamSession[]>([]);
  const [evolutions, setEvolutions] = useState<EvolutionRecord[]>([]);
  const [stats, setStats] = useState<DreamStats | null>(null);
  const [activeTab, setActiveTab] = useState<"dreams" | "evolutions" | "history">("dreams");
  const [error, setError] = useState("");

  const selectedAgent = customAgent || agentId;

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/dreams/${selectedAgent}/status`);
      if (res.ok) {
        const data = await res.json();
        setIsDreaming(data.is_dreaming);
      }
    } catch {
      /* ignore */
    }
  }, [selectedAgent]);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/dreams/${selectedAgent}/sessions`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data.sessions || []);
      }
    } catch {
      /* ignore */
    }
  }, [selectedAgent]);

  const fetchEvolutions = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/dreams/${selectedAgent}/evolutions`);
      if (res.ok) {
        const data = await res.json();
        setEvolutions(data.evolutions || []);
      }
    } catch {
      /* ignore */
    }
  }, [selectedAgent]);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/dreams/stats/overview`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchSessions();
    fetchEvolutions();
    fetchStats();
  }, [fetchStatus, fetchSessions, fetchEvolutions, fetchStats]);

  const startDream = async () => {
    setError("");
    setIsDreaming(true);
    try {
      const res = await fetch(`${API}/api/v1/dreams/${selectedAgent}/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          max_scenarios: 5,
          agent_data: { system_prompt: "You are a helpful AI assistant for the Gnosis platform." },
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to start dream");
      }
      const session = await res.json();
      setCurrentSession(session);
      setActiveTab("dreams");
      await fetchSessions();
      await fetchEvolutions();
      await fetchStats();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setIsDreaming(false);
    }
  };

  const handleAcceptEvolution = async (evolutionId: string) => {
    try {
      await fetch(`${API}/api/v1/dreams/${selectedAgent}/evolve/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ evolution_id: evolutionId }),
      });
      await fetchEvolutions();
    } catch {
      /* ignore */
    }
  };

  const handleRejectEvolution = async (evolutionId: string) => {
    try {
      await fetch(`${API}/api/v1/dreams/${selectedAgent}/evolve/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ evolution_id: evolutionId }),
      });
      await fetchEvolutions();
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="relative min-h-screen">
      <ParticleField />

      <div className="relative z-10 space-y-8">
        {/* ─── Header ─── */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center py-8"
        >
          <h1 className="text-4xl md:text-5xl font-display font-bold mb-3">
            <span className="bg-gradient-to-r from-purple-400 via-blue-400 to-emerald-400 bg-clip-text text-transparent">
              🌀 Agent Dreams
            </span>
          </h1>
          <p className="text-gnosis-muted text-lg">
            Where AI agents learn while sleeping
          </p>
        </motion.div>

        {/* ─── Stats Bar ─── */}
        {stats && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-3"
          >
            {[
              { label: "Dream Sessions", value: stats.total_dream_sessions, icon: "🌙" },
              { label: "Dreaming Now", value: stats.agents_dreaming_now, icon: "💤" },
              { label: "Evolutions", value: stats.total_evolutions, icon: "🧬" },
              { label: "Accepted", value: stats.accepted_evolutions, icon: "✅" },
            ].map((s, i) => (
              <div
                key={i}
                className="p-4 rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm text-center"
              >
                <span className="text-2xl">{s.icon}</span>
                <p className="text-2xl font-bold text-gnosis-text mt-1">{s.value}</p>
                <p className="text-xs text-gnosis-muted">{s.label}</p>
              </div>
            ))}
          </motion.div>
        )}

        {/* ─── Control Panel ─── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="p-6 rounded-2xl border border-purple-500/20 bg-gradient-to-br from-purple-500/[0.04] to-blue-500/[0.04] backdrop-blur-sm"
        >
          <h2 className="text-lg font-semibold text-gnosis-text mb-4 flex items-center gap-2">
            <span className="text-2xl">🎮</span> Dream Control Panel
          </h2>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-end gap-4">
            <div className="flex-1 space-y-2">
              <label className="text-xs text-gnosis-muted font-medium uppercase tracking-wider">Agent</label>
              <div className="flex gap-2">
                <select
                  value={agentId}
                  onChange={(e) => { setAgentId(e.target.value); setCustomAgent(""); }}
                  className="flex-1 px-3 py-2.5 rounded-xl bg-white/[0.05] border border-white/[0.08] text-gnosis-text text-sm focus:outline-none focus:border-purple-500/50 transition-colors"
                >
                  <option value="agent-1">Agent 1 — Default</option>
                  <option value="agent-2">Agent 2 — Research</option>
                  <option value="agent-3">Agent 3 — Code</option>
                  <option value="agent-4">Agent 4 — Creative</option>
                </select>
                <input
                  type="text"
                  placeholder="Or type agent ID..."
                  value={customAgent}
                  onChange={(e) => setCustomAgent(e.target.value)}
                  className="flex-1 px-3 py-2.5 rounded-xl bg-white/[0.05] border border-white/[0.08] text-gnosis-text text-sm placeholder:text-gnosis-muted/50 focus:outline-none focus:border-purple-500/50 transition-colors"
                />
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Status */}
              <div className="flex items-center gap-2">
                <div
                  className={`w-3 h-3 rounded-full ${
                    isDreaming
                      ? "bg-purple-400 animate-pulse shadow-lg shadow-purple-500/50"
                      : "bg-emerald-400"
                  }`}
                />
                <span className="text-sm text-gnosis-muted">
                  {isDreaming ? "Dreaming..." : "Awake"}
                </span>
              </div>

              {/* Dream Button */}
              <button
                onClick={startDream}
                disabled={isDreaming}
                className={`relative px-6 py-2.5 rounded-xl font-medium text-sm transition-all ${
                  isDreaming
                    ? "bg-purple-500/10 text-purple-300 cursor-not-allowed border border-purple-500/20"
                    : "bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:from-purple-500 hover:to-blue-500 shadow-lg shadow-purple-500/25 hover:shadow-purple-500/40 hover:scale-[1.02] active:scale-[0.98]"
                }`}
              >
                {isDreaming ? (
                  <span className="flex items-center gap-2">
                    <span className="inline-block animate-spin">🌀</span> Dreaming...
                  </span>
                ) : (
                  <span>Put Agent to Sleep 💤</span>
                )}
              </button>
            </div>
          </div>

          {error && (
            <p className="mt-3 text-sm text-red-400 bg-red-400/5 rounded-lg px-3 py-2 border border-red-500/10">
              {error}
            </p>
          )}
        </motion.div>

        {/* ─── Active Dream Visualization ─── */}
        {currentSession && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gnosis-text flex items-center gap-2">
                <span className="text-2xl">✨</span> Latest Dream Session
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  currentSession.status === "completed"
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "bg-yellow-500/10 text-yellow-400"
                }`}>
                  {currentSession.status}
                </span>
              </h2>
              <p className="text-xs text-gnosis-muted font-mono">
                {currentSession.scenarios_played} scenarios · {currentSession.insights_discovered} insights · {currentSession.memory_consolidations} consolidations
              </p>
            </div>

            <PhaseIndicator dreams={currentSession.dreams} />

            {currentSession.summary && (
              <div className="p-3 rounded-xl bg-purple-500/5 border border-purple-500/10 text-sm text-purple-300">
                📋 {currentSession.summary}
              </div>
            )}
          </motion.div>
        )}

        {/* ─── Tabs ─── */}
        <div className="flex gap-1 p-1 rounded-xl bg-white/[0.03] border border-white/[0.06] w-fit">
          {(["dreams", "evolutions", "history"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab
                  ? "bg-purple-500/15 text-purple-300 border border-purple-500/30"
                  : "text-gnosis-muted hover:text-gnosis-text"
              }`}
            >
              {tab === "dreams" && "🌀 "}
              {tab === "evolutions" && "🧬 "}
              {tab === "history" && "📜 "}
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* ─── Dream Feed ─── */}
        <AnimatePresence mode="wait">
          {activeTab === "dreams" && currentSession && (
            <motion.div
              key="dreams"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid gap-3"
            >
              {currentSession.dreams.length === 0 && (
                <div className="text-center py-16 text-gnosis-muted">
                  <p className="text-4xl mb-3">🌙</p>
                  <p>No dreams yet. Put an agent to sleep to start dreaming.</p>
                </div>
              )}
              {currentSession.dreams.map((dream, i) => (
                <DreamCard key={dream.id || i} dream={dream} index={i} />
              ))}
            </motion.div>
          )}

          {activeTab === "dreams" && !currentSession && (
            <motion.div
              key="no-dreams"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-center py-16 text-gnosis-muted"
            >
              <p className="text-6xl mb-4">🌙</p>
              <p className="text-lg mb-2">No active dream session</p>
              <p className="text-sm">Put an agent to sleep to see their dreams unfold</p>
            </motion.div>
          )}

          {/* ─── Evolution Timeline ─── */}
          {activeTab === "evolutions" && (
            <motion.div
              key="evolutions"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-0"
            >
              {evolutions.length === 0 && (
                <div className="text-center py-16 text-gnosis-muted">
                  <p className="text-4xl mb-3">🧬</p>
                  <p>No evolutions yet. Dreams will generate prompt improvements.</p>
                </div>
              )}
              {evolutions.map((ev) => (
                <EvolutionCard
                  key={ev.id}
                  evolution={ev}
                  onAccept={handleAcceptEvolution}
                  onReject={handleRejectEvolution}
                />
              ))}
            </motion.div>
          )}

          {/* ─── Dream History ─── */}
          {activeTab === "history" && (
            <motion.div
              key="history"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-3"
            >
              {sessions.length === 0 && (
                <div className="text-center py-16 text-gnosis-muted">
                  <p className="text-4xl mb-3">📜</p>
                  <p>No dream history yet.</p>
                </div>
              )}
              {sessions.map((session, i) => (
                <motion.div
                  key={session.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-4 rounded-xl border border-white/[0.06] bg-white/[0.02] hover:border-purple-500/20 transition-all cursor-pointer"
                  onClick={() => {
                    setCurrentSession(session);
                    setActiveTab("dreams");
                  }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">🌙</span>
                      <span className="text-sm font-medium text-gnosis-text">
                        Session {session.id}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          session.status === "completed"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : session.status === "interrupted"
                            ? "bg-red-500/10 text-red-400"
                            : "bg-yellow-500/10 text-yellow-400"
                        }`}
                      >
                        {session.status}
                      </span>
                    </div>
                    <span className="text-xs text-gnosis-muted font-mono">
                      {session.ended_at ? `${(session.ended_at - session.started_at).toFixed(1)}s` : "..."}
                    </span>
                  </div>
                  <div className="flex gap-4 text-xs text-gnosis-muted">
                    <span>🎯 {session.scenarios_played} scenarios</span>
                    <span>💡 {session.insights_discovered} insights</span>
                    <span>🧠 {session.memory_consolidations} consolidations</span>
                    {session.prompt_improvements.length > 0 && (
                      <span>🧬 {session.prompt_improvements.length} evolution(s)</span>
                    )}
                  </div>
                  {session.summary && (
                    <p className="text-xs text-gnosis-muted/70 mt-2 italic">{session.summary}</p>
                  )}
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
