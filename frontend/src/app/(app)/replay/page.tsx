"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx } from "clsx";
import { Card } from "@/components/shared/Card";
import { Badge } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/* ─── Types ─── */
interface RecordingSummary {
  id: string;
  agent_id: string;
  task: string;
  status: string;
  total_duration_ms: number;
  step_count: number;
  started_at: string;
  completed_at: string | null;
}

interface StepDetail {
  phase: string;
  status: string;
  input_summary: string;
  output_summary: string;
  duration_ms: number;
  metadata: Record<string, unknown>;
  timestamp: string;
}

interface RecordingDetail {
  id: string;
  agent_id: string;
  task: string;
  steps: StepDetail[];
  total_duration_ms: number;
  token_usage: Record<string, number>;
  status: string;
  started_at: string;
  completed_at: string | null;
}

/* ─── Phase colors ─── */
const PHASE_COLORS: Record<string, string> = {
  perceive: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  memory: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  context: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
  reason: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  meta: "bg-pink-500/20 text-pink-400 border-pink-500/30",
  meta_cognition: "bg-pink-500/20 text-pink-400 border-pink-500/30",
  act: "bg-green-500/20 text-green-400 border-green-500/30",
  post: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  error: "bg-red-500/20 text-red-400 border-red-500/30",
};

const PHASE_ICONS: Record<string, string> = {
  perceive: "👁",
  memory: "🧠",
  context: "📋",
  reason: "⚡",
  meta: "🔍",
  meta_cognition: "🔍",
  act: "🎯",
  post: "📝",
  error: "❌",
};

const STATUS_VARIANTS: Record<string, "success" | "error" | "warning" | "default"> = {
  completed: "success",
  failed: "error",
  running: "warning",
};

/* ─── Demo data ─── */
function generateDemoData(): { recordings: RecordingSummary[]; details: Record<string, RecordingDetail> } {
  const phases = ["perceive", "memory", "context", "reason", "meta_cognition", "act", "post"];
  const tasks = [
    "Process incoming email from support@acme.com",
    "Analyze quarterly sales report and generate summary",
    "Monitor GitHub PR #142 and provide code review",
    "Schedule team standup and send reminders",
    "Classify incoming webhook payload from Stripe",
  ];
  const agents = ["agent-email-01", "agent-analytics-02", "agent-devops-03", "agent-scheduler-04", "agent-webhook-05"];
  const statuses = ["completed", "completed", "completed", "failed", "completed"];

  const recordings: RecordingSummary[] = [];
  const details: Record<string, RecordingDetail> = {};

  for (let i = 0; i < 5; i++) {
    const id = `rec-demo-${i + 1}`;
    const steps: StepDetail[] = phases.map((phase, j) => ({
      phase,
      status: statuses[i] === "failed" && j === 3 ? "failed" : "completed",
      input_summary: `Input for ${phase} phase — processing ${tasks[i].slice(0, 60)}`,
      output_summary: `${phase} completed: extracted ${Math.floor(Math.random() * 10) + 1} signals`,
      duration_ms: Math.floor(Math.random() * 800) + 50,
      metadata: {},
      timestamp: new Date(Date.now() - (5 - i) * 3600000 - (phases.length - j) * 60000).toISOString(),
    }));

    const totalMs = steps.reduce((s, st) => s + st.duration_ms, 0);

    recordings.push({
      id,
      agent_id: agents[i],
      task: tasks[i],
      status: statuses[i],
      total_duration_ms: totalMs,
      step_count: steps.length,
      started_at: new Date(Date.now() - (5 - i) * 3600000).toISOString(),
      completed_at: new Date(Date.now() - (5 - i) * 3600000 + totalMs).toISOString(),
    });

    details[id] = {
      id,
      agent_id: agents[i],
      task: tasks[i],
      steps,
      total_duration_ms: totalMs,
      token_usage: { prompt: Math.floor(Math.random() * 2000) + 500, completion: Math.floor(Math.random() * 800) + 100 },
      status: statuses[i],
      started_at: recordings[i].started_at,
      completed_at: recordings[i].completed_at,
    };
  }

  return { recordings, details };
}

