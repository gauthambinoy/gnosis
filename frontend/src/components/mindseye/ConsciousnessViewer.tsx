"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GnosisSocket } from "@/lib/ws";

// --- Types ---

interface PhaseEvent {
  phase: CortexPhase;
  status: "pending" | "active" | "completed";
  duration_ms?: number;
  confidence?: number;
  tokens?: number;
}

interface MemoryHit {
  id: string;
  tier: "correction" | "episodic" | "semantic" | "procedural";
  content: string;
  relevance: number;
}

interface ActionEntry {
  id: string;
  action: string;
  status: "pending" | "running" | "success" | "failed" | "escalated";
  timestamp: string;
}

interface ConsciousnessState {
  phases: PhaseEvent[];
  memories: MemoryHit[];
  tokens: { used: number; budget: number };
  confidence: number;
  actions: ActionEntry[];
  active: boolean;
}

type CortexPhase = "perceive" | "memory" | "context" | "reason" | "meta" | "act";

const CORTEX_PHASES: { key: CortexPhase; label: string; icon: string }[] = [
  { key: "perceive", label: "Perceive", icon: "👁" },
  { key: "memory", label: "Memory", icon: "🧠" },
  { key: "context", label: "Context", icon: "📋" },
  { key: "reason", label: "Reason", icon: "⚡" },
  { key: "meta", label: "Meta", icon: "🔮" },
  { key: "act", label: "Act", icon: "🎯" },
];

const TIER_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  correction: { bg: "bg-red-500/15", text: "text-red-400", label: "Correction" },
  episodic: { bg: "bg-blue-500/15", text: "text-blue-400", label: "Episodic" },
  semantic: { bg: "bg-purple-500/15", text: "text-purple-400", label: "Semantic" },
  procedural: { bg: "bg-green-500/15", text: "text-green-400", label: "Procedural" },
};

const STATUS_ICONS: Record<string, string> = {
  pending: "○",
  running: "◌",
  success: "✓",
  failed: "✗",
  escalated: "⚠",
};

// --- Sub-components ---