export default function ReplayPage() {
  const [recordings, setRecordings] = useState<RecordingSummary[]>([]);
  const [selectedDetail, setSelectedDetail] = useState<RecordingDetail | null>(null);
  const [stats, setStats] = useState<{ total_recordings: number; by_status: Record<string, number> } | null>(null);
  const [filterAgent, setFilterAgent] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeStepIdx, setActiveStepIdx] = useState(-1);
  const [loading, setLoading] = useState(true);
  const playTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const demoDataRef = useRef<ReturnType<typeof generateDemoData> | null>(null);

  /* ─── Fetch recordings ─── */
  const fetchRecordings = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterAgent) params.set("agent_id", filterAgent);
      const res = await fetch(`${API}/replay?${params}`);
      if (res.ok) {
        const data = await res.json();
        if (data.recordings?.length > 0) {
          setRecordings(data.recordings);
          setLoading(false);
          return;
        }
      }
    } catch {
      // API unavailable — use demo data
    }
    // Fallback to demo data
    if (!demoDataRef.current) demoDataRef.current = generateDemoData();
    setRecordings(demoDataRef.current.recordings);
    setStats({ total_recordings: 5, by_status: { completed: 4, failed: 1 } });
    setLoading(false);
  }, [filterAgent]);

  useEffect(() => {
    fetchRecordings();
  }, [fetchRecordings]);

  /* ─── Fetch detail ─── */
  const fetchDetail = async (id: string) => {
    try {
      const res = await fetch(`${API}/replay/${id}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedDetail(data);
        setActiveStepIdx(-1);
        setIsPlaying(false);
        return;
      }
    } catch {
      // fallback
    }
    if (demoDataRef.current?.details[id]) {
      setSelectedDetail(demoDataRef.current.details[id]);
      setActiveStepIdx(-1);
      setIsPlaying(false);
    }
  };

  /* ─── Playback ─── */
  const startPlayback = () => {
    if (!selectedDetail || selectedDetail.steps.length === 0) return;
    setIsPlaying(true);
    setActiveStepIdx(0);
  };

  const stopPlayback = () => {
    setIsPlaying(false);
    if (playTimerRef.current) clearTimeout(playTimerRef.current);
  };

  useEffect(() => {
    if (!isPlaying || !selectedDetail) return;
    if (activeStepIdx >= selectedDetail.steps.length) {
      setIsPlaying(false);
      return;
    }
    const step = selectedDetail.steps[activeStepIdx];
    const delay = Math.max(step.duration_ms * 0.5, 300);
    playTimerRef.current = setTimeout(() => {
      setActiveStepIdx((prev) => prev + 1);
    }, delay);
    return () => {
      if (playTimerRef.current) clearTimeout(playTimerRef.current);
    };
  }, [isPlaying, activeStepIdx, selectedDetail]);

  /* ─── Filter ─── */
  const filtered = recordings.filter((r) => {
    if (filterStatus && r.status !== filterStatus) return false;
    if (filterAgent && !r.agent_id.toLowerCase().includes(filterAgent.toLowerCase())) return false;
    return true;
  });

  const uniqueAgents = [...new Set(recordings.map((r) => r.agent_id))];
  const maxDuration = Math.max(...(selectedDetail?.steps.map((s) => s.duration_ms) || [1]));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-gnosis-text">▶ Execution Replay</h1>
        <p className="text-gnosis-muted mt-1">Review and debug agent execution step-by-step</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card>
            <p className="text-xs text-gnosis-muted uppercase tracking-wider">Total Recordings</p>
            <p className="text-2xl font-bold text-gnosis-text mt-1">{stats.total_recordings}</p>
          </Card>
          <Card>
            <p className="text-xs text-gnosis-muted uppercase tracking-wider">Completed</p>
            <p className="text-2xl font-bold text-green-400 mt-1">{stats.by_status.completed || 0}</p>
          </Card>
          <Card>
            <p className="text-xs text-gnosis-muted uppercase tracking-wider">Failed</p>
            <p className="text-2xl font-bold text-red-400 mt-1">{stats.by_status.failed || 0}</p>
          </Card>
          <Card>
            <p className="text-xs text-gnosis-muted uppercase tracking-wider">Running</p>
            <p className="text-2xl font-bold text-yellow-400 mt-1">{stats.by_status.running || 0}</p>
          </Card>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={filterAgent}
          onChange={(e) => setFilterAgent(e.target.value)}
          className="bg-[#0A0A0A] border border-white/10 rounded-xl px-3 py-2 text-sm text-white/70 focus:outline-none focus:border-[#C8FF00]/50 appearance-none"
        >
          <option value="">All Agents</option>
          {uniqueAgents.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="bg-[#0A0A0A] border border-white/10 rounded-xl px-3 py-2 text-sm text-white/70 focus:outline-none focus:border-[#C8FF00]/50 appearance-none"
        >
          <option value="">All Statuses</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="running">Running</option>
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Recording List */}
        <div className="lg:col-span-2 space-y-2">
          {loading ? (
            <Card><p className="text-gnosis-muted text-sm animate-pulse">Loading recordings...</p></Card>
          ) : filtered.length === 0 ? (
            <Card><p className="text-gnosis-muted text-sm">No recordings found</p></Card>
          ) : (
            filtered.map((rec) => (
              <motion.div
                key={rec.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ scale: 1.01 }}
                onClick={() => fetchDetail(rec.id)}
                className={clsx(
                  "p-4 rounded-xl border cursor-pointer transition-all",
                  selectedDetail?.id === rec.id
                    ? "border-[#C8FF00]/40 bg-[#C8FF00]/5"
                    : "border-white/5 bg-[#0A0A0A] hover:border-white/10"
                )}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <p className="text-sm font-medium text-white truncate flex-1">{rec.task}</p>
                  <Badge variant={STATUS_VARIANTS[rec.status] || "default"}>{rec.status}</Badge>
                </div>
                <div className="flex items-center gap-4 text-xs text-white/40">
                  <span>{rec.agent_id}</span>
                  <span>{rec.step_count} steps</span>
                  <span>{rec.total_duration_ms.toFixed(0)}ms</span>
                </div>
                <p className="text-[10px] text-white/20 mt-1">
                  {new Date(rec.started_at).toLocaleString()}
                </p>
              </motion.div>
            ))
          )}
        </div>

        {/* Detail / Timeline */}
        <div className="lg:col-span-3">
          <AnimatePresence mode="wait">
            {selectedDetail ? (
              <motion.div
                key={selectedDetail.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-4"
              >
                {/* Detail header */}
                <Card>
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h2 className="text-lg font-semibold text-white">{selectedDetail.task}</h2>
                      <p className="text-xs text-white/40 mt-1">
                        Agent: {selectedDetail.agent_id} · {selectedDetail.total_duration_ms.toFixed(0)}ms total
                        {selectedDetail.token_usage?.prompt && (
                          <> · {selectedDetail.token_usage.prompt + (selectedDetail.token_usage.completion || 0)} tokens</>
                        )}
                      </p>
                    </div>
                    <Badge variant={STATUS_VARIANTS[selectedDetail.status] || "default"}>
                      {selectedDetail.status}
                    </Badge>
                  </div>

                  {/* Playback controls */}
                  <div className="flex items-center gap-3">
                    {!isPlaying ? (
                      <Button onClick={startPlayback}>
                        ▶ Play
                      </Button>
                    ) : (
                      <Button variant="secondary" onClick={stopPlayback}>
                        ⏸ Pause
                      </Button>
                    )}
                    <Button
                      variant="secondary"
                      onClick={() => { setActiveStepIdx(-1); setIsPlaying(false); }}
                    >
                      ⏮ Reset
                    </Button>
                    {activeStepIdx >= 0 && (
                      <span className="text-xs text-white/40">
                        Step {Math.min(activeStepIdx + 1, selectedDetail.steps.length)} / {selectedDetail.steps.length}
                      </span>
                    )}
                  </div>
                </Card>

                {/* Steps timeline */}
                <div className="space-y-2">
                  {selectedDetail.steps.map((step, idx) => {
                    const isActive = idx === activeStepIdx;
                    const isPast = idx < activeStepIdx;
                    const phaseColor = PHASE_COLORS[step.phase] || PHASE_COLORS.error;
                    const phaseIcon = PHASE_ICONS[step.phase] || "●";

                    return (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{
                          opacity: activeStepIdx === -1 || isPast || isActive ? 1 : 0.3,
                          y: 0,
                          scale: isActive ? 1.02 : 1,
                        }}
                        transition={{ duration: 0.3 }}
                        className={clsx(
                          "p-4 rounded-xl border transition-all",
                          isActive
                            ? "border-[#C8FF00]/50 bg-[#C8FF00]/5 shadow-lg shadow-[#C8FF00]/5"
                            : "border-white/5 bg-[#0A0A0A]"
                        )}
                      >
                        <div className="flex items-center gap-3 mb-2">
                          {/* Phase badge */}
                          <span
                            className={clsx(
                              "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border",
                              phaseColor
                            )}
                          >
                            {phaseIcon} {step.phase}
                          </span>
                          <Badge variant={step.status === "completed" ? "success" : step.status === "failed" ? "error" : "default"}>
                            {step.status}
                          </Badge>
                          <span className="text-xs text-white/30 ml-auto">{step.duration_ms.toFixed(0)}ms</span>
                        </div>

                        {/* Duration bar */}
                        <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden mb-3">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${(step.duration_ms / maxDuration) * 100}%` }}
                            transition={{ duration: 0.6, ease: "easeOut" }}
                            className={clsx(
                              "h-full rounded-full",
                              step.status === "failed" ? "bg-red-500" : "bg-[#C8FF00]"
                            )}
                          />
                        </div>

                        {/* Summaries */}
                        {step.input_summary && (
                          <p className="text-xs text-white/40 mb-1">
                            <span className="text-white/60 font-medium">In:</span> {step.input_summary}
                          </p>
                        )}
                        {step.output_summary && (
                          <p className="text-xs text-white/40">
                            <span className="text-white/60 font-medium">Out:</span> {step.output_summary}
                          </p>
                        )}
                      </motion.div>
                    );
                  })}
                </div>
              </motion.div>
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center justify-center h-64"
              >
                <p className="text-white/30 text-sm">Select a recording to view its execution timeline</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