function PhaseTimeline({ phases }: { phases: PhaseEvent[] }) {
  const phaseMap = new Map(phases.map((p) => [p.phase, p]));

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-medium text-gnosis-muted uppercase tracking-wider">
        Cortex Pipeline
      </h3>
      <div className="flex items-center gap-1">
        {CORTEX_PHASES.map((phase, i) => {
          const event = phaseMap.get(phase.key);
          const isActive = event?.status === "active";
          const isCompleted = event?.status === "completed";

          return (
            <div key={phase.key} className="flex items-center flex-1">
              <motion.div
                className={`
                  relative flex flex-col items-center justify-center rounded-lg px-2 py-2 w-full
                  border transition-colors duration-300
                  ${isActive
                    ? "border-gnosis-primary/60 bg-gnosis-primary/10"
                    : isCompleted
                      ? "border-gnosis-primary/30 bg-gnosis-primary/5"
                      : "border-gnosis-border bg-gnosis-bg"
                  }
                `}
                animate={
                  isActive
                    ? { boxShadow: ["0 0 8px rgba(200,255,0,0.15)", "0 0 20px rgba(200,255,0,0.3)", "0 0 8px rgba(200,255,0,0.15)"] }
                    : { boxShadow: "0 0 0px rgba(0,0,0,0)" }
                }
                transition={isActive ? { duration: 1.5, repeat: Infinity } : {}}
              >
                <span className="text-sm">{phase.icon}</span>
                <span
                  className={`text-[10px] mt-0.5 font-medium ${
                    isActive ? "text-gnosis-primary" : isCompleted ? "text-gnosis-text" : "text-gnosis-muted"
                  }`}
                >
                  {phase.label}
                </span>
                {event?.duration_ms !== undefined && (
                  <span className="text-[9px] text-gnosis-muted mt-0.5">
                    {event.duration_ms < 1000 ? `${event.duration_ms}ms` : `${(event.duration_ms / 1000).toFixed(1)}s`}
                  </span>
                )}
                {isActive && (
                  <motion.div
                    className="absolute inset-0 rounded-lg border border-gnosis-primary/40"
                    animate={{ opacity: [0.3, 0.7, 0.3] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  />
                )}
              </motion.div>
              {i < CORTEX_PHASES.length - 1 && (
                <div
                  className={`w-2 h-px mx-0.5 flex-shrink-0 ${
                    isCompleted ? "bg-gnosis-primary/50" : "bg-gnosis-border"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MemoryPanel({ memories }: { memories: MemoryHit[] }) {
  return (
    <div className="space-y-3">
      <h3 className="text-xs font-medium text-gnosis-muted uppercase tracking-wider">
        Retrieved Memories
        {memories.length > 0 && (
          <span className="ml-2 text-gnosis-primary">{memories.length}</span>
        )}
      </h3>
      <div className="space-y-2 max-h-40 overflow-y-auto scrollbar-thin">
        <AnimatePresence mode="popLayout">
          {memories.length === 0 ? (
            <p className="text-xs text-gnosis-muted/60 italic">No memories retrieved yet</p>
          ) : (
            memories.map((mem) => {
              const tier = TIER_COLORS[mem.tier] || TIER_COLORS.episodic;
              return (
                <motion.div
                  key={mem.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  className="flex items-start gap-2 rounded-lg bg-gnosis-bg border border-gnosis-border p-2"
                >
                  <span
                    className={`${tier.bg} ${tier.text} text-[10px] font-medium px-1.5 py-0.5 rounded-full flex-shrink-0`}
                  >
                    {tier.label}
                  </span>
                  <p className="text-xs text-gnosis-text/80 line-clamp-2 flex-1">
                    {mem.content}
                  </p>
                  <span className="text-[10px] text-gnosis-muted flex-shrink-0">
                    {(mem.relevance * 100).toFixed(0)}%
                  </span>
                </motion.div>
              );
            })
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function TokenTracker({ used, budget }: { used: number; budget: number }) {
  const pct = budget > 0 ? Math.min((used / budget) * 100, 100) : 0;
  const isWarning = pct > 75;
  const isDanger = pct > 90;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-medium text-gnosis-muted uppercase tracking-wider">
          Tokens
        </h3>
        <span className={`text-xs font-mono ${isDanger ? "text-red-400" : isWarning ? "text-yellow-400" : "text-gnosis-text"}`}>
          {used.toLocaleString()} / {budget.toLocaleString()}
        </span>
      </div>
      <div className="h-2 rounded-full bg-gnosis-bg border border-gnosis-border overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${isDanger ? "bg-red-500" : isWarning ? "bg-yellow-500" : "bg-gnosis-primary"}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ type: "spring", stiffness: 100, damping: 20 }}
        />
      </div>
    </div>
  );
}

function ConfidenceMeter({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(1, value));
  const degrees = clamped * 180;
  const color =
    clamped >= 0.7 ? "#00FF88" : clamped >= 0.4 ? "#FFD700" : "#FF3366";

  const radius = 36;
  const circumference = Math.PI * radius;
  const offset = circumference - (clamped * circumference);

  return (
    <div className="flex flex-col items-center gap-1">
      <h3 className="text-xs font-medium text-gnosis-muted uppercase tracking-wider">
        Confidence
      </h3>
      <div className="relative w-24 h-14 overflow-hidden">
        <svg viewBox="0 0 80 44" className="w-full h-full">
          {/* Background arc */}
          <path
            d="M 4 40 A 36 36 0 0 1 76 40"
            fill="none"
            stroke="#1A1A1A"
            strokeWidth="5"
            strokeLinecap="round"
          />
          {/* Value arc */}
          <motion.path
            d="M 4 40 A 36 36 0 0 1 76 40"
            fill="none"
            stroke={color}
            strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ type: "spring", stiffness: 60, damping: 15 }}
          />
          {/* Needle */}
          <motion.line
            x1="40"
            y1="40"
            x2="40"
            y2="10"
            stroke={color}
            strokeWidth="1.5"
            strokeLinecap="round"
            style={{ transformOrigin: "40px 40px" }}
            animate={{ rotate: degrees - 90 }}
            transition={{ type: "spring", stiffness: 80, damping: 12 }}
          />
          <circle cx="40" cy="40" r="2.5" fill={color} />
        </svg>
      </div>
      <motion.span
        className="text-lg font-bold font-mono"
        style={{ color }}
        key={clamped.toFixed(2)}
        initial={{ scale: 1.2, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
      >
        {(clamped * 100).toFixed(0)}%
      </motion.span>
    </div>
  );
}

function ActionLog({ actions }: { actions: ActionEntry[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [actions]);

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-medium text-gnosis-muted uppercase tracking-wider">
        Actions
        {actions.length > 0 && (
          <span className="ml-2 text-gnosis-primary">{actions.length}</span>
        )}
      </h3>
      <div ref={scrollRef} className="space-y-1.5 max-h-32 overflow-y-auto scrollbar-thin">
        <AnimatePresence mode="popLayout">
          {actions.length === 0 ? (
            <p className="text-xs text-gnosis-muted/60 italic">No actions yet</p>
          ) : (
            actions.map((act) => (
              <motion.div
                key={act.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2 text-xs"
              >
                <span
                  className={`flex-shrink-0 ${
                    act.status === "success"
                      ? "text-gnosis-success"
                      : act.status === "failed"
                        ? "text-gnosis-error"
                        : act.status === "running"
                          ? "text-gnosis-primary"
                          : act.status === "escalated"
                            ? "text-yellow-400"
                            : "text-gnosis-muted"
                  }`}
                >
                  {STATUS_ICONS[act.status] || "○"}
                </span>
                <span className="text-gnosis-text/80 truncate flex-1">{act.action}</span>
                <span className="text-gnosis-muted text-[10px] flex-shrink-0">
                  {new Date(act.timestamp).toLocaleTimeString()}
                </span>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

// --- Main Component ---

interface ConsciousnessViewerProps {
  agentId: string;
  /** Optional static data for replay mode */
  replayData?: ConsciousnessState;
}

export function ConsciousnessViewer({ agentId, replayData }: ConsciousnessViewerProps) {
  const [state, setState] = useState<ConsciousnessState>({
    phases: [],
    memories: [],
    tokens: { used: 0, budget: 4096 },
    confidence: 0,
    actions: [],
    active: false,
  });

  const socketRef = useRef<GnosisSocket | null>(null);

  const handlePhaseUpdate = useCallback((data: unknown) => {
    const event = data as PhaseEvent;
    setState((prev) => {
      const updated = prev.phases.filter((p) => p.phase !== event.phase);
      return { ...prev, phases: [...updated, event], active: true };
    });
  }, []);

  const handleMemoryRetrieved = useCallback((data: unknown) => {
    const mem = data as MemoryHit;
    setState((prev) => ({
      ...prev,
      memories: [...prev.memories.filter((m) => m.id !== mem.id), mem],
    }));
  }, []);

  const handleTokenUpdate = useCallback((data: unknown) => {
    const tokens = data as { used: number; budget: number };
    setState((prev) => ({ ...prev, tokens }));
  }, []);

  const handleConfidenceUpdate = useCallback((data: unknown) => {
    const { confidence } = data as { confidence: number };
    setState((prev) => ({ ...prev, confidence }));
  }, []);

  const handleActionUpdate = useCallback((data: unknown) => {
    const action = data as ActionEntry;
    setState((prev) => ({
      ...prev,
      actions: [...prev.actions.filter((a) => a.id !== action.id), action],
    }));
  }, []);

  const handleExecutionComplete = useCallback(() => {
    setState((prev) => ({ ...prev, active: false }));
  }, []);

  useEffect(() => {
    if (replayData) {
      setState(replayData);
      return;
    }

    const socket = new GnosisSocket(`/ws/minds-eye/${agentId}`);
    socketRef.current = socket;

    socket.on("phase_update", handlePhaseUpdate);
    socket.on("memory_retrieved", handleMemoryRetrieved);
    socket.on("token_update", handleTokenUpdate);
    socket.on("confidence_update", handleConfidenceUpdate);
    socket.on("action_update", handleActionUpdate);
    socket.on("execution_complete", handleExecutionComplete);

    socket.connect();

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [agentId, replayData, handlePhaseUpdate, handleMemoryRetrieved, handleTokenUpdate, handleConfidenceUpdate, handleActionUpdate, handleExecutionComplete]);

  return (
    <div className="space-y-5">
      {/* Status indicator */}
      <div className="flex items-center gap-2">
        <motion.div
          className={`w-2 h-2 rounded-full ${state.active ? "bg-gnosis-primary" : "bg-gnosis-muted/40"}`}
          animate={state.active ? { scale: [1, 1.3, 1], opacity: [0.7, 1, 0.7] } : {}}
          transition={state.active ? { duration: 1.5, repeat: Infinity } : {}}
        />
        <span className="text-xs text-gnosis-muted">
          {state.active ? "Processing..." : replayData ? "Replay" : "Waiting for execution"}
        </span>
      </div>

      {/* Phase Timeline */}
      <PhaseTimeline phases={state.phases} />

      {/* Middle row: Tokens + Confidence */}
      <div className="grid grid-cols-[1fr_auto] gap-6 items-end">
        <TokenTracker used={state.tokens.used} budget={state.tokens.budget} />
        <ConfidenceMeter value={state.confidence} />
      </div>

      {/* Memory Panel */}
      <MemoryPanel memories={state.memories} />

      {/* Action Log */}
      <ActionLog actions={state.actions} />
    </div>
  );
}
